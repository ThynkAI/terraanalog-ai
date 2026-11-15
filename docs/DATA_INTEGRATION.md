# Scientific data integration guide

The platform reads nine files from one directory (`TERRA_DATA_DIR`, default `data/fixtures`). To use the research bot's (Bot 1) outputs:

```bash
cp /path/to/bot1/output/* data/real/
.venv/bin/python scripts/validate_data.py data/real     # schema + ID-consistency report, exit 1 on errors
TERRA_DATA_DIR=./data/real .venv/bin/uvicorn app.main:app --app-dir backend --port 8000
```
Docker: `TERRA_DATA_DIR=/app/data/real docker compose up` (the folder is mounted read-only). Files are hot-reloaded when they change.
No UI changes are needed: every label, filter option, criterion, objective, weight and reference comes from the data.

When real data is loaded, the *Synthetic fixture data* badge disappears automatically (it is shown when any site has
`provenance: "synthetic"`, any value has `value_type: "synthetic"`, or `metadata.synthetic` is true).

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
`site_id, criterion_id, value, unit, value_type, confidence, source_id, notes`
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
