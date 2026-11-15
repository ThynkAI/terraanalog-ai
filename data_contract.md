# TerraAnalog AI data contract (v1.0.0)

This contract is for **Grok Bot 2** (web-app developer). Files live in `outputs/` and JSON Schemas (draft 2020-12) in `schemas/`.

## Conventions

* **IDs are stable:** `EA-001`…`EA-028` (Earth), `MOON-REF-01`…`07`, `MARS-REF-01`…`07`. They will never be reused for a different place.
* **Nulls:** an empty CSV cell and JSON `null` both mean *unavailable*. Never coerce them to 0.
* **Units:** SI throughout (m, K, fractions 0–1, mm/yr for precipitation as is standard for climate data). Celsius columns are suffixed `_c`, and Kelvin is `temperature_K`.
* **CRS:** Earth files use WGS84 lon/lat (EPSG:4326, RFC 7946). `planetary_reference_sites.geojson` uses **body-fixed planetocentric lon/lat** (IAU_2015:30100 Moon, IAU_2015:49900 Mars). Never place these on an Earth basemap.
* **Provenance classes:** measured | derived | modeled | literature | hypothesized | unavailable (see `scientific_methodology.md`).
* **Score semantics:** `fidelity_score` (0–100) is a per-mission-profile relative ranking aid, **not** a measure of planetary equivalence. Always display it together with `evidence_completeness` and `confidence`. Keep `operational_score` visually separate.

## File inventory

| File | Format | Key | Description |
|---|---|---|---|
| outputs/earth_analog_sites.geojson | GeoJSON FeatureCollection (Point) | `id` = site_id | Map layer with summary properties and per-profile `scores` object |
| outputs/earth_analog_site_bounds.geojson | GeoJSON (Polygon) | `id` | Approximate bounding boxes (boundary_status = approximate_bbox) |
| outputs/planetary_reference_sites.geojson | GeoJSON (Point, body CRS) | `id` = ref_id | Moon/Mars reference layer |
| outputs/analog_features.csv | CSV | site_id | All Earth features (dictionary below) |
| outputs/planetary_features.csv | CSV | ref_id | Reference features |
| outputs/analog_rankings.csv | CSV | (site_id, mission_profile) | Scores, ranks, uncertainty, per-feature similarities |
| data/processed/pair_scores.csv | CSV | (site_id, ref_id, mission_profile) | Score against every reference in each profile |
| outputs/site_evidence.json | JSON | earth_sites[site_id], planetary_references[ref_id] | Per-tag quotes and URLs, numeric sources, limitations, confidence |
| outputs/scoring_config.json | JSON | - | Copy of config/scoring_config.json used for this run |
| outputs/radar_chart_data.json | JSON | profiles[profile] → top 5 | Radar-chart series (feature → similarity) |
| outputs/similarity_matrix_site_x_reference.csv | CSV matrix | site_id × ref_id | Equal-weight mean similarity (0–100) |
| outputs/similarity_matrix_site_x_site.csv | CSV matrix | site_id × site_id | Cosine similarity of standardised features |
| outputs/analytics_summary.json | JSON | - | PCA, clusters, baseline comparison |
| outputs/sensitivity_summary.json | JSON | profiles[profile] | Monte Carlo, OAT, LOFO, strict-evidence results |
| outputs/data_gaps.csv | CSV | site_id | Missing values, hypothesized tags, recommended field measurements |
| outputs/dataset_catalog.csv | CSV | dataset_id | Dataset catalog |
| outputs/validation_report.md / validation_results.json | MD / JSON | - | Validation outcome |

## Column dictionary: `analog_features.csv`

| column | type | unit | provenance | description |
|---|---|---|---|---|
| `site_id` | string | - | - | Stable Earth site ID `EA-NNN` (primary key) |
| `name` | string | - | literature | Site name / country or territory |
| `country` | string | - | literature | Site name / country or territory |
| `lat` | number | deg (WGS84) | literature | Sampling-point latitude / longitude, EPSG:4326 |
| `lon` | number | deg (WGS84) | literature | Sampling-point latitude / longitude, EPSG:4326 |
| `group` | string | - | - | `baseline` (Atacama, Haughton, Death Valley) / `established` (documented analog use) / `candidate` |
| `coord_kind` | string | - | literature | What the point represents and where it came from |
| `coord_source` | string | - | literature | What the point represents and where it came from |
| `elev_point_m` | number | m (EGM2008) | measured | Copernicus DEM elevation at the sampling point |
| `t30m_r2km_elev_mean_m` | number | see suffix | derived | Terrain on 30 m local AEQD grid within 2 km: elev_mean_m, relief_m (p99-p1), slope_median_deg, slope_p90_deg, slope_frac_lt15 (0-1), tri_median_m (Riley TRI), valid_fraction |
| `t30m_r2km_relief_m` | number | see suffix | derived | Terrain on 30 m local AEQD grid within 2 km: elev_mean_m, relief_m (p99-p1), slope_median_deg, slope_p90_deg, slope_frac_lt15 (0-1), tri_median_m (Riley TRI), valid_fraction |
| `t30m_r2km_slope_median_deg` | number | see suffix | derived | Terrain on 30 m local AEQD grid within 2 km: elev_mean_m, relief_m (p99-p1), slope_median_deg, slope_p90_deg, slope_frac_lt15 (0-1), tri_median_m (Riley TRI), valid_fraction |
| `t30m_r2km_slope_p90_deg` | number | see suffix | derived | Terrain on 30 m local AEQD grid within 2 km: elev_mean_m, relief_m (p99-p1), slope_median_deg, slope_p90_deg, slope_frac_lt15 (0-1), tri_median_m (Riley TRI), valid_fraction |
| `t30m_r2km_slope_frac_lt15` | number | see suffix | derived | Terrain on 30 m local AEQD grid within 2 km: elev_mean_m, relief_m (p99-p1), slope_median_deg, slope_p90_deg, slope_frac_lt15 (0-1), tri_median_m (Riley TRI), valid_fraction |
| `t30m_r2km_tri_median_m` | number | see suffix | derived | Terrain on 30 m local AEQD grid within 2 km: elev_mean_m, relief_m (p99-p1), slope_median_deg, slope_p90_deg, slope_frac_lt15 (0-1), tri_median_m (Riley TRI), valid_fraction |
| `t30m_r2km_valid_fraction` | number | see suffix | derived | Terrain on 30 m local AEQD grid within 2 km: elev_mean_m, relief_m (p99-p1), slope_median_deg, slope_p90_deg, slope_frac_lt15 (0-1), tri_median_m (Riley TRI), valid_fraction |
| `t90m_r5km_elev_mean_m` | number | see suffix | derived | Same metrics on 90 m grid within 5 km (matched baseline for Moon references) |
| `t90m_r5km_relief_m` | number | see suffix | derived | Same metrics on 90 m grid within 5 km (matched baseline for Moon references) |
| `t90m_r5km_slope_median_deg` | number | see suffix | derived | Same metrics on 90 m grid within 5 km (matched baseline for Moon references) |
| `t90m_r5km_slope_p90_deg` | number | see suffix | derived | Same metrics on 90 m grid within 5 km (matched baseline for Moon references) |
| `t90m_r5km_slope_frac_lt15` | number | see suffix | derived | Same metrics on 90 m grid within 5 km (matched baseline for Moon references) |
| `t90m_r5km_tri_median_m` | number | see suffix | derived | Same metrics on 90 m grid within 5 km (matched baseline for Moon references) |
| `t90m_r5km_valid_fraction` | number | see suffix | derived | Same metrics on 90 m grid within 5 km (matched baseline for Moon references) |
| `t450m_r15km_elev_mean_m` | number | see suffix | derived | Same metrics on 450 m grid within 15 km (matched baseline for Mars references) |
| `t450m_r15km_relief_m` | number | see suffix | derived | Same metrics on 450 m grid within 15 km (matched baseline for Mars references) |
| `t450m_r15km_slope_median_deg` | number | see suffix | derived | Same metrics on 450 m grid within 15 km (matched baseline for Mars references) |
| `t450m_r15km_slope_p90_deg` | number | see suffix | derived | Same metrics on 450 m grid within 15 km (matched baseline for Mars references) |
| `t450m_r15km_slope_frac_lt15` | number | see suffix | derived | Same metrics on 450 m grid within 15 km (matched baseline for Mars references) |
| `t450m_r15km_tri_median_m` | number | see suffix | derived | Same metrics on 450 m grid within 15 km (matched baseline for Mars references) |
| `t450m_r15km_valid_fraction` | number | see suffix | derived | Same metrics on 450 m grid within 15 km (matched baseline for Mars references) |
| `wc_frac_bare_sparse_r5km` | number | fraction 0-1 | derived | ESA WorldCover 2021 class fraction within 5 km |
| `wc_frac_snow_ice_r5km` | number | fraction 0-1 | derived | ESA WorldCover 2021 class fraction within 5 km |
| `wc_frac_water_r5km` | number | fraction 0-1 | derived | ESA WorldCover 2021 class fraction within 5 km |
| `wc_frac_tree_r5km` | number | fraction 0-1 | derived | ESA WorldCover 2021 class fraction within 5 km |
| `wc_frac_shrub_r5km` | number | fraction 0-1 | derived | ESA WorldCover 2021 class fraction within 5 km |
| `wc_frac_grass_r5km` | number | fraction 0-1 | derived | ESA WorldCover 2021 class fraction within 5 km |
| `wc_frac_crop_r5km` | number | fraction 0-1 | derived | ESA WorldCover 2021 class fraction within 5 km |
| `wc_frac_built_r5km` | number | fraction 0-1 | derived | ESA WorldCover 2021 class fraction within 5 km |
| `wc_frac_wetland_r5km` | number | fraction 0-1 | derived | ESA WorldCover 2021 class fraction within 5 km |
| `wc_frac_moss_lichen_r5km` | number | fraction 0-1 | derived | ESA WorldCover 2021 class fraction within 5 km |
| `abiotic_fraction_r5km` | number | fraction 0-1 | derived | (bare/sparse + snow/ice) / land fraction within 5 km |
| `chelsa_maat_c` | number | °C | modeled | CHELSA V2.1 1981-2010 bio1 / bio5 / bio6 / bio7 |
| `chelsa_tmax_warmest_c` | number | °C | modeled | CHELSA V2.1 1981-2010 bio1 / bio5 / bio6 / bio7 |
| `chelsa_tmin_coldest_c` | number | °C | modeled | CHELSA V2.1 1981-2010 bio1 / bio5 / bio6 / bio7 |
| `chelsa_t_annual_range_c` | number | °C | modeled | CHELSA V2.1 1981-2010 bio1 / bio5 / bio6 / bio7 |
| `chelsa_precip_mm_yr` | number | mm/yr | modeled | CHELSA bio12 annual precipitation |
| `era5_t_mean_c` | number | °C | modeled | ERA5 1991-2020 daily (Open-Meteo): mean, 1st pct of Tmin, 99th pct of Tmax, mean diurnal range |
| `era5_t_min_p01_c` | number | °C | modeled | ERA5 1991-2020 daily (Open-Meteo): mean, 1st pct of Tmin, 99th pct of Tmax, mean diurnal range |
| `era5_t_max_p99_c` | number | °C | modeled | ERA5 1991-2020 daily (Open-Meteo): mean, 1st pct of Tmin, 99th pct of Tmax, mean diurnal range |
| `era5_diurnal_range_c` | number | °C | modeled | ERA5 1991-2020 daily (Open-Meteo): mean, 1st pct of Tmin, 99th pct of Tmax, mean diurnal range |
| `era5_precip_mm_yr` | number | mm/yr | modeled | ERA5 precipitation / FAO-56 reference ET0 |
| `era5_et0_mm_yr` | number | mm/yr | modeled | ERA5 precipitation / FAO-56 reference ET0 |
| `era5_aridity_index` | number | dimensionless | modeled | P / ET0 (UNEP aridity index) |
| `era5_freeze_thaw_days_yr` | number | days/yr | modeled | Days with Tmax>0 °C and Tmin<0 °C |
| `era5_wind_max_mean_kmh` | number | km/h | modeled | Mean of daily max 10 m wind |
| `era5_sw_rad_mj_m2_day` | number | MJ m-2 day-1 | modeled | Mean daily shortwave radiation |
| `climate_workable_month_fraction` | number | fraction 0-1 | modeled | Months with ERA5 mean T in [-25, 35] °C |
| `maat_for_scoring_c` | number | °C | modeled | MAAT used for scoring (CHELSA, else ERA5) |
| `maat_source` | string | - | - | Which source supplied the value |
| `temperature_K` | number | K | modeled (Earth) / literature or modeled (refs) | Temperature used by the thermal similarity |
| `permafrost_prob` | number | probability 0-1 | modeled | Obu et al. 2019 permafrost probability, else MAAT-logistic model |
| `permafrost_source` | string | - | - | Which source supplied the value |
| `ice_indicator` | number | 0-1 | modeled/derived | max(permafrost_prob, WorldCover snow/ice fraction); references 1/0 from literature ice evidence |
| `soil_sand_pct` | number | % mass | modeled | SoilGrids 2.0 0-5 cm mean |
| `soil_silt_pct` | number | % mass | modeled | SoilGrids 2.0 0-5 cm mean |
| `soil_clay_pct` | number | % mass | modeled | SoilGrids 2.0 0-5 cm mean |
| `fine_fraction` | number | fraction 0-1 | modeled (Earth) / derived (Moon) | silt+clay (<50 µm) fraction |
| `road_distance_m` | number | m | derived | Distance to nearest mapped road (Natural Earth 1:10m; OSM if available); upper bound |
| `road_distance_censored_gt_m` | number | m | derived | If set, no road within this distance (right-censored) |
| `nearest_highway_class` | string | - | derived | Class of nearest road |
| `populated_place_distance_m` | number | m | derived | Distance to nearest Natural Earth populated place |
| `access_source` | string | - | - | Which source supplied the value |
| `macrostrat_lith` | string | - | literature | Macrostrat map-unit lithology at point (map scale) |
| `macrostrat_unit` | string | - | literature | Macrostrat map-unit lithology at point (map scale) |
| `macrostrat_scale` | string | - | literature | Macrostrat map-unit lithology at point (map scale) |
| `lithology_tags` | string | ; separated | literature/hypothesized | Controlled-vocabulary tags (vocabulary in scoring_config.json); per-tag evidence in site_evidence.json |
| `process_tags` | string | ; separated | literature/hypothesized | Controlled-vocabulary tags (vocabulary in scoring_config.json); per-tag evidence in site_evidence.json |
| `landform_tags` | string | ; separated | literature/hypothesized | Controlled-vocabulary tags (vocabulary in scoring_config.json); per-tag evidence in site_evidence.json |
| `resource_tags` | string | ; separated | literature/hypothesized | Controlled-vocabulary tags (vocabulary in scoring_config.json); per-tag evidence in site_evidence.json |
| `regulatory_class` | string | - | literature/hypothesized | Operational classes (scoring_config.operational) |
| `infrastructure_class` | string | - | literature/hypothesized | Operational classes (scoring_config.operational) |
| `evidence_tag_fraction_literature` | number | fraction 0-1 | derived | Share of categorical tags supported by fetched text |
| `data_confidence` | number | 0-1 | derived | Mean per-feature provenance confidence |
| `limitations` | string | ' | ' separated | - | Site-specific caveats |

## Column dictionary: `analog_rankings.csv`

| column | type | unit | provenance | description |
|---|---|---|---|---|
| `site_id` | string | - | - | Stable Earth site ID `EA-NNN` (primary key) |
| `name` | string | - | literature | Site name / country or territory |
| `group` | string | - | - | `baseline` (Atacama, Haughton, Death Valley) / `established` (documented analog use) / `candidate` |
| `body` | string | - | - | `Moon` or `Mars` |
| `mission_profile` | string | - | - | Profile key in scoring_config.mission_profiles |
| `matched_reference_id` | string | - | - | Planetary reference ID (`MOON-REF-NN` / `MARS-REF-NN`) |
| `fidelity_score` | number | 0-100 | derived | Surface/process analog fidelity for this profile (best-matching reference). NOT planetary equivalence |
| `fidelity_rank` | integer | 1 = best | derived | Rank within the profile (n=28) |
| `evidence_completeness` | number | 0-1 | derived | Share of profile weight with available data |
| `confidence` | number | 0-1 | derived | Weight-averaged provenance confidence of used features |
| `operational_score` | number | 0-100 | derived | Operational test suitability (separate from fidelity) |
| `operational_completeness` | number | 0-1 | derived | Share of operational weight with data |
| `mc_score_p05` | number | 0-100 | derived | 5th/95th percentile of score over 2000 Dirichlet weight draws |
| `mc_score_p95` | number | 0-100 | derived | 5th/95th percentile of score over 2000 Dirichlet weight draws |
| `mc_rank_p05` | integer | rank | derived | 5th/95th percentile rank over weight draws |
| `mc_rank_p95` | integer | rank | derived | 5th/95th percentile rank over weight draws |
| `mc_top5_probability` | number | 0-1 | derived | Probability of being in the top 5 over weight draws |
| `sim_lithology` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |
| `sim_process` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |
| `sim_landform` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |
| `sim_resource` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |
| `sim_slope` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |
| `sim_ruggedness` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |
| `sim_thermal` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |
| `sim_aridity` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |
| `sim_ice` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |
| `sim_abiotic_surface` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |
| `sim_dust_sediment` | number | 0-1 | derived | Per-feature similarity to the matched reference (empty = unavailable) |

## Column dictionary: `planetary_features.csv`

| column | type | unit | provenance | description |
|---|---|---|---|---|
| `ref_id` | string | - | - | Planetary reference ID (`MOON-REF-NN` / `MARS-REF-NN`) |
| `body` | string | - | - | `Moon` or `Mars` |
| `name` | string | - | literature | Site name / country or territory |
| `lat` | number | deg (WGS84) | literature | Sampling-point latitude / longitude, EPSG:4326 |
| `lon` | number | deg (WGS84) | literature | Sampling-point latitude / longitude, EPSG:4326 |
| `crs` | string | - | - | Body CRS: IAU_2015:30100 (Moon) or IAU_2015:49900 (Mars) |
| `status_class` | string | - | literature | verified_mission_site | candidate_region | representative_region |
| `dem_product` | string | - | - | DEM used for terrain metrics |
| `dem_grid_res_m` | number | m | - | Analysis grid resolution / window radius |
| `sample_radius_m` | number | m | - | Analysis grid resolution / window radius |
| `ref_elev_point_m` | number | m | derived | Reference elevation (Moon: above 1737.4 km sphere; Mars: MOLA areoid) |
| `ref_elev_mean_m` | number | m | derived | Reference elevation (Moon: above 1737.4 km sphere; Mars: MOLA areoid) |
| `ref_relief_m` | number | m | derived | Reference elevation (Moon: above 1737.4 km sphere; Mars: MOLA areoid) |
| `ref_slope_median_deg` | number | deg | derived | Reference slope statistics |
| `ref_slope_p90_deg` | number | deg | derived | Reference slope statistics |
| `ref_slope_frac_lt15` | number | fraction 0-1 | derived | Fraction of slopes <15° |
| `ref_tri_median_m` | number | m | derived | Reference TRI |
| `temperature_K` | number | K | modeled (Earth) / literature or modeled (refs) | Temperature used by the thermal similarity |
| `temperature_provenance` | string | - | - | Provenance of temperature_K |
| `aridity_index` | number | - | derived | Defined as 0 (no liquid precipitation) / 1 (no vegetation) for references |
| `abiotic_fraction` | number | - | derived | Defined as 0 (no liquid precipitation) / 1 (no vegetation) for references |
| `lithology_tags` | string | ; separated | literature/hypothesized | Controlled-vocabulary tags (vocabulary in scoring_config.json); per-tag evidence in site_evidence.json |
| `process_tags` | string | ; separated | literature/hypothesized | Controlled-vocabulary tags (vocabulary in scoring_config.json); per-tag evidence in site_evidence.json |
| `landform_tags` | string | ; separated | literature/hypothesized | Controlled-vocabulary tags (vocabulary in scoring_config.json); per-tag evidence in site_evidence.json |
| `resource_tags` | string | ; separated | literature/hypothesized | Controlled-vocabulary tags (vocabulary in scoring_config.json); per-tag evidence in site_evidence.json |
| `ice_indicator` | number | 0-1 | modeled/derived | max(permafrost_prob, WorldCover snow/ice fraction); references 1/0 from literature ice evidence |
| `fine_fraction` | number | fraction 0-1 | modeled (Earth) / derived (Moon) | silt+clay (<50 µm) fraction |
| `illumination_summary` | string | - | literature | Narrative fields with sources in site_evidence.json |
| `ice_evidence` | string | - | literature | Narrative fields with sources in site_evidence.json |
| `hazards` | string | - | literature | Narrative fields with sources in site_evidence.json |
| `mission_objectives` | string | - | literature | Narrative fields with sources in site_evidence.json |

## site_evidence.json structure

```json
{"schema_version":"1.0.0","earth_sites":{"EA-001":{"site_id":"EA-001","coordinates":{"lat":..,"lon":..,"source":"wiki:..","kind":"..","provenance":"literature"},
 "lithology":[{"tag":"evaporite_salts","keyword":"salt","provenance":"literature","quote":"<verbatim sentence>","source":"https://en.wikipedia.org/wiki/...","source_revision":123,"retrieved":"2026-11-15"}],
 "process":[...],"landform":[...],"resource":[...],"regulatory":{...},"infrastructure":{...},
 "numeric_sources":{"terrain":{"dataset_id":"DS-COP-DEM30","tiles":[...]},"climate_normals":{...},"era5":{"request":"<API URL>"},...},
 "limitations":["..."],"confidence":{"score":0.71,"method":"..."}}},
 "planetary_references":{"MOON-REF-01":{"status_note":"..","temperature":{"value":223,"provenance":"literature","quote":"..","source":".."},"terrain":{...},...}}}
```

## Recommended UI bindings

* Map: colour points by `group`, size them by the selected profile's `fidelity_score`, and render opacity from `evidence_completeness`.
* Profile selector: the 10 keys of `scoring_config.mission_profiles` (5 Moon, 5 Mars).
* Site panel: show the radar chart from `radar_chart_data.json` (or recompute from `sim_*`), list quotes from `site_evidence.json` and show limitations.
* Always show the disclaimer string from the GeoJSON `properties.disclaimer`.
