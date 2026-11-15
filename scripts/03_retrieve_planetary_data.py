"""Step 3 - planetary reference terrain from real NASA/USGS DEMs (no credentials).

  * LRO LOLA polar gridded DEM  LDEM_80S_80M (PDS Geosciences Node, polar stereographic, 80 m/px)
      -> south-polar references (MOON-REF-01..04)
  * LRO LOLA global DEM 118 m  (USGS Astrogeology mosaic, range reads)  -> MOON-REF-05..07
  * MGS MOLA global DEM 463 m  (USGS Astrogeology mosaic, range reads)  -> MARS-REF-01..07
Each DEM window is reprojected onto a body-fixed azimuthal-equidistant grid centred on the
reference (sphere radius from the product label) and slope/roughness are computed with the
same Horn/Riley code used for Earth (scripts/rasterwin.py) at the matched baselines:
Moon 90 m grid, Mars 450 m grid.
Run:  python scripts/03_retrieve_planetary_data.py [--refresh]
"""
import sys, requests
import numpy as np
import rasterio
from rasterio.warp import Resampling
from common import *
from rasterwin import *

REFRESH = "--refresh" in sys.argv
PDS = "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/"
DEMS = {
    "LOLA_80S_80M": {"path": str(RAW / "planetary" / "ldem_80s_80m.lbl"), "R": 1737400.0, "scale": 0.5,
                     "url": PDS + "ldem_80s_80m.img", "product": "LRO LOLA LDEM_80S_80M (PDS3, LRO-L-LOLA-4-GDR-V1.0)"},
    "LOLA_GLOBAL_118M": {"path": "/vsicurl/https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif",
                         "R": 1737400.0, "scale": 1.0, "url": "https://planetarymaps.usgs.gov/mosaic/Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif",
                         "product": "LRO LOLA global LDEM 118 m (USGS Astrogeology mosaic, Mar 2014)"},
    "MOLA_463M": {"path": "/vsicurl/https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif",
                  "R": 3396190.0, "scale": 1.0, "url": "https://planetarymaps.usgs.gov/mosaic/Mars_MGS_MOLA_DEM_mosaic_global_463m.tif",
                  "product": "MGS MOLA global DEM 463 m (USGS Astrogeology mosaic)"},
}


def ensure_lola_polar():
    d = RAW / "planetary"; d.mkdir(parents=True, exist_ok=True)
    for ext in ("lbl", "img"):
        p = d / f"ldem_80s_80m.{ext}"
        if not p.exists():
            with requests.get(PDS + p.name, stream=True, timeout=900) as r:
                r.raise_for_status()
                with open(p, "wb") as f:
                    for ch in r.iter_content(1 << 20):
                        f.write(ch)


def main():
    ensure_lola_polar()
    out_p = RAW / "planetary" / "planetary_terrain.json"
    out = {} if REFRESH or not out_p.exists() else load_json(out_p)
    for r in planetary_refs():
        if r["ref_id"] in out:
            continue
        dem = DEMS[r["dem"]]
        res = 90.0 if r["body"] == "Moon" else 450.0
        half = r["sample_radius_m"] * 1.05
        crs = aeqd_crs(r["lat"], r["lon"], dem["R"])
        tr, shape = target_grid(half, res)
        with rasterio.open(dem["path"]) as ds:
            # Planetary products ship WKT with body-specific GEOGCS; rasterio/PROJ handles the sphere.
            z = warp_sources_to_grid([ds], crs, tr, shape, Resampling.bilinear, scale=dem["scale"])
        prefix = "t90m" if r["body"] == "Moon" else "t450m"
        rec = {"ref_id": r["ref_id"], "dem_key": r["dem"], "product": dem["product"], "url": dem["url"],
               "retrieved": RETRIEVAL_DATE, "grid_res_m": res, "radius_m": r["sample_radius_m"], "grid_crs": crs.to_proj4()}
        m = terrain_metrics(z, res, r["sample_radius_m"], prefix)
        rec.update({k.replace(prefix + "_", "ref_"): v for k, v in m.items()})
        c = shape[0] // 2
        rec["ref_elev_point_m"] = None if np.isnan(z[c, c]) else float(z[c, c])
        rec["elevation_datum"] = ("height above 1737.4 km reference sphere" if r["body"] == "Moon" else
                                  "MOLA areoid-referenced elevation (USGS mosaic)")
        out[r["ref_id"]] = rec
        print(r["ref_id"], {k: clean(v, 2) for k, v in rec.items() if k.startswith("ref_")}, flush=True)
        save_json(out, out_p)


if __name__ == "__main__":
    main()
