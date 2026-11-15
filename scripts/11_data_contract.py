"""Step 11 - write data_contract.md (CSV column dictionary + JSON/GeoJSON contract) and JSON Schemas in schemas/.
Also verifies that every CSV column is documented (raises if not)."""
import csv, re
from common import *

T = {"str": "string", "num": "number", "int": "integer"}
# (pattern, type, unit, provenance, description)
FEAT = [
 (r"site_id", "str", "-", "-", "Stable Earth site ID `EA-NNN` (primary key)"),
 (r"name|country", "str", "-", "literature", "Site name / country or territory"),
 (r"lat|lon", "num", "deg (WGS84)", "literature", "Sampling-point latitude / longitude, EPSG:4326"),
 (r"group", "str", "-", "-", "`baseline` (Atacama, Haughton, Death Valley) / `established` (documented analog use) / `candidate`"),
 (r"coord_kind|coord_source", "str", "-", "literature", "What the point represents and where it came from"),
 (r"elev_point_m", "num", "m (EGM2008)", "measured", "Copernicus DEM elevation at the sampling point"),
 (r"t30m_r2km_.*", "num", "see suffix", "derived", "Terrain on 30 m local AEQD grid within 2 km: elev_mean_m, relief_m (p99-p1), slope_median_deg, slope_p90_deg, slope_frac_lt15 (0-1), tri_median_m (Riley TRI), valid_fraction"),
 (r"t90m_r5km_.*", "num", "see suffix", "derived", "Same metrics on 90 m grid within 5 km (matched baseline for Moon references)"),
 (r"t450m_r15km_.*", "num", "see suffix", "derived", "Same metrics on 450 m grid within 15 km (matched baseline for Mars references)"),
 (r"wc_frac_.*_r5km", "num", "fraction 0-1", "derived", "ESA WorldCover 2021 class fraction within 5 km"),
 (r"abiotic_fraction_r5km", "num", "fraction 0-1", "derived", "(bare/sparse + snow/ice) / land fraction within 5 km"),
 (r"chelsa_maat_c|chelsa_tmax_warmest_c|chelsa_tmin_coldest_c|chelsa_t_annual_range_c", "num", "°C", "modeled", "CHELSA V2.1 1981-2010 bio1 / bio5 / bio6 / bio7"),
 (r"chelsa_precip_mm_yr", "num", "mm/yr", "modeled", "CHELSA bio12 annual precipitation"),
 (r"era5_t_mean_c|era5_t_min_p01_c|era5_t_max_p99_c|era5_diurnal_range_c", "num", "°C", "modeled", "ERA5 1991-2020 daily (Open-Meteo): mean, 1st pct of Tmin, 99th pct of Tmax, mean diurnal range"),
 (r"era5_precip_mm_yr|era5_et0_mm_yr", "num", "mm/yr", "modeled", "ERA5 precipitation / FAO-56 reference ET0"),
 (r"era5_aridity_index", "num", "dimensionless", "modeled", "P / ET0 (UNEP aridity index)"),
 (r"era5_freeze_thaw_days_yr", "num", "days/yr", "modeled", "Days with Tmax>0 °C and Tmin<0 °C"),
 (r"era5_wind_max_mean_kmh", "num", "km/h", "modeled", "Mean of daily max 10 m wind"),
 (r"era5_sw_rad_mj_m2_day", "num", "MJ m-2 day-1", "modeled", "Mean daily shortwave radiation"),
 (r"climate_workable_month_fraction", "num", "fraction 0-1", "modeled", "Months with ERA5 mean T in [-25, 35] °C"),
 (r"maat_for_scoring_c", "num", "°C", "modeled", "MAAT used for scoring (CHELSA, else ERA5)"),
 (r"maat_source|permafrost_source|access_source", "str", "-", "-", "Which source supplied the value"),
 (r"temperature_K", "num", "K", "modeled (Earth) / literature or modeled (refs)", "Temperature used by the thermal similarity"),
 (r"permafrost_prob", "num", "probability 0-1", "modeled", "Obu et al. 2019 permafrost probability, else MAAT-logistic model"),
 (r"ice_indicator", "num", "0-1", "modeled/derived", "max(permafrost_prob, WorldCover snow/ice fraction); references 1/0 from literature ice evidence"),
 (r"soil_(sand|silt|clay)_pct", "num", "% mass", "modeled", "SoilGrids 2.0 0-5 cm mean"),
 (r"fine_fraction", "num", "fraction 0-1", "modeled (Earth) / derived (Moon)", "silt+clay (<50 µm) fraction"),
 (r"soil_texture_source", "str", "", "derived", "SoilGrids2_point, or SoilGrids2_nearest_valid_pixel where the point pixel is masked (scripts/02b_soilgrids_nearby.py)"),
 (r"soil_nearby_distance_km", "num", "km", "derived", "Distance from the sampling point to the nearest valid SoilGrids pixel (only for the fallback)"),
 (r"road_distance_m", "num", "m", "derived", "Distance to nearest mapped road (Natural Earth 1:10m; OSM if available); upper bound"),
 (r"road_distance_censored_gt_m", "num", "m", "derived", "If set, no road within this distance (right-censored)"),
 (r"populated_place_distance_m", "num", "m", "derived", "Distance to nearest Natural Earth populated place"),
 (r"nearest_highway_class", "str", "-", "derived", "Class of nearest road"),
 (r"macrostrat_lith|macrostrat_unit|macrostrat_scale", "str", "-", "literature", "Macrostrat map-unit lithology at point (map scale)"),
 (r"(lithology|process|landform|resource)_tags", "str", "; separated", "literature/hypothesized", "Controlled-vocabulary tags (vocabulary in scoring_config.json); per-tag evidence in site_evidence.json"),
 (r"regulatory_class|infrastructure_class", "str", "-", "literature/hypothesized", "Operational classes (scoring_config.operational)"),
 (r"evidence_tag_fraction_literature", "num", "fraction 0-1", "derived", "Share of categorical tags supported by fetched text"),
 (r"data_confidence", "num", "0-1", "derived", "Mean per-feature provenance confidence"),
 (r"limitations", "str", "' | ' separated", "-", "Site-specific caveats"),
 # rankings
 (r"body", "str", "-", "-", "`Moon` or `Mars`"),
 (r"mission_profile", "str", "-", "-", "Profile key in scoring_config.mission_profiles"),
 (r"matched_reference_id|ref_id", "str", "-", "-", "Planetary reference ID (`MOON-REF-NN` / `MARS-REF-NN`)"),
 (r"fidelity_score", "num", "0-100", "derived", "Surface/process analog fidelity for this profile (best-matching reference). NOT planetary equivalence"),
 (r"fidelity_rank", "int", "1 = best", "derived", "Rank within the profile (n=28)"),
 (r"evidence_completeness", "num", "0-1", "derived", "Share of profile weight with available data"),
 (r"confidence", "num", "0-1", "derived", "Weight-averaged provenance confidence of used features"),
 (r"operational_score", "num", "0-100", "derived", "Operational test suitability (separate from fidelity)"),
 (r"operational_completeness", "num", "0-1", "derived", "Share of operational weight with data"),
 (r"mc_score_p05|mc_score_p95", "num", "0-100", "derived", "5th/95th percentile of score over 2000 Dirichlet weight draws"),
 (r"mc_rank_p05|mc_rank_p95", "int", "rank", "derived", "5th/95th percentile rank over weight draws"),
 (r"mc_top5_probability", "num", "0-1", "derived", "Probability of being in the top 5 over weight draws"),
 (r"sim_.*", "num", "0-1", "derived", "Per-feature similarity to the matched reference (empty = unavailable)"),
 # planetary
 (r"crs", "str", "-", "-", "Body CRS: IAU_2015:30100 (Moon) or IAU_2015:49900 (Mars)"),
 (r"status_class", "str", "-", "literature", "verified_mission_site | candidate_region | representative_region"),
 (r"dem_product", "str", "-", "-", "DEM used for terrain metrics"),
 (r"dem_grid_res_m|sample_radius_m", "num", "m", "-", "Analysis grid resolution / window radius"),
 (r"ref_elev_point_m|ref_elev_mean_m|ref_relief_m", "num", "m", "derived", "Reference elevation (Moon: above 1737.4 km sphere; Mars: MOLA areoid)"),
 (r"ref_slope_median_deg|ref_slope_p90_deg", "num", "deg", "derived", "Reference slope statistics"),
 (r"ref_slope_frac_lt15", "num", "fraction 0-1", "derived", "Fraction of slopes <15°"),
 (r"ref_tri_median_m", "num", "m", "derived", "Reference TRI"),
 (r"temperature_provenance", "str", "-", "-", "Provenance of temperature_K"),
 (r"aridity_index|abiotic_fraction", "num", "-", "derived", "Defined as 0 (no liquid precipitation) / 1 (no vegetation) for references"),
 (r"illumination_summary|ice_evidence|hazards|mission_objectives", "str", "-", "literature", "Narrative fields with sources in site_evidence.json"),
]


def lookup(col):
    for pat, t, u, prov, d in FEAT:
        if re.fullmatch(pat, col):
            return T[t], u, prov, d
    raise KeyError(col)


def table(path):
    cols = next(csv.reader(open(path, encoding="utf-8")))
    rows = ["| column | type | unit | provenance | description |", "|---|---|---|---|---|"]
    for c in cols:
        t, u, p, d = lookup(c)
        rows.append(f"| `{c}` | {t} | {u} | {p} | {d} |")
    return cols, rows


def schema_for_csv(cols, title):
    props = {}
    for c in cols:
        t, u, p, d = lookup(c)
        props[c] = {"type": [t, "null"] if c not in ("site_id", "ref_id", "mission_profile") else t, "description": f"{d} [{u}; {p}]"}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": title, "type": "object",
            "properties": props, "required": [c for c in cols if c in ("site_id", "ref_id", "mission_profile", "fidelity_score", "lat", "lon")]}


GEO_SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "earth_analog_sites.geojson feature",
              "type": "object", "required": ["type", "id", "geometry", "properties"],
              "properties": {"type": {"const": "Feature"}, "id": {"type": "string", "pattern": "^EA-[0-9]{3}$"},
                             "bbox": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
                             "geometry": {"type": "object", "required": ["type", "coordinates"], "properties": {"type": {"const": "Point"},
                                          "coordinates": {"type": "array", "prefixItems": [{"type": "number", "minimum": -180, "maximum": 180}, {"type": "number", "minimum": -90, "maximum": 90}]}}},
                             "properties": {"type": "object", "required": ["site_id", "name", "country", "group", "best_moon_profile", "best_moon_score", "best_mars_profile", "best_mars_score", "scores", "operational_score", "limitations", "disclaimer"],
                                            "properties": {"scores": {"type": "object", "additionalProperties": {"type": "object", "required": ["fidelity_score", "fidelity_rank", "evidence_completeness", "confidence", "matched_reference_id"]}}}}}}
REF_SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "planetary_reference_sites.geojson feature", "type": "object",
              "required": ["type", "id", "geometry", "properties"],
              "properties": {"id": {"type": "string", "pattern": "^(MOON|MARS)-REF-[0-9]{2}$"},
                             "properties": {"type": "object", "required": ["ref_id", "body", "crs", "status_class", "not_an_approved_base_site"],
                                            "properties": {"body": {"enum": ["Moon", "Mars"]}, "crs": {"enum": ["IAU_2015:30100", "IAU_2015:49900"]},
                                                           "status_class": {"enum": ["verified_mission_site", "candidate_region", "representative_region"]},
                                                           "not_an_approved_base_site": {"const": True}}}}}
EVID_SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "site_evidence.json", "type": "object",
               "required": ["schema_version", "earth_sites", "planetary_references"],
               "$defs": {"tag": {"type": "object", "required": ["tag", "provenance"], "properties": {"tag": {"type": "string"}, "keyword": {"type": ["string", "null"]},
                         "provenance": {"enum": ["literature", "hypothesized"]}, "quote": {"type": ["string", "null"]}, "source": {"type": ["string", "null"]}}}},
               "properties": {"earth_sites": {"type": "object", "additionalProperties": {"type": "object", "required": ["site_id", "coordinates", "lithology", "process", "landform", "resource", "numeric_sources", "limitations", "confidence"],
                              "properties": {k: {"type": "array", "items": {"$ref": "#/$defs/tag"}} for k in ("lithology", "process", "landform", "resource")}}}}}


def main():
    sch = ROOT / "schemas"; sch.mkdir(exist_ok=True)
    parts = []
    for fn, title in (("analog_features.csv", "analog_features row"), ("analog_rankings.csv", "analog_rankings row"), ("planetary_features.csv", "planetary_features row")):
        cols, rows = table(OUTPUTS / fn)
        save_json(schema_for_csv(cols, title), sch / fn.replace(".csv", ".schema.json"))
        parts.append((fn, rows))
    save_json(GEO_SCHEMA, sch / "earth_analog_sites.feature.schema.json")
    save_json(REF_SCHEMA, sch / "planetary_reference_sites.feature.schema.json")
    save_json(EVID_SCHEMA, sch / "site_evidence.schema.json")
    L = ["# TerraAnalog AI data contract (v1.0.0)", "",
         "This contract is for **Grok Bot 2** (web-app developer). Files live in `outputs/` and JSON Schemas (draft 2020-12) in `schemas/`.", "",
         "## Conventions", "",
         "* **IDs are stable:** `EA-001`…`EA-028` (Earth), `MOON-REF-01`…`07`, `MARS-REF-01`…`07`. They will never be reused for a different place.",
         "* **Nulls:** an empty CSV cell and JSON `null` both mean *unavailable*. Never coerce them to 0.",
         "* **Units:** SI throughout (m, K, fractions 0–1, mm/yr for precipitation as is standard for climate data). Celsius columns are suffixed `_c`, and Kelvin is `temperature_K`.",
         "* **CRS:** Earth files use WGS84 lon/lat (EPSG:4326, RFC 7946). `planetary_reference_sites.geojson` uses **body-fixed planetocentric lon/lat** (IAU_2015:30100 Moon, IAU_2015:49900 Mars). Never place these on an Earth basemap.",
         "* **Provenance classes:** measured | derived | modeled | literature | hypothesized | unavailable (see `scientific_methodology.md`).",
         "* **Score semantics:** `fidelity_score` (0–100) is a per-mission-profile relative ranking aid, **not** a measure of planetary equivalence. Always display it together with `evidence_completeness` and `confidence`. Keep `operational_score` visually separate.", "",
         "## File inventory", "",
         "| File | Format | Key | Description |", "|---|---|---|---|",
         "| outputs/earth_analog_sites.geojson | GeoJSON FeatureCollection (Point) | `id` = site_id | Map layer with summary properties and per-profile `scores` object |",
         "| outputs/earth_analog_site_bounds.geojson | GeoJSON (Polygon) | `id` | Approximate bounding boxes (boundary_status = approximate_bbox) |",
         "| outputs/planetary_reference_sites.geojson | GeoJSON (Point, body CRS) | `id` = ref_id | Moon/Mars reference layer |",
         "| outputs/analog_features.csv | CSV | site_id | All Earth features (dictionary below) |",
         "| outputs/planetary_features.csv | CSV | ref_id | Reference features |",
         "| outputs/analog_rankings.csv | CSV | (site_id, mission_profile) | Scores, ranks, uncertainty, per-feature similarities |",
         "| data/processed/pair_scores.csv | CSV | (site_id, ref_id, mission_profile) | Score against every reference in each profile |",
         "| outputs/site_evidence.json | JSON | earth_sites[site_id], planetary_references[ref_id] | Per-tag quotes and URLs, numeric sources, limitations, confidence |",
         "| outputs/scoring_config.json | JSON | - | Copy of config/scoring_config.json used for this run |",
         "| outputs/radar_chart_data.json | JSON | profiles[profile] → top 5 | Radar-chart series (feature → similarity) |",
         "| outputs/similarity_matrix_site_x_reference.csv | CSV matrix | site_id × ref_id | Equal-weight mean similarity (0–100) |",
         "| outputs/similarity_matrix_site_x_site.csv | CSV matrix | site_id × site_id | Cosine similarity of standardised features |",
         "| outputs/analytics_summary.json | JSON | - | PCA, clusters, baseline comparison |",
         "| outputs/sensitivity_summary.json | JSON | profiles[profile] | Monte Carlo, OAT, LOFO, strict-evidence results |",
         "| outputs/data_gaps.csv | CSV | site_id | Missing values, hypothesized tags, recommended field measurements |",
         "| outputs/dataset_catalog.csv | CSV | dataset_id | Dataset catalog |",
         "| outputs/validation_report.md / validation_results.json | MD / JSON | - | Validation outcome |", ""]
    for fn, rows in parts:
        L += [f"## Column dictionary: `{fn}`", ""] + rows + [""]
    L += ["## site_evidence.json structure", "", "```json",
          '{"schema_version":"1.0.0","earth_sites":{"EA-001":{"site_id":"EA-001","coordinates":{"lat":..,"lon":..,"source":"wiki:..","kind":"..","provenance":"literature"},',
          ' "lithology":[{"tag":"evaporite_salts","keyword":"salt","provenance":"literature","quote":"<verbatim sentence>","source":"https://en.wikipedia.org/wiki/...","source_revision":123,"retrieved":"2026-11-15"}],',
          ' "process":[...],"landform":[...],"resource":[...],"regulatory":{...},"infrastructure":{...},',
          ' "numeric_sources":{"terrain":{"dataset_id":"DS-COP-DEM30","tiles":[...]},"climate_normals":{...},"era5":{"request":"<API URL>"},...},',
          ' "limitations":["..."],"confidence":{"score":0.71,"method":"..."}}},',
          ' "planetary_references":{"MOON-REF-01":{"status_note":"..","temperature":{"value":223,"provenance":"literature","quote":"..","source":".."},"terrain":{...},...}}}', "```", "",
          "## Recommended UI bindings", "",
          "* Map: colour points by `group`, size them by the selected profile's `fidelity_score`, and render opacity from `evidence_completeness`.",
          "* Profile selector: the 10 keys of `scoring_config.mission_profiles` (5 Moon, 5 Mars).",
          "* Site panel: show the radar chart from `radar_chart_data.json` (or recompute from `sim_*`), list quotes from `site_evidence.json` and show limitations.",
          "* Always show the disclaimer string from the GeoJSON `properties.disclaimer`."]
    (ROOT / "data_contract.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("data_contract.md + schemas written")


if __name__ == "__main__":
    main()
