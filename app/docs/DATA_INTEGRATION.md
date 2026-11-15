# Scientific data integration guide

The platform reads nine files from one directory (`TERRA_DATA_DIR`). **Default: `data/research/`** — the research bot's outputs
(package `ThynkAI/terraanalog-ai @ 195b7a8`, contract `terraanalog-app-contract-1.0.0`), copied byte-for-byte from the research
workspace. If that folder is absent the API falls back to the synthetic `data/fixtures/`; you can also select it explicitly with
`TERRA_DATA_DIR=data/fixtures` (setup.sh), `-DataDir data/fixtures` (setup.ps1) or `TERRA_DATA_DIR=/app/data/fixtures` (Docker).

## What is loaded by default (data/research)
| Item | Count |
|---|---|
| Earth analog sites (WGS84) | 28 (EA-001 … EA-028), all relevant to both bodies |
| Planetary references | 14 (MOON-REF-01…07, MARS-REF-01…07), with `status_class` candidate_region / representative_region / verified_mission_site |
| Criteria | 155 = 11 similarity features × 14 references (`<REF_ID>.<feature>`) + `operational_suitability` (weight 0, shown separately) |
| Feature values | 4,340: measured 770 · modeled 1,463 · provisional 1,647 · missing 460 (never imputed) |
| Mission objectives | 11 (`general` + 5 Moon + 5 Mars profiles) |
| Published rankings | 588 rows over 21 (reference, objective) pairs |
| Dataset catalog | 37 sources |
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
published rows independently. Current result: max |diff| 0.0111, mean 0.0031 (588/588 ≤ 0.05), completeness identical. The residual
comes from the published scores being computed before values were rounded to 3 dp for export. Ranking uses the unrounded score;
4 rows (2 pairs) differ in rank only where the published scores are tied at 2 dp.

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
| `name`, `country`, `region` | string | |
| `analog_types` | string[] | keys of `scoring_config.analog_types` (first one drives the map symbol) |
| `climate`, `geology`, `description` | string | |
| `target_bodies` | `["moon"|"mars"]` | rankings show sites relevant to the reference's body |
| `mission_objectives` | string[] | objective IDs the site supports (filter) |
| `environment` | object | free-form key → value (shown in detail panel) |
| `elevation_m` | number \| null | |
| `limitations` | string[] | |
| `imagery` | `{url, credit, license}` \| null | only licensed imagery |
| `provenance` | `measured|modeled|provisional|synthetic|mixed|published` | |
| `citations` | string[] | |
Optional `metadata` at collection level (e.g. `{"synthetic": false}`).

### 2. `planetary_reference_sites.geojson` — Points `[lon_east, lat]` in the **body's** frame (not WGS84)
`ref_id`, `body` (`moon|mars`), `name`, `region_type`, `lon_east_360` (0–360, must agree with geometry), `coordinate_system` (verbatim),
`body_radius_km`, `diameter_km`, `gazetteer_feature_id`, `description`, `traits[]`, `analog_type_affinity[]` (analog types sought), `citation`.

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

## Known data issues in the research package (reported back to the research bot)
Observed in `data/research/` as delivered; the app displays them honestly and does not patch them.
1. `dust_sediment` is missing for 231 of 392 site × reference values (59 %); `resource` 145, `thermal` 56, `abiotic_surface` 14 and
   `ruggedness` 14 missing (one site's worth each).
2. 145 (site, criterion) entries in `site_evidence.json` have zero evidence items.
3. `region` is empty and `imagery` is null for all 28 sites.
4. The 28 `operational_suitability` rows have blank `confidence`.
5. `gazetteer_feature_id` is null for all 14 references; `lon_east` is absent from properties (only geometry and `lon_east_360`).
6. 17 `dataset_catalog.csv` rows have an empty `usage`.
7. Mission-profile multipliers also list the other body's 77 criteria, so a Moon profile applies silently to Mars references
   (the app now notes this and filters objectives by body).
8. Published scores (2 dp) were computed from unrounded values, while exported values are rounded to 3 dp, which gives up to
   0.011 points of difference; ties at 2 dp make the published rank order ambiguous for 2 pairs.
9. 784 evidence citations have an empty author segment (`"… -  et al. (2022) …"`), and 27 evidence statements contain empty
   parentheses `()` left over from text extraction.
10. Climate strings are unique long sentences per site, so they cannot work as a categorical filter (the UI uses a "contains" box).
11. The handoff describes an `outputs/` layout and extra files (`data_gaps.csv`, `radar_chart_data.json`, `sensitivity_summary.json`,
    `mc_*` columns, site bounds) that are not in the 9 delivered contract files.
