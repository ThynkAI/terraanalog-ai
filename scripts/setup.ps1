<#
.SYNOPSIS
  TerraAnalog AI - one-command local setup + start for Windows (Windows PowerShell 5.1 or PowerShell 7+).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Dev
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -NoStart -Tests
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -ApiPort 8001 -WebPort 3001

.NOTES
  Prerequisites: Python 3.11+ (python.org installer or "py" launcher) and Node.js 20+. Docker is NOT required.
  Written for Windows PowerShell 5.1: no '&&' chaining, no ternary or null-coalescing operators.
#>
[CmdletBinding()]
param(
  [switch]$Dev,
  [switch]$NoStart,
  [switch]$Tests,
  [int]$ApiPort = 8000,
  [int]$WebPort = 3000,
  [string]$DataDir = "data/fixtures"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Say([string]$msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Fail([string]$msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }
function Invoke-Checked([string]$exe, [string[]]$argv) {
  & $exe @argv
  if ($LASTEXITCODE -ne 0) { Fail "'$exe $($argv -join ' ')' failed with exit code $LASTEXITCODE" }
}

$IsWin = ($env:OS -eq "Windows_NT")
if ($IsWin) { $VenvPy = Join-Path $Root ".venv\Scripts\python.exe"; $Npm = "npm.cmd"; $Npx = "npx.cmd" }
else { $VenvPy = Join-Path $Root ".venv/bin/python"; $Npm = "npm"; $Npx = "npx" }

# ---- prerequisites -------------------------------------------------------------------
$PyExe = $null; $PyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) { $PyExe = "py"; $PyArgs = @("-3") }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $PyExe = "python" }
elseif (Get-Command python3 -ErrorAction SilentlyContinue) { $PyExe = "python3" }
if (-not $PyExe) { Fail "Python 3.11+ is required: https://www.python.org/downloads/ (tick 'Add python.exe to PATH')." }
& $PyExe @($PyArgs + @("-c", "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"))
if ($LASTEXITCODE -ne 0) { Fail "Python 3.11+ is required." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail "Node.js 20+ is required: https://nodejs.org" }
$NodeMajor = [int]((& node -p "process.versions.node.split('.')[0]") | Out-String).Trim()
if ($NodeMajor -lt 20) { Fail "Node.js 20+ is required (found $(& node -v))." }
$PyVer = (& $PyExe @($PyArgs + @("-c", "import platform; print(platform.python_version())")) | Out-String).Trim()
Say "Python $PyVer, Node $(& node -v)"

# ---- backend -------------------------------------------------------------------------
if (-not (Test-Path $VenvPy)) {
  Say "Creating Python virtualenv in .venv"
  Invoke-Checked $PyExe ($PyArgs + @("-m", "venv", ".venv"))
}
Say "Installing backend dependencies"
Invoke-Checked $VenvPy @("-m", "pip", "install", "-q", "--upgrade", "pip")
$Req = "backend/requirements.txt"
if ($Tests) { $Req = "backend/requirements-dev.txt" }
Invoke-Checked $VenvPy @("-m", "pip", "install", "-q", "-r", $Req)
Invoke-Checked $VenvPy @("scripts/validate_data.py", $DataDir)
Say "Data directory validated ($DataDir)"

# ---- frontend ------------------------------------------------------------------------
Say "Installing web dependencies (npm ci)"
Push-Location (Join-Path $Root "web")
try {
  Invoke-Checked $Npm @("ci", "--no-audit", "--no-fund")
  if ($Tests) { Invoke-Checked $Npx @("playwright", "install", "chromium") }
  if (-not $Dev) {
    Say "Building the web UI"
    Invoke-Checked $Npm @("run", "build")
  }
} finally { Pop-Location }

if ($NoStart) { Say "Setup complete. Start later with: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1"; exit 0 }

# ---- start ---------------------------------------------------------------------------
function Test-PortBusy([int]$port) {
  $c = New-Object System.Net.Sockets.TcpClient
  try { $c.Connect("127.0.0.1", $port); return $true } catch { return $false } finally { $c.Close() }
}
if (Test-PortBusy $ApiPort) { Fail "Port $ApiPort is already in use. Re-run with -ApiPort <free port>." }
if (Test-PortBusy $WebPort) { Fail "Port $WebPort is already in use. Re-run with -WebPort <free port>." }
$env:TERRA_DATA_DIR = $DataDir
$env:TERRA_CORS_ORIGINS = "http://localhost:$WebPort"
Say "Starting API on http://127.0.0.1:$ApiPort (docs at /docs)"
$apiArgs = @("-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "$ApiPort")
$api = Start-Process -FilePath $VenvPy -ArgumentList $apiArgs -WorkingDirectory $Root -NoNewWindow -PassThru
try {
  $ok = $false
  for ($i = 0; $i -lt 40; $i++) {
    if ($api.HasExited) { Fail "API failed to start (exit code $($api.ExitCode))." }
    try {
      $r = Invoke-WebRequest -Uri "http://127.0.0.1:$ApiPort/api/health" -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep -Milliseconds 500 }
  }
  if (-not $ok) { Fail "API did not become healthy on port $ApiPort." }
  Say "Starting web UI on http://localhost:$WebPort  (Ctrl+C stops both)"
  $env:PORT = "$WebPort"
  $env:API_URL = "http://127.0.0.1:$ApiPort"
  Push-Location (Join-Path $Root "web")
  try {
    if ($Dev) { & $Npm run dev } else { & $Npm start }
  } finally { Pop-Location }
} finally {
  if ($api -and -not $api.HasExited) { Say "Stopping API (pid $($api.Id))"; Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue }
}
