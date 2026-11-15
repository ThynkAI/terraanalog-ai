# Architecture

```
 Browser ──► Next.js 15 (web/)  ──/api/* server-side proxy──►  FastAPI (backend/)  ──►  DATA DIR (9 contract files)
           React 19 · Tailwind      app/api/[...path]/route.ts      loader → validation        GeoJSON · CSV · JSON · MD
           MapLibre GL 5 (globe)    API_URL read at runtime         scoring · analysis         (data/research by default; data/fixtures synthetic fallback)
           Recharts                                                 recommend
```

## Why this shape (simplest robust option)
* **FastAPI owns all science**: loading, validation, ID consistency, scoring, sensitivity, clustering and recommendations live in one
  Python package with one test suite. There is exactly one implementation of the scoring formula (no TS duplicate to drift).
* **Next.js owns presentation** and proxies `/api/*` through a route handler, so the browser talks to a single origin (no CORS setup,
  backend URL never shipped to the client, `API_URL` changeable at container runtime).
* **No database.** The dataset is small (tens–hundreds of sites); files are parsed into memory and **hot-reloaded when their mtime
  changes**, so Bot 1 can overwrite files without restarts. PostGIS would be the next step only if datasets grow to raster/AOI scale.
* **deck.gl only where it adds something**: the Earth Analog Explorer keeps MapLibre's native globe + DOM markers (keyboard-focusable,
  screen-reader friendly). The Comparison Lab's *Analog Discovery* tab adds a deck.gl 9 map (`@deck.gl/mapbox` `MapboxOverlay` on an
  offline MapLibre basemap) with an **ArcLayer** linking each feature-space cluster member to its anchor (highest score vs the selected
  reference), a **ScatterplotLayer** (colour = cluster, radius = score) and a **TextLayer** for anchors. It shows that similar
  environments are spread across continents, which the 2-D feature scatter cannot. Only Earth (WGS84) coordinates are drawn; planetary
  references are never projected onto Earth. Anchor/arc logic is a pure function (`web/lib/clusterArcs.ts`) with unit tests.
* **PDF reports are generated server-side** with ReportLab (`backend/app/report.py`, `GET /api/export/compare.pdf`): same inputs and
  validation as `/api/compare`; includes the synthetic-data banner, reference coordinates + citation, scores with plausible ranges,
  completeness/confidence, criterion matrix with value types (missing shown as missing), per-criterion breakdown with sources,
  site limitations and what Earth cannot replicate. The browser print view remains as a secondary option.

## Backend modules (`backend/app/`)
| Module | Responsibility |
|---|---|
| `config.py` | `TERRA_DATA_DIR` (default `data/research`, falls back to `data/fixtures`), `TERRA_CORS_ORIGINS`, list of contract files |
| `models.py` | Pydantic schemas for every contract file (ranges, ID patterns, lon/lon_360 agreement, missing-value semantics, config integrity) |
| `loader.py` | Loads each file independently; invalid rows/features are rejected and reported, missing files become empty; cross-file ID checks; mtime-based cache |
| `scoring.py` | Weighted score over the reference's active criteria (`<REF_ID>.<feature>` + shared), completeness, confidence, plausible range, ranking on the unrounded score, feature-keyed weight parsing |
| `analysis.py` | Feature-keyed weight sweeps / rank stability; mask-aware k-means clusters on per-reference feature vectors |
| `recommend.py` | Keyword intent parser → structured filters → scoring → explanation assembly |
| `main.py` | REST endpoints with validated parameters |

## Scoring (single source of truth)
`w_c = body_weight[body][c] × reference_multiplier[ref][c] × objective_multiplier[obj][c] × user_multiplier[c]`

`score = 100 · Σ_present w_c·x̂_c / Σ_present w_c`, `completeness = Σ_present w_c / Σ_all w_c`,
range = missing criteria at scale min/max, `confidence = completeness × weighted mean value confidence`.
Below `min_completeness` (0.70) → status `insufficient_evidence`, no point score, unranked. Missing values are never imputed.

## API
| Method & path | Purpose |
|---|---|
| `GET /api/health` | liveness + synthetic flag |
| `GET /api/meta` | criteria, objectives, weights, analog types, data status |
| `GET /api/validation` | file status + validation/ID-consistency issues |
| `GET /api/sites` | filter (body, analog_type, climate, geology, mission_objective, min_score, min_confidence, q, near+radius_km), sort, scores vs `ref_id`/`objective`/`weights` |
| `GET /api/sites/{id}` | detail, feature values, evidence, score breakdown, scores vs every reference, non-replicable factors |
| `GET /api/planetary-references[/{ref_id}]` | references (+ ranked Earth matches) |
| `GET /api/rankings` | ranking for `ref_id` × `objective` × custom `weights` (+ published rank from analog_rankings.csv) |
| `GET /api/compare` | 1–6 sites side by side; `GET /api/export/compare.csv` CSV report |
| `GET /api/sensitivity` | weight sweeps and rank stability |
| `GET /api/clusters` | analog discovery clusters |
| `GET /api/features` | all criterion values with value types |
| `GET /api/datasets` | dataset catalog |
| `GET /api/docs/{methodology|references}` | markdown documents from the data dir |
| `POST /api/recommend` | explainable recommendations |

Parameters are validated (regex IDs, numeric ranges, weight syntax); unknown IDs → 404, bad values → 422, missing scoring config → 503.
No secrets are required or exposed; error messages never include filesystem paths.

## Frontend (`web/`)
* App Router pages: `/` overview, `/explorer`, `/moon`, `/mars`, `/compare` (tabs: compare · weights · sensitivity · discovery), `/methodology`, `/data`, `/impact`.
* All view state is in the URL (shareable deep links: `?site=…&ref=…&obj=…&compare=…&w=…&tab=…`).
* `EarthMap` (MapLibre GL 5): style built in code — offline Natural Earth land + graticule, optional NASA GIBS raster layers; globe/mercator.
* `PlanetViewer`: SVG equirectangular viewer that places NASA Trek WMTS tiles from their *geographic* tile matrix (correct for plate carrée,
  which is why MapLibre's Web-Mercator pipeline is **not** used for Moon/Mars), plus a south-polar stereographic inset on the body's IAU sphere.
* Accessibility: skip link, one `<h1>` per page, labelled controls, focusable markers, ARIA tabs, meter roles, reduced-motion support, axe-tested.

## Coordinate conventions
* Earth: WGS84 lon/lat (RFC 7946 GeoJSON). Distances (geographic search) use haversine on the mean Earth radius — Earth only.
* Moon/Mars: planetocentric latitude, east-positive longitude as published by the Gazetteer (stored in −180…180 plus 0…360), IAU mean radii
  1737.4 km / 3389.5 km. Polar distances and the stereographic inset use those spheres. No WGS84/ellipsoid math touches planetary geometry.
