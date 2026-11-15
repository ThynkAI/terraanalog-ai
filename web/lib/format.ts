export const pct = (x: number | null | undefined, digits = 0) => (x === null || x === undefined ? "—" : `${(x * 100).toFixed(digits)}%`);
export const num = (x: number | null | undefined, digits = 1) => (x === null || x === undefined ? "—" : x.toFixed(digits));

export function fmtLat(lat: number) {
  return `${Math.abs(lat).toFixed(2)}°${lat >= 0 ? "N" : "S"}`;
}
export function fmtLonEarth(lon: number) {
  return `${Math.abs(lon).toFixed(2)}°${lon >= 0 ? "E" : "W"}`;
}
/** Planetary longitudes are always reported east-positive (IAU), never as W. */
export function fmtLonEast(lon: number) {
  return `${lon.toFixed(2)}°E`;
}

export function scoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return "#6c7587";
  if (score >= 80) return "#4ade80";
  if (score >= 65) return "#a3e635";
  if (score >= 50) return "#fbbf24";
  if (score >= 35) return "#f08a55";
  return "#ef4444";
}

export function toCSV(rows: Record<string, unknown>[], banner?: string): string {
  if (!rows.length) return banner ? `# ${banner}\n` : "";
  const cols = Object.keys(rows[0]);
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [cols.join(","), ...rows.map((r) => cols.map((c) => esc(r[c])).join(","))];
  return (banner ? `# ${banner}\n` : "") + lines.join("\n") + "\n";
}

export function downloadText(filename: string, text: string, mime = "text/csv") {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Parse "lat, lon" (decimal degrees, optional N/S/E/W) for geographic search. Returns null when not coordinates. */
export function parseLatLon(input: string): { lat: number; lon: number } | null {
  const m = input.trim().match(/^(-?\d+(?:\.\d+)?)\s*°?\s*([NSns])?\s*[,;\s]\s*(-?\d+(?:\.\d+)?)\s*°?\s*([EWew])?$/);
  if (!m) return null;
  let lat = parseFloat(m[1]);
  let lon = parseFloat(m[3]);
  if (m[2] && m[2].toUpperCase() === "S") lat = -Math.abs(lat);
  if (m[4] && m[4].toUpperCase() === "W") lon = -Math.abs(lon);
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
  return { lat, lon };
}

export function weightsToParam(w: Record<string, number>): string {
  return Object.entries(w)
    .filter(([, v]) => Math.abs(v - 1) > 1e-9)
    .map(([k, v]) => `${k}:${Number(v.toFixed(2))}`)
    .join(",");
}

export function paramToWeights(s: string | null): Record<string, number> {
  const out: Record<string, number> = {};
  if (!s) return out;
  s.split(",").forEach((p) => {
    const [k, v] = p.split(":");
    const x = parseFloat(v);
    if (k && Number.isFinite(x) && x >= 0 && x <= 5) out[k.trim()] = x;
  });
  return out;
}
