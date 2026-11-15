"""Step 2 - retrieve real open data at every Earth analog site (no credentials needed).

Sources (all accessed live; responses cached under data/raw/<source>/<site_id>.json):
  * Copernicus DEM GLO-30 COG tiles  - AWS open bucket (https, range reads)       -> terrain metrics
  * ESA WorldCover 10 m 2021 v200    - AWS open bucket (https, range reads)       -> land-cover fractions
  * CHELSA V2.1 1981-2010 bioclim    - EnviDat/WSL object store (https, range)    -> climate normals
  * ERA5 via Open-Meteo archive API  - daily 1991-2020                             -> climate, ET0, aridity
  * Obu et al. (2019) NH permafrost probability (PANGAEA zip, downloaded)          -> permafrost
  * Macrostrat map-unit lithology API (point query)                                -> mapped lithology text
  * ISRIC SoilGrids 2.0 REST API (0-5 cm sand/silt/clay)                           -> fine-sediment fraction
  * OpenStreetMap Overpass API (nearest highway/track)                              -> field access
WorldClim 2.1 is the preferred climate baseline but geodata.ucdavis.edu refused TLS from the
build host on 2026-11-15; scripts/retrieve_credentialed_or_blocked.py contains the retrieval
code to run where it is reachable.

Run:  python scripts/02_retrieve_earth_data.py [--only EA-001,EA-002] [--refresh] [--skip osm,soil]
"""
import sys, math, time, zipfile, traceback
import numpy as np
import requests
import rasterio
from rasterio.warp import Resampling, transform
from concurrent.futures import ThreadPoolExecutor
from common import *
from rasterwin import *

H = {"User-Agent": USER_AGENT}
REFRESH = "--refresh" in sys.argv
ONLY = None
SKIP = set()
for i, a in enumerate(sys.argv):
    if a == "--only":
        ONLY = set(sys.argv[i + 1].split(","))
    if a == "--skip":
        SKIP = set(sys.argv[i + 1].split(","))

HALF_M = 15500  # half-width of the analysis grid (m)
RES = 30.0
DEM_URL = "https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif"
WC_URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{t}_Map.tif"
CHELSA_URL = "https://os.zhdk.cloud.switch.ch/chelsav2/GLOBAL/climatologies/1981-2010/bio/CHELSA_{v}_1981-2010_V.2.1.tif"
WC_CLASSES = {10: "tree", 20: "shrub", 30: "grass", 40: "crop", 50: "built", 60: "bare_sparse", 70: "snow_ice",
              80: "water", 90: "wetland", 95: "mangrove", 100: "moss_lichen"}
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")


def cache(source, sid):
    p = RAW / source / f"{sid}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def deg_bounds(lat, lon, half_m):
    dlat = half_m / 110574.0 * 1.15
    dlon = half_m / (111320.0 * max(math.cos(math.radians(lat)), 0.05)) * 1.15
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def dem_tile_names(b):
    names = []
    for la in range(math.floor(b[1]), math.floor(b[3]) + 1):
        for lo in range(math.floor(b[0]), math.floor(b[2]) + 1):
            ns = f"N{la:02d}" if la >= 0 else f"S{-la:02d}"
            ew = f"E{lo:03d}" if lo >= 0 else f"W{-lo:03d}"
            names.append(f"Copernicus_DSM_COG_10_{ns}_00_{ew}_00_DEM")
    return names


def wc_tile_names(b):
    names = set()
    for la in range(math.floor(b[1] / 3) * 3, math.floor(b[3] / 3) * 3 + 1, 3):
        for lo in range(math.floor(b[0] / 3) * 3, math.floor(b[2] / 3) * 3 + 1, 3):
            ns = f"N{la:02d}" if la >= 0 else f"S{-la:02d}"
            ew = f"E{lo:03d}" if lo >= 0 else f"W{-lo:03d}"
            names.add(ns + ew)
    return sorted(names)


def open_many(urls):
    out, used, missing = [], [], []
    for u in urls:
        try:
            out.append(rasterio.open("/vsicurl/" + u)); used.append(u)
        except Exception:
            missing.append(u)
    return out, used, missing


def terrain_and_cover(s):
    p = cache("dem", s["site_id"])
    if p.exists() and not REFRESH:
        return load_json(p)
    lat, lon = s["lat"], s["lon"]
    b = deg_bounds(lat, lon, HALF_M)
    crs = aeqd_crs(lat, lon)
    tr, shape = target_grid(HALF_M, RES)
    dem_ds, dem_used, dem_missing = open_many([DEM_URL.format(n=n) for n in dem_tile_names(b)])
    z = warp_sources_to_grid(dem_ds, crs, tr, shape, Resampling.bilinear)
    wc_ds, wc_used, wc_missing = open_many([WC_URL.format(t=t) for t in wc_tile_names(b)])
    wc = warp_sources_to_grid(wc_ds, crs, tr, shape, Resampling.nearest) if wc_ds else np.full(shape, np.nan, "float32")
    for d in dem_ds + wc_ds:
        d.close()
    # Mask open water (WorldCover class 80) - Copernicus DEM is flattened over water bodies
    water = wc == 80
    z_land = z.copy(); z_land[water] = np.nan
    np.savez_compressed(RAW / "dem" / f"{s['site_id']}_grid30m.npz", z=z.astype("float32"), wc=wc.astype("float32"))
    rec = {"site_id": s["site_id"], "retrieved": RETRIEVAL_DATE, "grid_crs": crs.to_proj4(), "grid_res_m": RES,
           "dem_tiles_used": dem_used, "dem_tiles_missing": dem_missing, "worldcover_tiles_used": wc_used,
           "worldcover_tiles_missing": wc_missing, "water_masked_pixels": int(water.sum())}
    rec.update(terrain_metrics(z_land, RES, 2000, "t30m_r2km"))
    rec.update(terrain_metrics(block_mean(z_land, 3), RES * 3, 5000, "t90m_r5km"))
    rec.update(terrain_metrics(block_mean(z_land, 15), RES * 15, 15000, "t450m_r15km"))
    # point elevation (nearest grid cell to centre)
    c = shape[0] // 2
    rec["elev_point_m"] = None if np.isnan(z[c, c]) else float(z[c, c])
    m5 = disk_mask(shape, RES, 5000)
    v = wc[m5]; v = v[~np.isnan(v)]
    if v.size:
        for k, name in WC_CLASSES.items():
            rec[f"wc_frac_{name}_r5km"] = float(np.mean(v == k))
        rec["wc_valid_fraction_r5km"] = float(v.size / m5.sum())
    else:
        for name in WC_CLASSES.values():
            rec[f"wc_frac_{name}_r5km"] = None
        rec["wc_valid_fraction_r5km"] = 0.0
    save_json(rec, p)
    return rec


def chelsa(sites):
    p = RAW / "chelsa" / "chelsa_points.json"
    if p.exists() and not REFRESH:
        return load_json(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    # CHELSA V2.1 encoding: temperatures = DN*0.1 - 273.15 (deg C); bio7 = DN*0.1 (K); bio12 = DN*0.1 (kg m-2 yr-1)
    spec = {"bio1": (0.1, -273.15), "bio5": (0.1, -273.15), "bio6": (0.1, -273.15), "bio7": (0.1, 0.0), "bio12": (0.1, 0.0)}
    out = {s["site_id"]: {"retrieved": RETRIEVAL_DATE} for s in sites}
    for v, (sc, off) in spec.items():
        url = CHELSA_URL.format(v=v)
        with rasterio.open("/vsicurl/" + url) as d:
            for s in sites:
                val = list(d.sample([(s["lon"], s["lat"])]))[0][0]
                ok = val != 0 and (d.nodata is None or val != d.nodata) and val < 65535
                out[s["site_id"]][f"chelsa_{v}"] = float(val) * sc + off if ok else None
                out[s["site_id"]][f"chelsa_{v}_url"] = url
    save_json(out, p)
    return out


def era5(s):
    p = cache("era5", s["site_id"])
    if p.exists() and not REFRESH:
        return load_json(p)
    params = {"latitude": s["lat"], "longitude": s["lon"], "start_date": "1991-01-01", "end_date": "2020-12-31",
              "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration,wind_speed_10m_max,shortwave_radiation_sum",
              "models": "era5", "timezone": "GMT"}
    for attempt in range(5):
        r = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, headers=H, timeout=180)
        if r.status_code == 200:
            break
        time.sleep(20 * (attempt + 1))
    r.raise_for_status()
    j = r.json()
    d = j["daily"]
    tm = np.array(d["temperature_2m_mean"], float); tx = np.array(d["temperature_2m_max"], float)
    tn = np.array(d["temperature_2m_min"], float); pr = np.array(d["precipitation_sum"], float)
    et = np.array(d["et0_fao_evapotranspiration"], float); ws = np.array(d["wind_speed_10m_max"], float)
    sw = np.array(d["shortwave_radiation_sum"], float)
    months = np.array([int(t[5:7]) for t in d["time"]])
    years = 30.0
    mon_means = [float(np.nanmean(tm[months == m])) for m in range(1, 13)]
    P, E = float(np.nansum(pr) / years), float(np.nansum(et) / years)
    rec = {"site_id": s["site_id"], "retrieved": RETRIEVAL_DATE, "source": "Open-Meteo Historical Weather API, models=era5",
           "request": r.url, "grid_lat": j["latitude"], "grid_lon": j["longitude"], "grid_elevation_m": j.get("elevation"),
           "period": "1991-01-01/2020-12-31", "n_days": int(len(tm)),
           "era5_t_mean_c": float(np.nanmean(tm)), "era5_t_min_p01_c": float(np.nanpercentile(tn, 1)),
           "era5_t_max_p99_c": float(np.nanpercentile(tx, 99)), "era5_diurnal_range_c": float(np.nanmean(tx - tn)),
           "era5_precip_mm_yr": P, "era5_et0_mm_yr": E, "era5_aridity_index": (P / E) if E > 0 else None,
           "era5_freeze_thaw_days_yr": float(np.sum((tx > 0) & (tn < 0)) / years),
           "era5_wind_max_mean_kmh": float(np.nanmean(ws)), "era5_sw_rad_mj_m2_day": float(np.nanmean(sw)),
           "era5_monthly_t_mean_c": mon_means}
    save_json(rec, p)
    time.sleep(3)
    return rec


_PERPROB = None


def permafrost(sites):
    p = RAW / "permafrost" / "obu_points.json"
    if p.exists() and not REFRESH:
        return load_json(p)
    z = RAW / "permafrost" / "UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.zip"
    if not z.exists():
        url = "https://store.pangaea.de/Publications/ObuJ-etal_2018/UiO_PEX_PERPROB_5.0_20181128_2000_2016_NH.zip"
        with requests.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(z, "wb") as f:
                for ch in r.iter_content(1 << 20):
                    f.write(ch)
    with zipfile.ZipFile(z) as zf:
        tif = [n for n in zf.namelist() if n.lower().endswith(".tif")][0]
        if not (RAW / "permafrost" / Path(tif).name).exists():
            zf.extract(tif, RAW / "permafrost")
            (RAW / "permafrost" / tif).rename(RAW / "permafrost" / Path(tif).name) if Path(tif).name != tif else None
    tifp = RAW / "permafrost" / Path(tif).name
    out = {}
    with rasterio.open(tifp) as d:
        for s in sites:
            rec = {"retrieved": RETRIEVAL_DATE, "file": tifp.name}
            if s["lat"] < 25:
                rec.update({"obu_perprob": None, "note": "outside product coverage (Northern Hemisphere >= 25N only)"})
            else:
                xs, ys = transform("EPSG:4326", d.crs, [s["lon"]], [s["lat"]])
                v = list(d.sample([(xs[0], ys[0])]))[0][0]
                ok = d.nodata is None or v != d.nodata
                rec["obu_perprob"] = float(v) if ok and v >= 0 and v <= 1.0001 else None
                if rec["obu_perprob"] is None:
                    rec["note"] = f"nodata/out-of-range value {float(v)} (e.g. glacier/water/excluded)"
            out[s["site_id"]] = rec
    save_json(out, p)
    return out


def macrostrat(s):
    p = cache("macrostrat", s["site_id"])
    if p.exists() and not REFRESH:
        return load_json(p)
    url = "https://macrostrat.org/api/v2/geologic_units/map"
    rec = {"site_id": s["site_id"], "retrieved": RETRIEVAL_DATE, "units": []}
    for scale in ("large", "medium", "small", "tiny"):
        try:
            r = requests.get(url, params={"lat": s["lat"], "lng": s["lon"], "scale": scale}, headers=H, timeout=60)
            data = r.json().get("success", {})
            for u in data.get("data", []):
                rec["units"].append({"scale": scale, "name": u.get("name"), "lith": u.get("lith"), "descrip": (u.get("descrip") or "")[:300],
                                     "age": u.get("best_int_name"), "source_ref": data.get("refs", {}).get(str(u.get("source_id")))})
        except Exception as e:
            rec.setdefault("errors", []).append(f"{scale}: {e}")
        time.sleep(0.5)
    save_json(rec, p)
    return rec


def soilgrids(s):
    p = cache("soilgrids", s["site_id"])
    if p.exists() and not REFRESH:
        return load_json(p)
    url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    params = [("lon", s["lon"]), ("lat", s["lat"]), ("property", "sand"), ("property", "silt"), ("property", "clay"),
              ("depth", "0-5cm"), ("value", "mean"), ("value", "Q0.05"), ("value", "Q0.95")]
    rec = {"site_id": s["site_id"], "retrieved": RETRIEVAL_DATE}
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, headers=H, timeout=90)
            if r.status_code == 200:
                for layer in r.json()["properties"]["layers"]:
                    vals = layer["depths"][0]["values"]
                    f = layer["unit_measure"]["d_factor"]
                    for k, v in vals.items():
                        rec[f"soil_{layer['name']}_{k}_pct"] = None if v is None else v / f
                rec["request"] = r.url
                break
            rec["http_status"] = r.status_code
        except Exception as e:
            rec["error"] = str(e)
        time.sleep(15)
    save_json(rec, p)
    time.sleep(13)  # ISRIC fair-use: <= 5 requests/minute
    return rec


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371008.8 * math.asin(math.sqrt(a))


def osm_access(s):
    p = cache("osm", s["site_id"])
    if p.exists() and not REFRESH:
        return load_json(p)
    rec = {"site_id": s["site_id"], "retrieved": RETRIEVAL_DATE, "source": "OpenStreetMap via Overpass API (ODbL)"}
    hw = "motorway|trunk|primary|secondary|tertiary|unclassified|residential|track|service"
    for radius in (2000, 10000, 50000, 150000):
        q = f'[out:json][timeout:120];way[highway~"^({hw})$"](around:{radius},{s["lat"]},{s["lon"]});out geom 400;'
        for ep in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
            try:
                r = requests.post(ep, data={"data": q}, headers=H, timeout=200)
                if r.status_code == 200:
                    els = r.json().get("elements", [])
                    break
            except Exception as e:
                rec.setdefault("errors", []).append(str(e)); els = None
        else:
            els = None
        if els is None:
            rec["road_distance_m"] = None; rec["note"] = "Overpass unavailable"; break
        if els:
            best, kind = 1e12, None
            for w in els:
                for g in w.get("geometry", []):
                    d = haversine(s["lat"], s["lon"], g["lat"], g["lon"])
                    if d < best:
                        best, kind = d, w.get("tags", {}).get("highway")
            rec.update({"road_distance_m": best, "nearest_highway_class": kind, "search_radius_m": radius,
                        "note": "distance to nearest mapped vertex of the nearest way (upper bound of true distance)"})
            break
        time.sleep(2)
    else:
        rec.update({"road_distance_m": None, "road_distance_censored_gt_m": 150000,
                    "note": "no mapped highway/track within 150 km (right-censored)"})
    save_json(rec, p)
    time.sleep(2)
    return rec


def main():
    sites = [s for s in earth_sites() if ONLY is None or s["site_id"] in ONLY]
    t0 = time.time()
    if "dem" not in SKIP:
        with ThreadPoolExecutor(4) as ex:
            for s, r in zip(sites, ex.map(lambda s: _safe(terrain_and_cover, s), sites)):
                print("dem", s["site_id"], r.get("t30m_r2km_slope_median_deg") if r else "ERR", f"{time.time()-t0:.0f}s", flush=True)
    if "chelsa" not in SKIP:
        chelsa(earth_sites()); print("chelsa done", flush=True)
    if "permafrost" not in SKIP:
        permafrost(earth_sites()); print("permafrost done", flush=True)
    for name, fn in (("era5", era5), ("macrostrat", macrostrat), ("osm", osm_access), ("soil", soilgrids)):
        if name in SKIP:
            continue
        for s in sites:
            r = _safe(fn, s)
            print(name, s["site_id"], "ok" if r else "ERR", f"{time.time()-t0:.0f}s", flush=True)


def _safe(fn, s):
    try:
        return fn(s)
    except Exception:
        print("ERROR", fn.__name__, s["site_id"], traceback.format_exc()[-600:], flush=True)
        return None


if __name__ == "__main__":
    main()
