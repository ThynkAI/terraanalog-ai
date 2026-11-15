"""Step 02c - administrative region (Natural Earth 1:10m admin-1 states/provinces, public domain) for each Earth site.
Point-in-polygon on the site's sampling point; if the point falls in no polygon (e.g. offshore by a few hundred m)
the nearest admin-1 polygon within 5 km is used and flagged. Antarctica has no admin-1 units -> null.
Output: data/raw/admin1/regions.json
"""
import shapefile
from shapely.geometry import shape, Point
from common import *

SHP = RAW / "basemap" / "ne_10m_admin_1_states_provinces" / "ne_10m_admin_1_states_provinces.shp"


def main():
    sf = shapefile.Reader(str(SHP), encoding="utf-8")
    fields = [f[0] for f in sf.fields[1:]]
    polys = []
    for sr in sf.iterShapeRecords():
        rec = dict(zip(fields, sr.record))
        polys.append((shape(sr.shape.__geo_interface__), rec))
    sites = load_json(CONFIG / "earth_sites_master.json")
    sites = sites["sites"] if isinstance(sites, dict) else sites
    out = {}
    for s in sites:
        pt = Point(s["lon"], s["lat"])
        hit = [(g, r) for g, r in polys if g.contains(pt)]
        how = "contains"
        if not hit:
            near = sorted(((g.distance(pt), g, r) for g, r in polys if g.distance(pt) < 0.05), key=lambda x: x[0])
            hit = [(near[0][1], near[0][2])] if near else []
            how = "nearest_within_~5km" if hit else "none"
        if hit:
            r = hit[0][1]
            out[s["site_id"]] = {"admin1": r.get("name"), "admin1_type": r.get("type_en"), "country": r.get("admin"), "iso_3166_2": r.get("iso_3166_2"), "match": how}
        else:
            out[s["site_id"]] = {"admin1": None, "match": how}
        print(s["site_id"], out[s["site_id"]])
    save_json({"source": "Natural Earth 1:10m Admin 1 - States, Provinces (public domain), https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip",
               "retrieved": "2026-11-15", "regions": out}, RAW / "admin1" / "regions.json")


if __name__ == "__main__":
    main()
