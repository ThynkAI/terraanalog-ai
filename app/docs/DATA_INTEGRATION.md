# Scientific data integration guide

The platform reads nine files from one directory (`TERRA_DATA_DIR`). **Default: `data/research/`** — the research bot's outputs
(package `ThynkAI/terraanalog-ai @ d2e464b`, contract `terraanalog-app-contract-1.0.0`), copied byte-for-byte from the research
workspace, plus optional `supplementary/` extras. If that folder is absent the API falls back to the synthetic `data/fixtures/`; you can also select it explicitly with
`TERRA_DATA_DIR=data/fixtures` (setup.sh), `-DataDir data/fixtures` (setup.ps1) or `TERRA_DATA_DIR=/app/data/fixtures` (Docker).

## What is loaded by default (data/research)
| Item | Count |
|---|---|
| Earth analog sites (WGS84) | 28 (EA-001 … EA-028), all relevant to both bodies |
| Planetary references | 14 (MOON-REF-01…07, MARS-REF-01…07), with `status_class` candidate_region / representative_region / verified_mission_site |
| Criteria | 155 = 11 similarity features × 14 references (`<REF_ID>.<feature>`) + `operational_suitability` (weight 0, shown separately) |
| Feature values | 4,340: measured 770 · modeled 1,519 · provisional 1,673 · missing 378 (never imputed) |
| Mission objectives | 11 (`general` + 5 Moon + 5 Mars profiles) |
| Published rankings | 588 rows over 21 (reference, objective) pairs |
| Dataset catalog | 40 sources |
`python scripts/validate_data.py data/research` exits 0 (no schema or ID-consistency errors).

### Per-reference criteria (`<REF_ID>.<feature>`)
The research config gives every reference its own 11 criteria (value = 5 × similarity of the Earth site *to that reference*), with
extra keys `ref_id` and `feature`. The engine handles this generically:
* `ScoringConfig.active_criteria(ref_id)` = that reference's criteria + shared criteria (no `ref_id`); scores, breakdowns, comparison
  matrix, CSV/PDF, sensitivity sweeps, clustering and the evidence inspector use only these, so other references' criteria never leak in.
* Everything is grouped by `feature` with readable labels derived from the data (`"Ice / permafrost agreement - …"` → *Ice / permafrost
  agreement*). Weight-lab sliders and `w=` deep-link weights are keyed by feature (`w=ice:2,aridity:0.5`), and criterion ids still work.
* If no reference is selected the body's `default_reference` is used (MOON-REF-01 / MARS-REF-01) and the API returns
  `reference_defaulted: true` plus a note that the UI displays. Choosing a Moon objective with a Mars reference (or vice versa) is
  allowed but flagged with a note; the UI lists only objectives for the reference's body.
* Old fixture-style configs (shared criteria without `ref_id`) work unchanged; the 68 original tests still run on `data/fixtures`.

### Published-score reproduction
`python scripts/verify_published.py data/research --json docs/test-results/published_reproduction.json` recomputes all 588
published rows independently. Current result (Final submission pass): all **588 ranks agree**, maximum unrounded |diff| **0.00004737** points
(older four-decimal summaries displayed this residual as 0.0). Completeness is identical on every row.

## Loading other research outputs
```bash
cp /path/to/bot1/output/* data/real/
.venv/bin/python scripts/validate_data.py data/real     # schema + ID-consistency report, exit 1 on errors
TERRA_DATA_DIR=./data/real .venv/bin/uvicorn app.main:app --app-dir backend --port 8000
```
Docker: `TERRA_DATA_DIR=/app/data/real docker compose up` (the folder is mounted read-only). Files are hot-reloaded when they change.
No UI changes are needed: every label, filter option, criterion, objective, weight and reference comes from the data.

With real data the *Synthetic fixture data* badge is replaced by a *Research dataset* badge and the `metadata.notice` banner. The synthetic badge is shown only when any site has
`provenance: "synthetic"`, any value has `value_type: "synthetic"`, or `metadata.synthetic` is true.

## File-by-file contract
Lines beginning with `#` at the top of CSV files are ignored (used for warning banners).

### 1. `earth_analog_sites.geojson` — FeatureCollection of Points, `[lon, lat]` WGS84
| property | type | notes |
|---|---|---|
| `site_id` | string `^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$` | unique; key used everywhere |
| `name`, `country`, `region` | string | `region` is the Natural Earth admin-1 name; `region_source` explains the match |
| `analog_types` | string[] | keys of `scoring_config.analog_types` (first one drives the map symbol) |
| `climate`, `geology`, `description` | string | `climate` is the long provenance sentence |
| `climate_class`, `aridity_class` | string | Köppen–Geiger (Peel et al. 2007) and UNEP P/ET0 aridity of the ERA5 cell; show them together (polar sites can be classed humid) |
| `climate_class_source` | string | method/source sentence for those classes |
| `target_bodies` | `["moon"|"mars"]` | rankings show sites relevant to the reference's body |
| `mission_objectives` | string[] | objective IDs the site supports (filter) |
| `environment` | object | free-form key → value (shown in detail panel) |
| `elevation_m` | number \| null | |
| `limitations` | string[] | |
| `imagery` | `{url, credit, license, license_url?, attribution_page?, source?}` \| null | licensed imagery with author/licence attribution; may be null |
| `data_confidence` | number \| null | site-level 0–1 confidence |
| `provenance` | `measured|modeled|provisional|synthetic|mixed|published` | |
| `citations` | string[] | |
Optional `metadata` at collection level (e.g. `{"synthetic": false}`).

### 2. `planetary_reference_sites.geojson` — Points `[lon_east, lat]` in the **body's** frame (not WGS84)
`ref_id`, `body` (`moon|mars`), `name`, `region_type`, `lon_east` (geometry; also in properties), `lon_east_360` (0–360, must agree with geometry), `coordinate_system` (verbatim),
`body_radius_km`, `diameter_km`, `gazetteer_feature_id`, `gazetteer_feature_name`, `gazetteer_match`, `gazetteer_url`, `gazetteer_note`, `description`, `traits[]`, `analog_type_affinity[]` (analog types sought), `citation`.
A reference may have no Gazetteer id (the lunar south pole region is not a named IAU feature); `gazetteer_note` explains that.

### 3. `analog_features.csv` — long format, one row per site × criterion
`site_id, criterion_id, value, unit, value_type, confidence, source_id, notes` (extra research columns such as `ref_id`, `feature` are accepted)
* `value` on the config scale (default 0–5). **Empty = missing**; it lowers evidence completeness and is never imputed.
* `value_type`: `measured | modeled | provisional | synthetic | missing`. `confidence` 0–1 (optional; default from config by type).
* `source_id` should exist in `dataset_catalog.csv`.

### 4. `analog_rankings.csv` — Bot 1's published rankings (optional)
`ref_id, objective, site_id, score, rank, completeness, method_version, provenance` — shown next to live scores.

### 5. `dataset_catalog.csv`
`source_id, name, provider, url, license, data_type, usage, status, provenance, notes`

### 6. `site_evidence.json`
```json
{"meta": {...}, "evidence": {"<site_id>": {"<criterion_id>": [
  {"statement": "...", "source_id": "MODIS-LST", "value_type": "measured", "confidence": 0.8, "citation": "Author (Year) ... doi:..."}]}}}
```

### 7. `scoring_config.json`
`scale_min`, `scale_max`, `min_completeness`, `criteria[] {id,label,description,earth_proxy,source_families}`,
`body_weights {moon:{criterion:w}, mars:{...}}`, `reference_multipliers {ref_id:{criterion:m}}`,
`objectives[] {id,label,description,multipliers}`, `default_objective`, `default_reference {moon,mars}`,
`value_type_confidence`, `non_replicable {moon:[...], mars:[...]}`, `analog_types {id: label}`.
Validation rejects unknown criteria in weights/multipliers, negative weights and duplicate IDs.

### 8–9. `scientific_methodology.md`, `source_references.md`
Rendered on the Methodology and Data & Provenance pages.

## Consistency checks performed (see `/api/validation` and the Data page)
* feature/evidence/ranking `site_id`s exist in the sites file; ranking `ref_id`s and objectives exist;
* criteria used in features are defined in the config; reference multipliers refer to existing references; default references exist;
* `source_id`s used are catalogued; sites with no features are flagged (they cannot be scored);
* duplicate IDs, out-of-range coordinates/values, inconsistent longitudes → row/feature rejected with a reported reason.

## Regenerating fixtures
`make fixtures` (runs `scripts/build_fixtures.py`). The script documents exactly which values are real (Gazetteer coordinates),
provisional (AnalogSite PREP_DRAFT expert judgement) or synthetic.

## Optional `supplementary/` extras (not part of the 9-file contract)
If `data/research/supplementary/` is present the loader reads it; missing files are not errors (fixtures have none).

| file | how the app uses it |
|---|---|
| `analog_profile_rankings.csv` | Published per-profile ranks (best matched reference) with Monte Carlo score/rank intervals, shown on the site detail page |
| `sensitivity_summary.json` | Published MC / OAT / LOFO results for the selected mission profile, shown on the Sensitivity tab above the live weight sweep |
| `radar_chart_data.json` | Published top-5 per-feature similarities (0–1) for the selected profile, shown as a radar on the Sensitivity tab |
| `data_gaps.csv` | Per-site missing inputs and recommended field measurements, shown on the site detail page |
| `earth_analog_site_bounds.geojson` | Loaded for completeness; approximate site extents |
| `README.md` | File inventory |

## Known data issues in the research package (export @ d2e464b)
The 15 November 2026 re-export (research commits `3be5e92` fixes, `d2e464b` export) resolved the previously reported issues
(historical, before that re-export):
empty `region`/`imagery`, blank operational confidence, null Gazetteer ids and missing `lon_east` properties, empty catalog `usage`,
empty citation authors and leftover `()`, unique-sentence climate filters, rounding drift in published scores (historical max |diff| was 0.0111
with two tie-related rank swaps), empty evidence items, cross-body profile multipliers, and the missing `outputs/` extras.
`scripts/validate_data.py data/research` exits 0 with **0 errors and 0 warnings**. All 588 published ranks match.

The app displays the remaining gaps honestly and does not invent or impute values.

1. **378 missing feature values**, each with an evidence item of the form `No evidence: value missing - <reason>`. None are imputed.
   By feature (of 392 site × reference cells): `dust_sediment` 203, `resource` 119, `thermal` 28, `abiotic_surface` 14, `ruggedness` 14.
2. **No licensed imagery** for EA-012 Salar de Antofalla (Puna de Atacama) and EA-013 Dresser Formation (North Pole Dome, Pilbara).
   The other 26 sites have Wikimedia Commons images with licence and author credit.
3. **The lunar south pole (MOON-REF-01)** has no IAU Gazetteer feature (`gazetteer_match: none`; note: "The lunar south pole region is not a named IAU feature").
   The other 13 references have a `gazetteer_feature_id`, name, URL and `lon_east`.
