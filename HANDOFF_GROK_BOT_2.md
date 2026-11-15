# Handoff to Grok Bot 2: TerraAnalog AI web application

**From:** TerraAnalog AI data/science build (Grok Bot), 2026-11-15
**Repo:** `ThynkAI/terraanalog-ai` (private), branch `main`. The package root is the repo root.
**Your job:** build an interactive web app that *displays and explains* these results. Do not recompute science in the front end, except to reproduce scores from `sim_*` columns for the "what-if weights" feature described below.

## 1. Non-negotiable display rules

1. Every score must be shown with its profile name, `evidence_completeness` and `confidence`. Never show a bare number labelled "Moon-likeness" or "Mars equivalence".
2. Show the disclaimer from `properties.disclaimer` on the map and on every site page: *"Scores rank relative analog fidelity for one mission objective; not a measure of planetary equivalence."*
3. **Fidelity and operational suitability are separate.** Use two separate gauges or columns, and never sum or average them.
4. Planetary references carry `status_class` ∈ {verified_mission_site, candidate_region, representative_region} and `not_an_approved_base_site: true`. Show the class as a badge. Never label any reference a "base".
5. Null means **unavailable**. Render it as "—" with a tooltip ("not available: see data gaps"), and never as 0. The radar PNGs plot missing as 0 for drawing only. In the app, grey out those axes instead.
6. Provenance must be visible. Each value gets a small chip: measured / derived / modeled / literature / hypothesized. Hypothesized tags get a dashed outline.
7. Planetary coordinates are **not WGS84**. Moon features use IAU_2015:30100, and Mars features use IAU_2015:49900. Render them on separate Moon and Mars basemaps, never on the Earth map.

## 2. Layers and files

| Layer / view | File | Geometry / CRS | Key |
|---|---|---|---|
| Earth sites (points) | `outputs/earth_analog_sites.geojson` | Point, EPSG:4326 | `id` = `site_id` |
| Earth site extents | `outputs/earth_analog_site_bounds.geojson` | Polygon, EPSG:4326 (approximate bbox, `boundary_status`) | `id` |
| Moon references | `outputs/planetary_reference_sites.geojson` filtered `body == "Moon"` | Point, IAU_2015:30100 lon/lat | `id` = `ref_id` |
| Mars references | same file, `body == "Mars"` | Point, IAU_2015:49900 lon/lat | `id` |
| Rankings table | `outputs/analog_rankings.csv` | — | (`site_id`, `mission_profile`) |
| Site detail | `outputs/analog_features.csv` + `outputs/site_evidence.json` | — | `site_id` |
| Radar charts | `outputs/radar_chart_data.json` (top 5 per profile) or the `sim_*` columns | — | profile → site |
| Uncertainty | `mc_score_p05/p95`, `mc_rank_p05/p95`, `mc_top5_probability`; `outputs/sensitivity_summary.json` | — | profile |
| Data gaps | `outputs/data_gaps.csv` | — | `site_id` |
| Dataset catalog / sources | `outputs/dataset_catalog.csv`, `source_references.md` | — | `dataset_id` |
| Static figures | `outputs/figures/*.svg` (preferred) / `*.png` | — | — |

Basemap suggestions: an Earth basemap of your choice (attribute it). For Moon and Mars, use NASA Trek WMTS tile services (https://trek.nasa.gov/moon/, https://trek.nasa.gov/mars/). Check their current tile endpoints and terms before shipping. Note that they serve equirectangular planetocentric lon/lat, which is consistent with the reference coordinates.

Full column dictionary and JSON Schemas: `data_contract.md`, `schemas/*.schema.json`. Validate the files against the schemas in CI.

## 3. Recommended screens

1. **Map + profile selector.** Offer 10 profiles (`scoring_config.mission_profiles`: 5 MOON_*, 5 MARS_*). Size points by `scores[profile].fidelity_score`, set opacity from `evidence_completeness`, and colour by `group` (baseline / established / candidate).
2. **Ranking table** per profile: rank, site, score with a p05–p95 band, completeness, confidence, top-5 probability and operational score (in a separate column), plus the matched reference.
3. **Site page:**
   * Key facts with provenance chips.
   * A radar chart against the matched reference.
   * Evidence quotes with source links from `site_evidence.json`.
   * Limitations and data gaps.
   * Operational breakdown (`sensitivity_summary.operational_components`).
4. **Reference page** (Moon or Mars basemap): status badge, terrain, temperature with provenance, illumination, ice evidence, hazards and mission objectives, each with its source.
5. **Compare view:** two to four sites side by side using `sim_*` and `similarity_matrix_site_x_site.csv`.
6. **What-if weights (optional):** a slider per feature weight. Recompute `100·Σw·sim/Σw` over non-null `sim_*` from `analog_rankings.csv`. This matches the engine within 0.01 (validation check `score_recalculation`). Label the result "user-weighted, exploratory".
7. **About / methods:** render `scientific_methodology.md`, `validation_report.md` and `source_references.md`.

## 4. Current results snapshot

<!-- RESULTS:START -->
| Profile | #1 (score, completeness) | #2 | #3 | MC mean Spearman |
|---|---|---|---|---|
| MOON_ISRU_ICE | EA-002 Haughton impact crater (57.4, 1.00) | EA-004 McMurdo Dry Valleys (45.6, 0.90) | EA-005 Bockfjorden Volcanic Complex (42.0, 1.00) | 0.914 |
| MOON_ROVER_MOBILITY | EA-028 Mars Desert Research Station area (77.2, 0.95) | EA-008 Timanfaya volcanic field (68.5, 0.80) | EA-011 Salar de Uyuni (67.3, 0.75) | 0.925 |
| MOON_EVA_HABITAT | EA-004 McMurdo Dry Valleys (50.9, 0.75) | EA-005 Bockfjorden Volcanic Complex (44.7, 1.00) | EA-002 Haughton impact crater (39.5, 1.00) | 0.938 |
| MOON_FIELD_GEOLOGY | EA-024 Mistastin Lake impact structure (51.1, 1.00) | EA-002 Haughton impact crater (44.5, 1.00) | EA-023 Meteor Crater (42.4, 1.00) | 0.952 |
| MOON_LAVA_TUBE | EA-009 Cueva de los Verdes lava tube (74.3, 0.95) | EA-016 Undara lava tubes (69.1, 0.95) | EA-008 Timanfaya volcanic field (58.7, 0.90) | 0.97 |
| MARS_ISRU_ICE | EA-002 Haughton impact crater (65.7, 1.00) | EA-004 McMurdo Dry Valleys (64.0, 0.80) | EA-005 Bockfjorden Volcanic Complex (43.2, 0.85) | 0.917 |
| MARS_ROVER_MOBILITY | EA-028 Mars Desert Research Station area (71.5, 0.95) | EA-008 Timanfaya volcanic field (62.3, 0.95) | EA-006 Holuhraun lava field (61.7, 0.95) | 0.946 |
| MARS_EVA_HABITAT | EA-002 Haughton impact crater (57.2, 0.95) | EA-018 Qaidam Basin (53.9, 0.95) | EA-028 Mars Desert Research Station area (45.8, 0.95) | 0.925 |
| MARS_ASTROBIO_SEDIMENTS | EA-028 Mars Desert Research Station area (61.6, 1.00) | EA-003 Death Valley (51.6, 1.00) | EA-018 Qaidam Basin (50.3, 1.00) | 0.958 |
| MARS_LAVA_TUBE | EA-009 Cueva de los Verdes lava tube (57.5, 0.95) | EA-016 Undara lava tubes (51.4, 0.95) | EA-008 Timanfaya volcanic field (45.3, 0.95) | 0.953 |

Validation: **42/42 checks passed** (see `outputs/validation_report.md`).

Scores are relative, profile-specific fidelity (0-100), not planetary equivalence. Completeness = share of profile weight with data.
<!-- RESULTS:END -->

## 5. Known limitations to surface in the UI

* Access distances use Natural Earth major roads, because OSM was blocked. They are **upper bounds**, and Antarctica is censored (`road_distance_censored_gt_m`).
* ERA5 (0.25°) and CHELSA are modeled climate. SoilGrids is null on bare rock and ice for several sites.
* Categorical tags come from Wikipedia text. Hypothesized tags are flagged, and an evidence-strict re-ranking is provided (`sensitivity_summary.strict_evidence_variant`).
* MODIS LST, Landsat, Sentinel-2, HiRISE, CTX and CRISM were **not** ingested.
* Expected-role check: Río Tinto (EA-026) does **not** rank in the top quartile for MARS_ASTROBIO_SEDIMENTS, even though the literature analog role exists. Its acid-mine chemistry is not captured by the surface features. Show this honestly rather than tuning weights.

## 6. Updating data

Run `python scripts/run_all.py --offline` after editing `config/*.json`. Run it without `--offline` to re-retrieve (see README "Regenerating the raw data"). All outputs, the README and this file's snapshot regenerate automatically. Keep IDs stable: add new sites as `EA-029`+ and never renumber.
