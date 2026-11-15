"""Step 8 - GIS outputs.
  outputs/earth_analog_sites.geojson           RFC 7946 FeatureCollection of Points (WGS84 lon/lat)
  outputs/earth_analog_site_bounds.geojson     approximate bounding-box Polygons (labelled approximate)
  outputs/planetary_reference_sites.geojson    body-fixed planetocentric lon/lat Points (NOT WGS84; see crs_note)
Run:  python scripts/08_build_geojson.py
"""
import csv
from common import *

CFG = scoring_config()


def main():
    feats = load_json(PROCESSED / "features.json")
    ev = load_json(OUTPUTS / "site_evidence.json")
    ranks = list(csv.DictReader(open(OUTPUTS / "analog_rankings.csv", encoding="utf-8")))
    master = {s["site_id"]: s for s in earth_sites()}
    by_site = {}
    for r in ranks:
        by_site.setdefault(r["site_id"], {})[r["mission_profile"]] = {
            "fidelity_score": float(r["fidelity_score"]), "fidelity_rank": int(r["fidelity_rank"]),
            "evidence_completeness": float(r["evidence_completeness"]), "confidence": float(r["confidence"]),
            "matched_reference_id": r["matched_reference_id"], "mc_top5_probability": float(r["mc_top5_probability"])}
    pts, polys = [], []
    for e in feats["earth"]:
        sid = e["site_id"]; s = master[sid]
        prof = by_site[sid]
        best_moon = max((k for k in prof if k.startswith("MOON")), key=lambda k: prof[k]["fidelity_score"])
        best_mars = max((k for k in prof if k.startswith("MARS")), key=lambda k: prof[k]["fidelity_score"])
        op = next(r for r in ranks if r["site_id"] == sid)["operational_score"]
        h = s["bbox_half_deg"]
        hl = h / max(math.cos(math.radians(e["lat"])), 0.2)
        bbox = [clean(max(-180, e["lon"] - hl), 5), clean(max(-90, e["lat"] - h), 5), clean(min(180, e["lon"] + hl), 5), clean(min(90, e["lat"] + h), 5)]
        props = {
            "site_id": sid, "name": e["name"], "country": e["country"], "group": e["group"],
            "coord_kind": e["coord_kind"], "coord_source": e["coord_source"],
            "elevation_m": e["elev_point_m"], "slope_median_30m_deg": e["t30m_r2km_slope_median_deg"],
            "slope_p90_30m_deg": e["t30m_r2km_slope_p90_deg"], "tri_30m_m": e["t30m_r2km_tri_median_m"],
            "maat_c": e["maat_for_scoring_c"], "maat_source": e["maat_source"], "precip_mm_yr": e["era5_precip_mm_yr"],
            "aridity_index": e["era5_aridity_index"], "permafrost_prob": e["permafrost_prob"], "permafrost_source": e["permafrost_source"],
            "abiotic_fraction": e["abiotic_fraction_r5km"], "fine_fraction": e["fine_fraction"], "road_distance_m": e["road_distance_m"],
            "lithology_tags": e["lithology_tags"].split(";") if e["lithology_tags"] else [],
            "process_tags": e["process_tags"].split(";") if e["process_tags"] else [],
            "landform_tags": e["landform_tags"].split(";") if e["landform_tags"] else [],
            "resource_tags": e["resource_tags"].split(";") if e["resource_tags"] else [],
            "best_moon_profile": best_moon, "best_moon_score": prof[best_moon]["fidelity_score"],
            "best_mars_profile": best_mars, "best_mars_score": prof[best_mars]["fidelity_score"],
            "operational_score": None if op == "" else float(op),
            "scores": prof, "data_confidence": e["data_confidence"],
            "limitations": ev["earth_sites"][sid]["limitations"],
            "bbox_status": "approximate (sampling point ± bbox_half_deg; not a mapped boundary)",
            "disclaimer": "Scores rank relative analog fidelity for one mission objective; not a measure of planetary equivalence."}
        pts.append({"type": "Feature", "id": sid, "bbox": bbox, "geometry": {"type": "Point", "coordinates": [e["lon"], e["lat"]]}, "properties": props})
        ring = [[bbox[0], bbox[1]], [bbox[2], bbox[1]], [bbox[2], bbox[3]], [bbox[0], bbox[3]], [bbox[0], bbox[1]]]
        polys.append({"type": "Feature", "id": sid, "geometry": {"type": "Polygon", "coordinates": [ring]},
                      "properties": {"site_id": sid, "name": e["name"], "boundary_status": "approximate_bbox", "half_width_deg_lat": h}})
    meta = {"schema_version": "1.0.0", "generated": RETRIEVAL_DATE, "crs": "WGS84 lon/lat (EPSG:4326, RFC 7946 default)"}
    save_json({"type": "FeatureCollection", "name": "earth_analog_sites", "metadata": meta, "features": pts}, OUTPUTS / "earth_analog_sites.geojson")
    save_json({"type": "FeatureCollection", "name": "earth_analog_site_bounds", "metadata": {**meta, "note": "Approximate bounding boxes only."}, "features": polys}, OUTPUTS / "earth_analog_site_bounds.geojson")
    rf = []
    for r in feats["references"]:
        rev = ev["planetary_references"][r["ref_id"]]
        rf.append({"type": "Feature", "id": r["ref_id"], "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                   "properties": {"ref_id": r["ref_id"], "body": r["body"], "name": r["name"], "crs": r["crs"],
                                  "coordinate_system": "planetocentric latitude, east-positive longitude in [-180,180]",
                                  "status_class": r["status_class"], "status_note": rev["status_note"],
                                  "elevation_m": r["ref_elev_point_m"], "elevation_datum": "Moon: height above 1737.4 km sphere; Mars: MOLA areoid",
                                  "slope_median_deg": r["ref_slope_median_deg"], "slope_p90_deg": r["ref_slope_p90_deg"],
                                  "slope_baseline_m": r["dem_grid_res_m"], "relief_m": r["ref_relief_m"], "dem_product": r["dem_product"],
                                  "temperature_K": r["temperature_K"], "temperature_provenance": r["temperature_provenance"],
                                  "illumination": r["illumination_summary"], "ice_evidence": r["ice_evidence"], "hazards": r["hazards"],
                                  "mission_objectives": r["mission_objectives"],
                                  "lithology_tags": r["lithology_tags"].split(";"), "process_tags": r["process_tags"].split(";"),
                                  "landform_tags": r["landform_tags"].split(";"), "resource_tags": [t for t in r["resource_tags"].split(";") if t],
                                  "not_an_approved_base_site": True}})
    save_json({"type": "FeatureCollection", "name": "planetary_reference_sites",
               "crs_note": "NOT WGS84. Coordinates are planetocentric body-fixed lon/lat: Moon features use IAU_2015:30100 (Moon 2015 sphere), Mars features use IAU_2015:49900 (Mars 2015 planetocentric). Do not overlay on Earth basemaps; render on separate Moon/Mars basemaps (e.g., NASA Trek WMTS).",
               "metadata": {"schema_version": "1.0.0", "generated": RETRIEVAL_DATE}, "features": rf}, OUTPUTS / "planetary_reference_sites.geojson")
    print(f"geojson: {len(pts)} Earth points, {len(rf)} references")


if __name__ == "__main__":
    main()
