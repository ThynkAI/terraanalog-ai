"""Step 4 - preprocessing & feature extraction.

Merges the cached raw retrievals into:
  outputs/analog_features.csv        one row per Earth site (SI units, explicit nulls)
  outputs/planetary_features.csv     one row per planetary reference
  outputs/site_evidence.json         per-site / per-reference provenance, quotes and source URLs
  data/processed/features.json       machine-readable merge used by scoring
Run:  python scripts/04_build_features.py
"""
import csv, math
from common import *

CFG = scoring_config()
EQUIV = CFG["tag_equivalences"]


def tags_with_evidence(entity, field):
    """Return (tags, evidence list). Keyword found in a cited source -> 'literature'; else 'hypothesized'."""
    texts = []
    for t in entity.get("wiki", []):
        p, meta = wiki_file(t)
        if p and p.exists():
            texts.append((t, meta, p.read_text(encoding="utf-8")))
    tags, ev = [], []
    for raw in entity.get(field, []):
        tag, kw, hyp = parse_tag(raw)
        rec = {"tag": tag, "keyword": kw or None, "provenance": "hypothesized", "quote": None, "source": None}
        if not hyp:
            for title, meta, txt in texts:
                q = find_sentence(txt, kw)
                if q:
                    rec.update({"provenance": "literature", "quote": q, "source": meta["url"],
                                "source_revision": meta.get("lastrevid"), "retrieved": meta.get("retrieved")})
                    break
        if rec["provenance"] == "hypothesized":
            rec["note"] = "expert assignment; keyword not found in fetched source text" if not hyp else "expert assignment (marked '?')"
        if tag not in tags:
            tags.append(tag)
        ev.append(rec)
    return tags, ev


def g(d, k):
    return None if d is None else clean(d.get(k))


def logistic_pf(maat):
    pm = CFG["permafrost_model"]
    return 1.0 / (1.0 + math.exp((maat + 2.0) / 1.0))


def build_earth():
    chelsa = load_json(RAW / "chelsa" / "chelsa_points.json")
    pf = load_json(RAW / "permafrost" / "obu_points.json")
    rows, evidence = [], {}
    for s in earth_sites():
        sid = s["site_id"]
        dem = _load(RAW / "dem" / f"{sid}.json")
        era = _load(RAW / "era5" / f"{sid}.json")
        mac = _load(RAW / "macrostrat" / f"{sid}.json")
        soil = _load(RAW / "soilgrids" / f"{sid}.json")
        osm = _load(RAW / "osm" / f"{sid}.json")
        ch = chelsa.get(sid, {})
        r = {"site_id": sid, "name": s["name"], "country": s["country"], "lat": s["lat"], "lon": s["lon"],
             "group": s["group"], "coord_kind": s["coord_kind"], "coord_source": s["coord_source"]}
        # --- terrain (Copernicus DEM GLO-30, derived) ---
        r["elev_point_m"] = g(dem, "elev_point_m")
        for pre in ("t30m_r2km", "t90m_r5km", "t450m_r15km"):
            for k in ("elev_mean_m", "relief_m", "slope_median_deg", "slope_p90_deg", "slope_frac_lt15", "tri_median_m", "valid_fraction"):
                r[f"{pre}_{k}"] = g(dem, f"{pre}_{k}")
        # --- land cover (ESA WorldCover 2021) ---
        for k in ("bare_sparse", "snow_ice", "water", "tree", "shrub", "grass", "crop", "built", "wetland", "moss_lichen"):
            r[f"wc_frac_{k}_r5km"] = g(dem, f"wc_frac_{k}_r5km")
        bs, si = r["wc_frac_bare_sparse_r5km"], r["wc_frac_snow_ice_r5km"]
        land = None if r["wc_frac_water_r5km"] is None else 1 - r["wc_frac_water_r5km"]
        r["abiotic_fraction_r5km"] = None if bs is None else clean(min(1.0, (bs + (si or 0)) / land) if land and land > 0 else None)
        # --- climate ---
        r["chelsa_maat_c"] = clean(ch.get("chelsa_bio1"), 2)
        r["chelsa_tmax_warmest_c"] = clean(ch.get("chelsa_bio5"), 2)
        r["chelsa_tmin_coldest_c"] = clean(ch.get("chelsa_bio6"), 2)
        r["chelsa_t_annual_range_c"] = clean(ch.get("chelsa_bio7"), 2)
        r["chelsa_precip_mm_yr"] = clean(ch.get("chelsa_bio12"), 1)
        for k in ("era5_t_mean_c", "era5_t_min_p01_c", "era5_t_max_p99_c", "era5_diurnal_range_c", "era5_precip_mm_yr",
                  "era5_et0_mm_yr", "era5_aridity_index", "era5_freeze_thaw_days_yr", "era5_wind_max_mean_kmh", "era5_sw_rad_mj_m2_day"):
            r[k] = g(era, k)
        if era and era.get("era5_monthly_t_mean_c"):
            mm = era["era5_monthly_t_mean_c"]
            r["climate_workable_month_fraction"] = clean(sum(1 for t in mm if -25 <= t <= 35) / 12.0)
        else:
            r["climate_workable_month_fraction"] = None
        maat = r["chelsa_maat_c"] if r["chelsa_maat_c"] is not None else r["era5_t_mean_c"]
        r["maat_for_scoring_c"] = maat
        r["maat_source"] = "CHELSA_V2.1_bio1" if r["chelsa_maat_c"] is not None else ("ERA5_OpenMeteo" if maat is not None else None)
        r["temperature_K"] = None if maat is None else clean(maat + 273.15, 2)
        # --- permafrost / ice ---
        pv = pf.get(sid, {}).get("obu_perprob")
        if pv is not None:
            r["permafrost_prob"], r["permafrost_source"] = clean(pv), "Obu2019_PERPROB"
        elif maat is not None:
            r["permafrost_prob"], r["permafrost_source"] = clean(logistic_pf(maat)), "MAAT_logistic_model"
        else:
            r["permafrost_prob"], r["permafrost_source"] = None, None
        ice_parts = [v for v in (r["permafrost_prob"], si) if v is not None]
        r["ice_indicator"] = clean(max(ice_parts)) if ice_parts else None
        # --- soil texture (SoilGrids, modeled) ---
        for k in ("sand", "silt", "clay"):
            r[f"soil_{k}_pct"] = g(soil, f"soil_{k}_mean_pct")
        if r["soil_silt_pct"] is not None and r["soil_clay_pct"] is not None:
            r["fine_fraction"] = clean((r["soil_silt_pct"] + r["soil_clay_pct"]) / 100.0)
        else:
            r["fine_fraction"] = None
        # --- access (OSM) ---
        r["road_distance_m"] = g(osm, "road_distance_m")
        r["road_distance_censored_gt_m"] = g(osm, "road_distance_censored_gt_m")
        r["nearest_highway_class"] = osm.get("nearest_highway_class") if osm else None
        # --- geology text from Macrostrat ---
        units = (mac or {}).get("units", [])
        best = next((u for sc in ("large", "medium", "small", "tiny") for u in units if u["scale"] == sc and u.get("lith")), None)
        r["macrostrat_lith"] = best.get("lith") if best else None
        r["macrostrat_unit"] = best.get("name") if best else None
        r["macrostrat_scale"] = best.get("scale") if best else None
        # --- categorical tags ---
        ev = {"site_id": sid, "coordinates": {"lat": s["lat"], "lon": s["lon"], "source": s["coord_source"],
                                               "kind": s["coord_kind"], "provenance": "literature"}}
        for f in ("lithology", "process", "landform", "resource"):
            tags, tev = tags_with_evidence(s, f)
            r[f"{f}_tags"] = ";".join(tags)
            ev[f] = tev
        r["regulatory_class"], _, reg_kw = s["regulatory"].partition(":")
        r["infrastructure_class"], _, inf_kw = s["infrastructure"].partition(":")
        for name, (cls, kw) in {"regulatory": (r["regulatory_class"], reg_kw), "infrastructure": (r["infrastructure_class"], inf_kw)}.items():
            ent = {"tag": cls, "keyword": kw or None, "provenance": "hypothesized", "quote": None}
            for t in s["wiki"]:
                p, meta = wiki_file(t)
                q = find_sentence(p.read_text(encoding="utf-8"), kw) if (p and kw) else None
                if q:
                    ent.update({"provenance": "literature", "quote": q, "source": meta["url"]}); break
            ev[name] = ent
        r["evidence_tag_fraction_literature"] = clean(
            sum(1 for f in ("lithology", "process", "landform", "resource") for e in ev[f] if e["provenance"] == "literature") /
            max(1, sum(len(ev[f]) for f in ("lithology", "process", "landform", "resource"))))
        ev["numeric_sources"] = {
            "terrain": {"dataset_id": "DS-COP-DEM30", "provenance": "derived", "tiles": (dem or {}).get("dem_tiles_used"),
                        "missing_tiles": (dem or {}).get("dem_tiles_missing"), "method": "bilinear reprojection to 30 m local AEQD grid; Horn slope; Riley TRI; water (WorldCover=80) masked; 90 m / 450 m by block mean"},
            "land_cover": {"dataset_id": "DS-ESA-WC2021", "provenance": "derived", "tiles": (dem or {}).get("worldcover_tiles_used")},
            "climate_normals": {"dataset_id": "DS-CHELSA21", "provenance": "modeled", "urls": sorted({v for k, v in ch.items() if k.endswith('_url')})},
            "era5": {"dataset_id": "DS-ERA5-OM", "provenance": "modeled", "request": (era or {}).get("request"),
                     "grid_point": [(era or {}).get("grid_lat"), (era or {}).get("grid_lon")], "grid_elevation_m": (era or {}).get("grid_elevation_m")},
            "permafrost": {"dataset_id": "DS-OBU-PF" if r["permafrost_source"] == "Obu2019_PERPROB" else "DS-CHELSA21",
                           "provenance": "modeled", "method": r["permafrost_source"], "note": pf.get(sid, {}).get("note")},
            "soil": {"dataset_id": "DS-SOILGRIDS", "provenance": "modeled", "request": (soil or {}).get("request"),
                     "error": (soil or {}).get("error") or (soil or {}).get("http_status")},
            "access": {"dataset_id": "DS-OSM", "provenance": "derived", "note": (osm or {}).get("note")},
            "geology_map": {"dataset_id": "DS-MACROSTRAT", "provenance": "literature", "units": units[:4]},
        }
        ev["limitations"] = site_limitations(s, r)
        ev["confidence"] = site_confidence(r, ev)
        r["data_confidence"] = ev["confidence"]["score"]
        r["limitations"] = " | ".join(ev["limitations"])
        rows.append(r)
        evidence[sid] = ev
    return rows, evidence


def site_limitations(s, r):
    L = []
    if "centroid" in s["coord_kind"] or "region" in s["coord_kind"]:
        L.append("Sampling point is a region centroid; local terrain may not represent the best analog outcrops.")
    if "water" in s["coord_kind"] or "lake" in s["coord_kind"]:
        L.append("Reference point lies on a water body; terrain metrics use water-masked DEM (WorldCover class 80).")
    if r["maat_source"] != "CHELSA_V2.1_bio1":
        L.append("CHELSA climate unavailable at point; ERA5 0.25° grid value used.")
    if r["permafrost_source"] == "MAAT_logistic_model":
        L.append("Permafrost probability is a coarse MAAT-based model (Obu 2019 covers only >=25°N).")
    if r["fine_fraction"] is None:
        L.append("SoilGrids texture unavailable (masked/no response).")
    if r["road_distance_m"] is None:
        L.append("No mapped road/track within search radius or Overpass unavailable.")
    L.append("ERA5 (0.25°) and CHELSA (30 arc-s) are modeled climate fields, not station measurements.")
    return L


def site_confidence(r, ev):
    pc = CFG["provenance_confidence"]
    vals = []
    vals += [pc["derived"] if r["t30m_r2km_slope_median_deg"] is not None else 0]
    vals += [pc["derived"] if r["abiotic_fraction_r5km"] is not None else 0]
    vals += [pc["modeled"] if r["temperature_K"] is not None else 0]
    vals += [pc["modeled"] if r["era5_aridity_index"] is not None else 0]
    vals += [pc["modeled"] * (1.0 if r["permafrost_source"] == "Obu2019_PERPROB" else 0.6) if r["permafrost_prob"] is not None else 0]
    vals += [pc["modeled"] if r["fine_fraction"] is not None else 0]
    for f in ("lithology", "process", "landform", "resource"):
        e = ev[f]
        vals += [sum(pc[x["provenance"]] for x in e) / len(e) if e else 0]
    return {"score": clean(sum(vals) / len(vals), 3), "method": "mean of per-feature provenance confidence (scoring_config.provenance_confidence); missing = 0"}


def build_refs():
    terr = load_json(RAW / "planetary" / "planetary_terrain.json")
    rows, evidence = [], {}
    for ref in planetary_refs():
        rid = ref["ref_id"]
        t = terr.get(rid, {})
        r = {"ref_id": rid, "body": ref["body"], "name": ref["name"], "lat": ref["lat"], "lon": ref["lon"],
             "crs": "IAU_2015:30100" if ref["body"] == "Moon" else "IAU_2015:49900", "status_class": ref["status_class"],
             "dem_product": t.get("product"), "dem_grid_res_m": t.get("grid_res_m"), "sample_radius_m": ref["sample_radius_m"]}
        for k in ("ref_elev_point_m", "ref_elev_mean_m", "ref_relief_m", "ref_slope_median_deg", "ref_slope_p90_deg", "ref_slope_frac_lt15", "ref_tri_median_m"):
            r[k] = clean(t.get(k))
        tk = ref.get("temperature_K") or {}
        r["temperature_K"] = tk.get("value")
        r["temperature_provenance"] = tk.get("provenance")
        r["aridity_index"] = 0.0
        r["abiotic_fraction"] = 1.0
        ice_tags = {"ground_ice", "water_ice_cold_traps"}
        ev = {"ref_id": rid, "status_note": ref["status_note"], "coord_source": ref["coord_source"]}
        for f in ("lithology", "process", "landform", "resource"):
            tags, tev = tags_with_evidence(ref, f)
            r[f"{f}_tags"] = ";".join(tags)
            ev[f] = tev
        all_tags = set(r["lithology_tags"].split(";")) | set(r["resource_tags"].split(";"))
        r["ice_indicator"] = 1.0 if all_tags & ice_tags else 0.0
        r["fine_fraction"] = CFG["lunar_regolith_fine_fraction"]["value"] if ref["body"] == "Moon" else None
        ev["temperature"] = tk
        ev["illumination"] = ref.get("illumination")
        ev["ice_evidence"] = ref.get("ice_evidence")
        ev["hazards"] = ref.get("hazards")
        ev["mission_objectives"] = ref.get("mission_objectives")
        ev["terrain"] = {"provenance": "derived", "dataset": t.get("product"), "url": t.get("url"),
                         "method": f"DEM reprojected to {t.get('grid_res_m')} m body-fixed AEQD grid, Horn slope, Riley TRI within {ref['sample_radius_m']} m"}
        ev["aridity"] = {"value": 0.0, "provenance": "derived", "note": "No liquid precipitation on present-day Moon/Mars surfaces; AI defined as 0."}
        ev["abiotic_fraction"] = {"value": 1.0, "provenance": "derived", "note": "No vegetation."}
        ev["fine_fraction"] = CFG["lunar_regolith_fine_fraction"] if ref["body"] == "Moon" else {"value": None, "provenance": "unavailable"}
        r["illumination_summary"] = (ref.get("illumination") or {}).get("value") if isinstance(ref.get("illumination"), dict) else None
        r["ice_evidence"] = ref.get("ice_evidence")
        r["hazards"] = "; ".join(ref.get("hazards") or [])
        r["mission_objectives"] = "; ".join(ref.get("mission_objectives") or [])
        rows.append(r)
        evidence[rid] = ev
    return rows, evidence


def _load(p):
    return load_json(p) if Path(p).exists() else None


def write_csv(rows, p):
    keys = list(rows[0].keys())
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in keys})


if __name__ == "__main__":
    erows, eev = build_earth()
    rrows, rev = build_refs()
    write_csv(erows, OUTPUTS / "analog_features.csv")
    write_csv(rrows, OUTPUTS / "planetary_features.csv")
    save_json({"schema_version": "1.0.0", "generated": RETRIEVAL_DATE,
               "note": "Empty CSV cells and JSON null both mean 'unavailable'. See data_contract.md.",
               "earth_sites": eev, "planetary_references": rev}, OUTPUTS / "site_evidence.json")
    save_json({"earth": erows, "references": rrows}, PROCESSED / "features.json")
    print(f"features: {len(erows)} Earth sites, {len(rrows)} references")
    lit = sum(1 for e in eev.values() for f in ("lithology", "process", "landform", "resource") for x in e[f] if x["provenance"] == "literature")
    tot = sum(len(e[f]) for e in eev.values() for f in ("lithology", "process", "landform", "resource"))
    print(f"Earth tag evidence: {lit}/{tot} literature-supported")
    for e in eev.values():
        miss = [x["tag"] + ":" + str(x["keyword"]) for f in ("lithology", "process", "landform", "resource") for x in e[f] if x["provenance"] != "literature"]
        if miss:
            print(" ", e["site_id"], "unsupported:", miss)
