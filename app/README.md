# TerraAnalog AI — Earth as a Testbed for Moon and Mars

Interactive decision-support platform (NASA Space Apps Challenge 2026) that ranks **terrestrial analog sites** for testing lunar and
Martian mission hardware, procedures and crews. Pick a Moon/Mars reference region and a mission objective → see ranked Earth sites on
a globe, with a transparent score breakdown, evidence completeness, confidence, sources, sensitivity analysis and an explicit list of
what Earth cannot replicate.

> **Data status: RESEARCH DATASET (default).** `data/research/` holds the research bot's 9 contract files (TerraAnalog research
> package `ThynkAI/terraanalog-ai @ d2e464b`, copied unmodified, plus `supplementary/`): 28 Earth analog sites, 14 Moon/Mars references, 155 criteria
> (11 reference-specific similarity features × 14 references + a separate operational-suitability score), 4,340 values
> (770 measured · 1,519 modeled · 1,673 provisional · 378 missing, never imputed) and 588 published rankings, which the engine
> reproduces exactly (max |diff| 0.0; [docs/TEST_RESULTS.md](docs/TEST_RESULTS.md)). The UI shows a *Research dataset* badge and the
> research notice on every page. `data/fixtures/` is kept as a clearly-labelled **synthetic fallback**
> (`TERRA_DATA_DIR=data/fixtures`; the *Synthetic fixture data* badge then appears). See [docs/DATA_INTEGRATION.md](docs/DATA_INTEGRATION.md).

![Earth Analog Explorer](docs/screenshots/03-earth-explorer-satellite-2d.png)

## Features
| Area | What you get |
|---|---|
| Earth Analog Explorer | MapLibre GL **globe / 2D** toggle, category-symbol markers (shape = analog type, ring = score), offline vector basemap + NASA GIBS satellite & terrain layers, filters (body, analog type, climate, geology, mission use, min score, min confidence, insufficient-evidence toggle), name or `lat, lon` geographic search with radius, ranked list, ranking chart with uncertainty whiskers, site detail panel, keyboard-accessible markers and legend, CSV export, deep links |
| Moon / Mars Reference Explorers | NASA Trek equirectangular imagery (LRO WAC mosaic, Viking MDIM 2.1) in a body-specific viewer, planetocentric/+East coordinates, south-polar stereographic inset on the IAU sphere, 14 research references (7 Moon: south polar highlands, Shackleton, Malapert, Cabeus PSR, Marius Hills pit, Mare Tranquillitatis pit, Apollo 11; 7 Mars: Jezero, Gale, Elysium Planitia, Vastitas Borealis, Planum Boreum, Arsia Mons skylights, Arcadia Planitia) with a status-class badge (candidate region / representative region / verified mission site — never "base"), Analog Match Explorer with matched Earth sites |
| Comparison Lab | radar comparison grouped by feature (only the selected reference's criteria), side-by-side table with value-type badges, transparent score breakdown, **Custom Weight Lab** (live re-ranking), **sensitivity analysis** (weight sweeps + rank stability), **Analog Discovery** clusters, feature distributions, CSV export, **generated PDF Site Comparison Report** (`/api/export/compare.pdf`, ReportLab), print view, shareable links, **deck.gl cluster-arc map** of where similar environments are |
| Recommendation engine | `POST /api/recommend`: deterministic intent parsing → structured filters → documented scoring; explains *why* and lists caveats and non-replicable factors. No generative model; cannot invent sites or facts |
| Methodology & Provenance | methodology/references markdown loaded from the data dir, live weight tables, dataset catalog, file status, validation & ID-consistency report |

## Quick start (local)

### Prerequisites
| Tool | Version | Notes |
|---|---|---|
| Python | **3.11+** (tested 3.12/3.13) | Windows: python.org installer with *Add python.exe to PATH*, or the `py` launcher |
| Node.js | **20+** (tested 22 and 26) | includes npm |
| Git | any | optional — only needed to clone |
| Docker | optional | only for `docker compose up --build`; **not** needed for local runs |
| Internet | first run | pip/npm installs; satellite/terrain/planetary imagery tiles load from NASA at runtime (the vector basemap works offline) |

### One command
**macOS / Linux**
```bash
./scripts/setup.sh            # venv + pip, npm ci, production build, then API :8000 + UI :3000 (Ctrl+C stops both)
./scripts/setup.sh --dev      # hot-reload UI instead of a production build
./scripts/setup.sh --no-start --tests   # install everything incl. pytest + Playwright Chromium, don't start
API_PORT=8001 WEB_PORT=3001 ./scripts/setup.sh
TERRA_DATA_DIR=data/fixtures ./scripts/setup.sh   # synthetic fallback data
```
**Windows (PowerShell 5.1 or 7, no Docker needed)**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Dev
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -NoStart -Tests
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -ApiPort 8001 -WebPort 3001
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -DataDir data/fixtures   # synthetic fallback data
```
Then open http://localhost:3000 (API docs: http://localhost:8000/docs).

### Manual equivalent
macOS / Linux:
```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
.venv/bin/uvicorn app.main:app --app-dir backend --port 8000
cd web && npm ci && npm run build && API_URL=http://127.0.0.1:8000 npm start   # http://localhost:3000 (PORT=xxxx to change)
```
Windows PowerShell (one command per line):
```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000   # leave running; new window for the UI:
cd web; npm ci; npm run build; $env:API_URL="http://127.0.0.1:8000"; npm start
```
`npm start` / `npm run dev` read the port from the `PORT` environment variable (default 3000) — no shell-specific syntax, so they work in cmd, PowerShell and bash.

### Docker
```bash
docker compose up --build            # UI http://localhost:3000 , API http://localhost:8000/docs
API_PORT=18000 WEB_PORT=13000 docker compose up --build -d   # other host ports
```

## Tests
```bash
make test-api   # pytest: schema, coordinates, scoring, filters, API, missing data, comparison, recommend, PDF report, research data (per-reference grouping, 588-row published-score reproduction)
make test-web   # tsc + vitest unit tests
make test-e2e   # Playwright: pages, axe accessibility, mobile viewport, explorer/compare flows
```
Latest executed results: [docs/TEST_RESULTS.md](docs/TEST_RESULTS.md).

## Repository layout
```
backend/app/        FastAPI service: models.py (schemas), loader.py (validation + ID checks), scoring.py, analysis.py, recommend.py, report.py (PDF), main.py
backend/tests/      pytest suite
data/research/      DEFAULT data: the research bot's 9 contract files (copied unmodified)
data/fixtures/      SYNTHETIC fallback versions of the 9 contract files (generated by scripts/build_fixtures.py)
data/real/          drop-in folder for other research outputs (git-ignored)
web/                Next.js 15 + React 19 + Tailwind + MapLibre GL 5 + deck.gl 9 + Recharts UI; /api/* proxied server-side to FastAPI
web/e2e/            Playwright end-to-end + axe accessibility + mobile tests
scripts/            setup.sh / setup.ps1 (one-command setup), dev.sh, build_fixtures.py, validate_data.py, verify_published.py (published-score reproduction)
docs/               architecture, data integration, deployment, pitch, demo script, presentation outline, screenshots
```

## Live demo
- App: https://terraanalog-web-cqgu.onrender.com
- API: https://terraanalog-api-cqgu.onrender.com/api/health
Free Render services sleep when idle; the first request after a pause can take about a minute.

## Documentation
- [Architecture](docs/ARCHITECTURE.md) · [Data integration guide](docs/DATA_INTEGRATION.md) · [Deployment](docs/DEPLOYMENT.md)
- [Pitch](docs/PITCH.md) · [3-minute demo script](docs/DEMO_SCRIPT.md) · [Presentation outline](docs/PRESENTATION_OUTLINE.md)
- [Test results](docs/TEST_RESULTS.md) · [Screenshots](docs/screenshots/)

## Licence
Code: [MIT](LICENSE) (copyright 2026 Deep Kanabar / ThynkAI). Data files keep their upstream licences, and research text and derived values are CC BY 4.0 unless upstream says otherwise. See *Licence and data terms* in the monorepo README (https://github.com/ThynkAI/terraanalog-ai).

## Attribution
Planetary imagery: NASA Moon Trek (LRO WAC, NASA/GSFC/ASU) and NASA Mars Trek (Viking MDIM 2.1, NASA/JPL/USGS). Earth tiles: NASA GIBS
(Blue Marble; ASTER GDEM shaded relief, NASA/METI). Land polygons: Natural Earth (public domain). Planetary coordinates: Gazetteer of
Planetary Nomenclature (IAU WGPSN / USGS). Site, reference, feature and ranking data: TerraAnalog research package (`data/research/`, see its `source_references.md` and the Data & Provenance page). The synthetic fallback in `data/fixtures/` uses twelve site entries and PREP_DRAFT factor scores from the team's AnalogSite prep pack.

Analog scores are decision-support proxies — **not** landing-site selections and **not** flight-hardware qualification.
