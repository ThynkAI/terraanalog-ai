"""Step 02b - SoilGrids 2.0 nearest-valid-pixel fallback for sites whose point query returned no data.

Reads the official SoilGrids 2.0 0-5 cm mean VRTs (Interrupted Goode Homolosine, 250 m, g/kg) from
files.isric.org with GDAL range requests, searches a window of radius MAX_KM around the site and keeps the nearest
pixel where sand, silt and clay are all valid. Nothing is interpolated: the value is that pixel's value, its distance
is recorded, and sites with no valid pixel within MAX_KM stay null.
Output: data/raw/soilgrids/<site_id>_nearby.json
"""
import json, math, sys
import os
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR"); os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".vrt,.tif"); os.environ.setdefault("GDAL_HTTP_TIMEOUT", "60")
import numpy as np, rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer
from common import *

MAX_KM = 10.0


def ropen(path, tries=5):
    """rasterio.open with retries - the remote VRT is ~6 MB and range reads occasionally fail."""
    import time
    for k in range(tries):
        try:
            return rasterio.open(path)
        except rasterio.errors.RasterioIOError:
            if k == tries - 1:
                raise
            time.sleep(10 * (k + 1))
BASE = "/vsicurl/https://files.isric.org/soilgrids/latest/data/{p}/{p}_0-5cm_mean.vrt"


def main():
    sites = load_json(CONFIG / "earth_sites_master.json")
    sites = sites["sites"] if isinstance(sites, dict) else sites
    todo = [s for s in sites if (load_json(RAW / "soilgrids" / f"{s['site_id']}.json") or {}).get("soil_silt_mean_pct") is None]
    print("sites needing fallback:", [s["site_id"] for s in todo])
    for s in todo:
        if (RAW / "soilgrids" / f"{s['site_id']}_nearby.json").exists() and "--force" not in sys.argv:
            print(s["site_id"], "already done"); continue
        out = {"site_id": s["site_id"], "retrieved": "2026-11-15", "method": f"nearest pixel with valid sand/silt/clay within {MAX_KM} km (no interpolation)",
               "sources": [BASE.format(p=p).replace("/vsicurl/", "") for p in ("sand", "silt", "clay")]}
        arrs = {}
        with ropen(BASE.format(p="silt")) as ds:
            tr = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
            x, y = tr.transform(s["lon"], s["lat"])
            r = MAX_KM * 1000 * 1.5  # homolosine distortion margin
            win = from_bounds(x - r, y - r, x + r, y + r, ds.transform).round_offsets().round_lengths()
            wt = ds.window_transform(win)
            crs = ds.crs
        for p in ("sand", "silt", "clay"):
            with ropen(BASE.format(p=p)) as ds:
                a = ds.read(1, window=win, boundless=True, fill_value=ds.nodata if ds.nodata is not None else -32768).astype(float)
                nd = ds.nodata
                a[(a == nd) | (a <= 0)] = np.nan if p != "clay" else np.nan
                arrs[p] = a
        valid = ~np.isnan(arrs["sand"]) & ~np.isnan(arrs["silt"]) & ~np.isnan(arrs["clay"])
        rows, cols = np.nonzero(valid)
        if len(rows) == 0:
            out.update({"found": False, "note": f"no valid SoilGrids pixel within the {MAX_KM} km search window"})
        else:
            xs, ys = rasterio.transform.xy(wt, rows, cols)
            back = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
            lons, lats = back.transform(np.array(xs), np.array(ys))
            # great-circle distance
            R = 6371.0088
            dl = np.radians(np.array(lats) - s["lat"]); dn = np.radians(np.array(lons) - s["lon"])
            h = np.sin(dl / 2) ** 2 + np.cos(math.radians(s["lat"])) * np.cos(np.radians(lats)) * np.sin(dn / 2) ** 2
            d = 2 * R * np.arcsin(np.sqrt(h))
            i = int(np.argmin(d))
            if d[i] > MAX_KM:
                out.update({"found": False, "note": f"nearest valid pixel {d[i]:.1f} km > {MAX_KM} km"})
            else:
                rr, cc = rows[i], cols[i]
                out.update({"found": True, "distance_km": round(float(d[i]), 3), "pixel_lon": round(float(lons[i]), 5), "pixel_lat": round(float(lats[i]), 5),
                            **{f"soil_{p}_mean_pct": round(float(arrs[p][rr, cc]) / 10.0, 1) for p in ("sand", "silt", "clay")},
                            "units_note": "SoilGrids stores g/kg; divided by 10 to give %"})
        save_json(out, RAW / "soilgrids" / f"{s['site_id']}_nearby.json")
        print(s["site_id"], out.get("found"), out.get("distance_km"), out.get("soil_silt_mean_pct"), out.get("note", ""))


if __name__ == "__main__":
    main()
