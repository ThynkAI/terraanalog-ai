"""Step 02d - categorical climate classes for each Earth site.

* climate_class: Koppen-Geiger type computed with the criteria of Peel, Finlayson & McMahon (2007), HESS 11:1633,
  doi:10.5194/hess-11-1633-2007, Table 1 (B tested first; Cs/Cw and Ds/Dw tie broken by half-year precipitation as in
  their section 3), from ERA5 1991-2020 monthly normals of 2 m mean temperature and precipitation at the same
  ERA5 grid cell used elsewhere (Open-Meteo Historical Weather API, models=era5). The ERA5 cell is 0.25 deg with its
  own elevation (grid_elevation_m), so the class describes the grid cell, not necessarily the exact sampling point.
* aridity_class: class of the ERA5 P/ET0 aridity index using the UNEP scheme as tabulated in Zomer et al. (2022),
  Sci Data 9:409, doi:10.1038/s41597-022-01493-1: <0.03 hyper-arid, 0.03-0.2 arid, 0.2-0.5 semi-arid,
  0.5-0.65 dry sub-humid, >0.65 humid.
Output: data/raw/era5_monthly/<site_id>.json (monthly normals) and data/raw/era5_monthly/climate_classes.json
"""
import json, time, requests
from collections import defaultdict
from common import *

OUT = RAW / "era5_monthly"
H = {"User-Agent": "TerraAnalogAI/1.0"}


def monthly_normals(sid):
    p = OUT / f"{sid}.json"
    if p.exists():
        return load_json(p)
    era = load_json(RAW / "era5" / f"{sid}.json")
    lat, lon = era["grid_lat"], era["grid_lon"]
    url = ("https://archive-api.open-meteo.com/v1/archive?latitude={}&longitude={}&start_date=1991-01-01&end_date=2020-12-31"
           "&daily=temperature_2m_mean%2Cprecipitation_sum&models=era5&timezone=GMT").format(lat, lon)
    for k in range(5):
        r = requests.get(url, headers=H, timeout=120)
        if r.status_code == 200:
            break
        time.sleep(20 * (k + 1))
    r.raise_for_status()
    d = r.json()["daily"]
    t_by = defaultdict(list); p_by = defaultdict(float); n_by = defaultdict(int)
    years = set()
    for day, t, pr in zip(d["time"], d["temperature_2m_mean"], d["precipitation_sum"]):
        y, m = int(day[:4]), int(day[5:7])
        years.add(y)
        if t is not None:
            t_by[m].append(t)
        if pr is not None:
            p_by[m] += pr; n_by[m] += 1
    ny = len(years)
    rec = {"site_id": sid, "retrieved": "2026-11-15", "request": url, "period": "1991-2020", "grid_lat": lat, "grid_lon": lon,
           "grid_elevation_m": r.json().get("elevation"),
           "monthly_t_mean_c": [round(sum(t_by[m]) / len(t_by[m]), 3) for m in range(1, 13)],
           "monthly_precip_mm": [round(p_by[m] / ny, 2) for m in range(1, 13)],
           "n_years": ny}
    save_json(rec, p)
    time.sleep(1.0)
    return rec


def koppen(T, P, lat):
    MAT, MAP = sum(T) / 12, sum(P)
    Thot, Tcold = max(T), min(T)
    summer = [3, 4, 5, 6, 7, 8] if lat >= 0 else [9, 10, 11, 0, 1, 2]  # AMJJAS (NH) / ONDJFM (SH), 0-based months
    winter = [m for m in range(12) if m not in summer]
    Ps, Pw = sum(P[m] for m in summer), sum(P[m] for m in winter)
    if MAP > 0 and Pw >= 0.7 * MAP: Pth = 2 * MAT
    elif MAP > 0 and Ps >= 0.7 * MAP: Pth = 2 * MAT + 28
    else: Pth = 2 * MAT + 14
    Tmon10 = sum(1 for t in T if t > 10)
    if MAP < 10 * Pth:
        return "B" + ("W" if MAP < 5 * Pth else "S") + ("h" if MAT >= 18 else "k"), Pth
    if Thot < 10:
        return ("ET" if Thot > 0 else "EF"), Pth
    if Tcold >= 18:
        Pdry = min(P)
        return ("Af" if Pdry >= 60 else ("Am" if Pdry >= 100 - MAP / 25 else "Aw")), Pth
    Psdry, Pwdry = min(P[m] for m in summer), min(P[m] for m in winter)
    Pswet, Pwwet = max(P[m] for m in summer), max(P[m] for m in winter)
    s = Psdry < 40 and Psdry < Pwwet / 3
    w = Pwdry < Pswet / 10
    second = ("w" if Ps > Pw else "s") if (s and w) else ("s" if s else ("w" if w else "f"))
    first = "C" if Tcold > 0 else "D"
    if Thot >= 22: third = "a"
    elif Tmon10 >= 4: third = "b"
    elif first == "D" and Tcold < -38: third = "d"
    else: third = "c"
    return first + second + third, Pth


def aridity_class(ai):
    if ai is None: return None
    if ai < 0.03: return "hyper-arid"
    if ai < 0.2: return "arid"
    if ai < 0.5: return "semi-arid"
    if ai <= 0.65: return "dry sub-humid"
    return "humid"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    out = {}
    for s in earth_sites():
        sid = s["site_id"]
        mn = monthly_normals(sid)
        era = load_json(RAW / "era5" / f"{sid}.json")
        k, pth = koppen(mn["monthly_t_mean_c"], mn["monthly_precip_mm"], s["lat"])
        out[sid] = {"climate_class": k, "aridity_class": aridity_class(era.get("era5_aridity_index")),
                    "aridity_index": era.get("era5_aridity_index"), "MAP_mm": round(sum(mn["monthly_precip_mm"]), 1),
                    "MAT_c": round(sum(mn["monthly_t_mean_c"]) / 12, 2), "Thot_c": max(mn["monthly_t_mean_c"]), "Tcold_c": min(mn["monthly_t_mean_c"]),
                    "Pthreshold_mm": round(pth, 1), "grid_elevation_m": era.get("grid_elevation_m")}
        print(sid, out[sid])
    save_json({"method": __doc__, "classes": out}, OUT / "climate_classes.json")


if __name__ == "__main__":
    main()
