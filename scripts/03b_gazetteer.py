"""Step 03b - USGS Gazetteer of Planetary Nomenclature (IAU WGPSN) feature IDs for the planetary references.

Downloads the full Moon and Mars search-result tables from planetarynames.wr.usgs.gov (HTML), parses every row
(feature ID, name, diameter, centre lat/lon, coordinate system, approval) and resolves each reference to a gazetteer
feature using config/planetary_references.json -> "gazetteer" {"name", "match"}:
  match = exact      -> the reference IS the named feature (diameter usable)
  match = containing -> the reference lies inside the named feature (checked against the feature's bounding box);
                        the feature ID is context only, its diameter is NOT the reference's
References without a named feature keep null.
Each matched feature's own page (planetarynames.wr.usgs.gov/Feature/<id>) is also fetched. Some pages carry geometry
for more than one control network (Mars: MDIM 2.0 and the currently selected MDIM 2.1, e.g. Planum Boreum 1100 km vs
354.63 km). Values are taken from the control network the page marks as selected, which is also what the search table
lists; the script asserts they agree and records the network label.
Output: data/raw/gazetteer/gazetteer_<body>.json, data/raw/gazetteer/reference_matches.json
"""
import re, sys, requests
from common import *

URLS = {"Moon": "https://planetarynames.wr.usgs.gov/SearchResults?Target=16_Moon",
        "Mars": "https://planetarynames.wr.usgs.gov/SearchResults?Target=20_Mars"}
GZ = RAW / "gazetteer"


def parse(html, body):
    out = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        ids = re.findall(r"Feature/(\d+)", r)
        if not ids:
            continue
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        # columns: id, name, clean name, target, diameter, centre lat, centre lon, N, S, E, W, coord system, ...
        try:
            fid, name, _, target, diam, clat, clon, n, s, e, w, csys = cells[:12]
            out[fid] = {"feature_id": int(fid), "name": name, "target": target, "diameter_km": float(diam) if diam else None,
                        "center_lat": float(clat), "center_lon": float(clon), "north": float(n), "south": float(s), "east": float(e), "west": float(w),
                        "coordinate_system": csys, "approval": next((c for c in cells if c.startswith("Approved") or c.startswith("Dropped")), None),
                        "url": f"https://planetarynames.wr.usgs.gov/Feature/{fid}"}
        except (ValueError, IndexError):
            continue
    return out


def feature_page(fid):
    f = GZ / f"feature_{fid}.html"
    if not f.exists() or "--refresh" in sys.argv:
        r = requests.get(f"https://planetarynames.wr.usgs.gov/Feature/{fid}", timeout=120, headers={"User-Agent": "TerraAnalogAI/1.0 (research; contact via GitHub ThynkAI)"})
        r.raise_for_status(); f.write_text(r.text, encoding="utf-8")
    h = f.read_text(encoding="utf-8")
    m_sel = re.search(r'<select name="selected_control_net".*?</select>', h, re.S)
    cs = re.search(r'id="selected_coordinate_system" type="hidden" value="(\d+)"', h).group(1)
    if m_sel:
        opts = re.findall(r'<option label="([^"]*)" value="(\d+)"\s*(selected)?', m_sel.group(0))
        label, gid = next(((l, v) for l, v, s_ in opts if s_), (opts[0][0], opts[0][1]))
    else:  # single control network on the page (no selector)
        gid = re.search(r'<tr class="geometry geom-(\d+) cs-%s">' % cs, h).group(1)
        m_net = re.search(r"Control Network</th>\s*<td>\s*([^<]+?)\s*</td>", h)
        label = m_net.group(1) if m_net else "single network (label not shown)"
        opts = [(label, gid, "selected")]
    rows = re.findall(r'<tr class="geometry geom-%s cs-%s">\s*<th>([^<]+)</th>\s*<td>(.*?)</td>' % (gid, cs), h, re.S)
    vals = {}
    for k, v in rows:
        m = re.search(r"(-?[0-9.]+)", re.sub(r"<[^>]+>", " ", v))
        if m and k.strip() not in vals:
            vals[k.strip()] = float(m.group(1))
    return {"control_network": label, "diameter_km": vals.get("Diameter"), "center_lat": vals.get("Center Latitude"),
            "center_lon": vals.get("Center Longitude"), "networks_on_page": [l for l, _, _ in opts]}


def lon_in(lon, west, east, system360):
    if system360:
        lon %= 360
    lo, hi = min(west, east), max(west, east)
    return lo <= lon <= hi


def main():
    GZ.mkdir(parents=True, exist_ok=True)
    tables = {}
    for body, url in URLS.items():
        f = GZ / f"{body.lower()}_searchresults.html"
        if not f.exists() or "--refresh" in sys.argv:
            r = requests.get(url, timeout=180, headers={"User-Agent": "TerraAnalogAI/1.0 (research; contact via GitHub ThynkAI)"})
            r.raise_for_status(); f.write_text(r.text, encoding="utf-8")
        tables[body] = parse(f.read_text(encoding="utf-8"), body)
        save_json({"source": url, "retrieved": "2026-11-15", "n_features": len(tables[body]), "features": tables[body]}, GZ / f"gazetteer_{body.lower()}.json")
        print(body, len(tables[body]), "features")
    refs = load_json(CONFIG / "planetary_references.json")["references"]
    res = {}
    for ref in refs:
        g = ref.get("gazetteer") or {}
        rid = ref["ref_id"]
        if not g.get("name"):
            res[rid] = {"feature_id": None, "match": "none", "note": g.get("note", "no named gazetteer feature")}
            continue
        cands = [v for v in tables[ref["body"]].values() if v["name"] == g["name"]]
        if len(cands) != 1:
            raise SystemExit(f"{rid}: {len(cands)} gazetteer rows named {g['name']}")
        v = cands[0]
        is360 = "0 - 360" in v["coordinate_system"]
        inside = v["south"] <= ref["lat"] <= v["north"] and lon_in(ref["lon"], v["west"], v["east"], is360)
        if g["match"] == "containing" and not inside:
            raise SystemExit(f"{rid} not inside {g['name']} bounding box")
        fp = feature_page(v["feature_id"])
        if fp["diameter_km"] is not None and v["diameter_km"] is not None and abs(fp["diameter_km"] - v["diameter_km"]) > 0.01:
            raise SystemExit(f"{rid}: feature page ({fp['control_network']}) diameter {fp['diameter_km']} != search table {v['diameter_km']}")
        res[rid] = {**v, "control_network": fp["control_network"], "networks_on_page": fp["networks_on_page"],
                    "match": g["match"], "reference_inside_bbox": inside}
        print(rid, g["match"], v["feature_id"], v["name"], v["diameter_km"], "inside" if inside else "outside")
    save_json(res, GZ / "reference_matches.json")


if __name__ == "__main__":
    main()
