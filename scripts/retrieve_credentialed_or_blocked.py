"""Executable retrieval for sources that were NOT available in the 2026-11-15 build
(credentials required or blocked from the build host). Observations from these sources are
marked unavailable in the package; run this where access exists, then re-run steps 04-09.

  python scripts/retrieve_credentialed_or_blocked.py worldclim          # open, but TLS-blocked from build host
  python scripts/retrieve_credentialed_or_blocked.py overpass           # open, but TLS-blocked from build host
  EARTHDATA_TOKEN=... python scripts/retrieve_credentialed_or_blocked.py modis_lst   # NASA Earthdata (AppEEARS)
  python scripts/retrieve_credentialed_or_blocked.py era5_cds           # needs ~/.cdsapirc (Copernicus CDS)

Outputs go to data/raw/<source>/ in the same per-site JSON layout used by 04_build_features.py.
"""
import sys, os, time, zipfile, json
import requests
from common import *


def worldclim():
    """WorldClim 2.1 bioclim (10 arc-min) -> point values at every site."""
    import rasterio
    d = RAW / "worldclim"; d.mkdir(parents=True, exist_ok=True)
    z = d / "wc2.1_10m_bio.zip"
    if not z.exists():
        url = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_10m_bio.zip"
        with requests.get(url, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(z, "wb") as f:
                for ch in r.iter_content(1 << 20):
                    f.write(ch)
    with zipfile.ZipFile(z) as zf:
        zf.extractall(d)
    out = {}
    for s in earth_sites():
        rec = {"retrieved": RETRIEVAL_DATE}
        for b in (1, 5, 6, 7, 12):
            with rasterio.open(d / f"wc2.1_10m_bio_{b}.tif") as ds:
                v = list(ds.sample([(s["lon"], s["lat"])]))[0][0]
                rec[f"wc_bio{b}"] = None if (ds.nodata is not None and v == ds.nodata) or v < -1e30 else float(v)
        out[s["site_id"]] = rec
    save_json(out, d / "worldclim_points.json")
    print("WorldClim points written (note: WorldClim excludes Antarctica -> EA-004 null)")


def overpass():
    """Re-run access distances with OpenStreetMap Overpass instead of Natural Earth roads."""
    os.system(f"{sys.executable} {Path(__file__).parent / '02_retrieve_earth_data.py'} --refresh --skip dem,chelsa,permafrost,era5,macrostrat,soil")


def modis_lst():
    """MOD11A2 v061 day/night LST 2015-2024 at each site via NASA AppEEARS point request (Earthdata token)."""
    tok = os.environ.get("EARTHDATA_TOKEN")
    if not tok:
        sys.exit("Set EARTHDATA_TOKEN (create at https://urs.earthdata.nasa.gov/ -> Generate Token).")
    api = "https://appeears.earthdatacloud.nasa.gov/api"
    H = {"Authorization": f"Bearer {tok}"}
    task = {"task_type": "point", "task_name": "terraanalog_lst",
            "params": {"dates": [{"startDate": "01-01-2015", "endDate": "12-31-2024"}],
                       "layers": [{"product": "MOD11A2.061", "layer": "LST_Day_1km"}, {"product": "MOD11A2.061", "layer": "LST_Night_1km"}],
                       "coordinates": [{"id": s["site_id"], "latitude": s["lat"], "longitude": s["lon"], "category": s["group"]} for s in earth_sites()]}}
    r = requests.post(f"{api}/task", json=task, headers=H, timeout=120); r.raise_for_status()
    tid = r.json()["task_id"]; print("AppEEARS task", tid)
    while True:
        st = requests.get(f"{api}/status/{tid}", headers=H, timeout=60).json()
        if st.get("status") == "done":
            break
        time.sleep(60)
    d = RAW / "modis_lst"; d.mkdir(parents=True, exist_ok=True)
    for f in requests.get(f"{api}/bundle/{tid}", headers=H, timeout=60).json()["files"]:
        if f["file_name"].endswith(".csv"):
            b = requests.get(f"{api}/bundle/{tid}/{f['file_id']}", headers=H, timeout=600)
            (d / Path(f["file_name"]).name).write_bytes(b.content)
    print("MODIS LST CSVs in", d, "(LST in K = DN*0.02; QC filtering required)")


def era5_cds():
    """ERA5 monthly means of 2 m temperature, total precipitation and soil temperature level 4 via the CDS API."""
    import cdsapi  # pip install cdsapi ; requires ~/.cdsapirc with url + key
    c = cdsapi.Client()
    d = RAW / "era5_cds"; d.mkdir(parents=True, exist_ok=True)
    for s in earth_sites():
        area = [s["lat"] + 0.25, s["lon"] - 0.25, s["lat"] - 0.25, s["lon"] + 0.25]
        c.retrieve("reanalysis-era5-single-levels-monthly-means", {
            "product_type": ["monthly_averaged_reanalysis"], "variable": ["2m_temperature", "total_precipitation", "soil_temperature_level_4"],
            "year": [str(y) for y in range(1991, 2021)], "month": [f"{m:02d}" for m in range(1, 13)], "time": ["00:00"],
            "area": area, "data_format": "netcdf"}, str(d / f"{s['site_id']}.nc"))
    print("ERA5 CDS NetCDFs in", d)


if __name__ == "__main__":
    {"worldclim": worldclim, "overpass": overpass, "modis_lst": modis_lst, "era5_cds": era5_cds}[sys.argv[1]]()
