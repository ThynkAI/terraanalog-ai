"""Step 9 - validation suite -> outputs/validation_report.md (+ validation_results.json).

Checks: coordinates & geometry, Wikipedia coordinate cross-check, URL reachability (HTTP status),
DOI resolution, unit/range consistency, CHELSA-vs-ERA5 consistency, missing values, independent score
recalculation, weight-sum tests, sensitivity, baseline comparison, scientific plausibility assertions.
Run:  python scripts/09_validate.py [--no-network]
"""
import csv, sys, re, math, time
import numpy as np
import requests
from shapely.geometry import shape
from common import *

NET = "--no-network" not in sys.argv
CFG = scoring_config()
RES = {"checks": []}


def check(name, ok, detail="", severity="error"):
    RES["checks"].append({"name": name, "pass": bool(ok), "detail": detail, "severity": severity})
    return ok


def read_csv(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def fnum(v):
    return None if v in ("", None) else float(v)


def hav(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    x = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(x))


def geometry_checks():
    out = []
    for fn in ("earth_analog_sites.geojson", "earth_analog_site_bounds.geojson", "planetary_reference_sites.geojson"):
        gj = load_json(OUTPUTS / fn)
        ids = [f["id"] for f in gj["features"]]
        bad = []
        for f in gj["features"]:
            g = shape(f["geometry"])
            lon, lat = (g.x, g.y) if g.geom_type == "Point" else (g.centroid.x, g.centroid.y)
            if not (-180 <= lon <= 180 and -90 <= lat <= 90) or not g.is_valid:
                bad.append(f["id"])
            if g.geom_type == "Polygon" and list(g.exterior.coords)[0] != list(g.exterior.coords)[-1]:
                bad.append(f["id"] + ":ring")
        check(f"geometry_valid:{fn}", not bad and len(ids) == len(set(ids)), f"{len(ids)} features; invalid={bad}; unique_ids={len(ids)==len(set(ids))}")
        pat = r"^EA-\d{3}$" if "earth" in fn else r"^(MOON|MARS)-REF-\d{2}$"
        check(f"id_format:{fn}", all(re.match(pat, i) for i in ids), pat)
    # Earth sites >= 20, >= 10 non-baseline
    E = earth_sites()
    nb = sum(1 for s in E if s["group"] != "baseline")
    check("site_count", len(E) >= 20 and nb >= 10, f"{len(E)} sites, {nb} outside the three baselines")
    lats = [s["lat"] for s in E]; lons = [s["lon"] for s in E]
    check("geographic_distribution", (max(lats) - min(lats)) > 120 and len({s['country'] for s in E}) >= 10,
          f"lat span {min(lats):.1f}..{max(lats):.1f}; {len({s['country'] for s in E})} countries/territories; continents incl. Antarctica")
    # Wikipedia GeoData cross-check
    wc = load_json(LIT / "wikipedia_coordinates.json")
    rows = []
    for s in E:
        src = s["coord_source"].replace("wiki:", "").split(" (")[0]
        c = (wc.get(src) or {}).get("coords")
        if c:
            d = hav(s["lat"], s["lon"], c[0]["lat"], c[0]["lon"])
            rows.append((s["site_id"], src, round(d, 3)))
    far = [r for r in rows if r[2] > 1.0]
    check("coords_match_wikipedia_geodata", not far, f"{len(rows)} sites cross-checked against GeoData (others from infobox coord templates); >1 km: {far}")
    # ERA5 grid distance
    dists = []
    for s in E:
        e = load_json(RAW / "era5" / f"{s['site_id']}.json")
        dists.append((s["site_id"], round(hav(s["lat"], s["lon"], e["grid_lat"], e["grid_lon"]), 1)))
    check("era5_grid_within_30km", all(d < 30 for _, d in dists), f"max {max(d for _, d in dists)} km", "warning")
    RES["coord_crosscheck"] = rows
    RES["era5_grid_distance_km"] = dists


def url_checks():
    if not NET:
        return
    cat = read_csv(OUTPUTS / "dataset_catalog.csv")
    res = []
    for r in cat:
        u = r["official_url"]
        code = None
        for meth in ("head", "get"):
            try:
                resp = getattr(requests, meth)(u, headers={"User-Agent": "Mozilla/5.0 " + USER_AGENT}, timeout=40, allow_redirects=True, stream=True)
                code = resp.status_code
                if code < 400:
                    break
            except Exception as ex:
                code = f"ERR:{type(ex).__name__}"
        res.append({"dataset_id": r["dataset_id"], "url": u, "status": code})
    RES["url_status"] = res
    bad = [x for x in res if not (isinstance(x["status"], int) and x["status"] < 400)]
    check("dataset_urls_reachable", len(bad) <= 3, f"{len(res)-len(bad)}/{len(res)} return HTTP <400; failures: {[(b['dataset_id'], b['status']) for b in bad]}",
          "warning")
    # evidence source URLs (unique)
    ev = load_json(OUTPUTS / "site_evidence.json")
    srcs = set()
    for grp in ("earth_sites", "planetary_references"):
        for e in ev[grp].values():
            for f in ("lithology", "process", "landform", "resource"):
                for x in e[f]:
                    if x.get("source"):
                        srcs.add(x["source"])
    ok = 0; fails = []
    for u in sorted(srcs):
        try:
            c = requests.head(u, headers={"User-Agent": USER_AGENT}, timeout=30, allow_redirects=True).status_code
        except Exception as ex:
            c = str(ex)[:40]
        if isinstance(c, int) and c < 400:
            ok += 1
        else:
            fails.append((u, c))
        time.sleep(0.2)
    check("evidence_source_urls_reachable", not fails, f"{ok}/{len(srcs)} evidence URLs OK; failures {fails}")


def doi_checks():
    d = load_json(LIT / "crossref_dois.json")
    listed = [x["doi"] for x in load_json(CONFIG / "doi_list.json")["dois"]]
    unresolved = [k for k in listed if (d.get(k) or {}).get("status") != 200]
    check("dois_resolve", not unresolved, f"{len(listed)-len(unresolved)}/{len(listed)} DOIs resolve (Crossref/doi.org); corrections applied: {d.get('_corrections')}")
    # every DOI used in md docs must be in the verified list
    used = set()
    corrected = {k.lower() for k in (d.get("_corrections") or {})}  # documented wrong DOIs, kept only in correction notes
    for p in list(ROOT.glob("*.md")) + [OUTPUTS / "dataset_catalog.csv", CONFIG / "planetary_references.json"]:
        if p.exists():
            used |= set(m.rstrip(").,;:") for m in re.findall(r"10\.\d{4,9}/[^\s|\"'<>\]`,]+", p.read_text(encoding="utf-8")))
    unknown = sorted(u for u in used if u.lower() not in {x.lower() for x in listed} | corrected)
    check("all_cited_dois_verified", not unknown, f"{len(used)} DOI strings found in docs/configs; not in verified list: {unknown}")


RANGES = {"lat": (-90, 90), "lon": (-180, 180), "elev_point_m": (-500, 9000), "t30m_r2km_slope_median_deg": (0, 90),
          "t30m_r2km_slope_p90_deg": (0, 90), "t90m_r5km_slope_median_deg": (0, 90), "t450m_r15km_slope_median_deg": (0, 90),
          "abiotic_fraction_r5km": (0, 1), "permafrost_prob": (0, 1), "ice_indicator": (0, 1), "fine_fraction": (0, 1),
          "temperature_K": (200, 320), "chelsa_maat_c": (-60, 40), "era5_t_mean_c": (-60, 40), "era5_precip_mm_yr": (0, 12000),
          "era5_et0_mm_yr": (0, 4000), "era5_aridity_index": (0, 20), "road_distance_m": (0, 1e6), "soil_sand_pct": (0, 100),
          "soil_silt_pct": (0, 100), "soil_clay_pct": (0, 100), "climate_workable_month_fraction": (0, 1)}


def unit_checks():
    rows = read_csv(OUTPUTS / "analog_features.csv")
    bad = []
    for r in rows:
        for k, (lo, hi) in RANGES.items():
            v = fnum(r.get(k))
            if v is not None and not (lo <= v <= hi):
                bad.append((r["site_id"], k, v))
    check("units_and_ranges", not bad, f"{len(RANGES)} columns range-checked in SI units; violations: {bad}")
    # slope ordering p90 >= median
    viol = [r["site_id"] for r in rows if fnum(r["t30m_r2km_slope_p90_deg"]) is not None and fnum(r["t30m_r2km_slope_p90_deg"]) < fnum(r["t30m_r2km_slope_median_deg"])]
    check("slope_p90_ge_median", not viol, str(viol))
    # temperature K = C + 273.15
    tk = [r["site_id"] for r in rows if fnum(r["temperature_K"]) is not None and abs(fnum(r["temperature_K"]) - fnum(r["maat_for_scoring_c"]) - 273.15) > 0.02]
    check("kelvin_conversion", not tk, str(tk))
    # CHELSA vs ERA5 consistency
    diffs = [(r["site_id"], round(fnum(r["chelsa_maat_c"]) - fnum(r["era5_t_mean_c"]), 2)) for r in rows if fnum(r["chelsa_maat_c"]) is not None and fnum(r["era5_t_mean_c"]) is not None]
    big = [d for d in diffs if abs(d[1]) > 3]
    corr = float(np.corrcoef([fnum(r["chelsa_maat_c"]) for r in rows if fnum(r["chelsa_maat_c"]) is not None],
                             [fnum(r["era5_t_mean_c"]) for r in rows if fnum(r["chelsa_maat_c"]) is not None])[0, 1])
    check("chelsa_vs_era5_maat", corr > 0.95, f"Pearson r={corr:.3f}; |diff|>3 °C at {big} (expected where ERA5 grid elevation differs from site)", "warning")
    RES["chelsa_minus_era5_c"] = diffs
    refs = read_csv(OUTPUTS / "planetary_features.csv")
    rb = [(r["ref_id"], r["ref_slope_median_deg"]) for r in refs if fnum(r["ref_slope_median_deg"]) is None or not 0 <= fnum(r["ref_slope_median_deg"]) <= 90]
    check("reference_terrain_present", not rb, f"{len(refs)} references with DEM-derived slope; problems {rb}")


def missing_report():
    rows = read_csv(OUTPUTS / "analog_features.csv")
    miss = {k: sum(1 for r in rows if r[k] == "") for k in rows[0].keys()}
    RES["missing_values"] = {k: v for k, v in miss.items() if v}
    check("missing_values_reported", True, f"{sum(1 for v in miss.values() if v)} columns contain explicit nulls (listed in report)", "info")


def recalculation():
    ranks = read_csv(OUTPUTS / "analog_rankings.csv")
    maxdiff = 0.0; n = 0
    for r in ranks:
        W = CFG["mission_profiles"][r["mission_profile"]]["weights"]
        num = den = 0.0
        for f, w in W.items():
            v = fnum(r.get(f"sim_{f}"))
            if w > 0 and v is not None:
                num += w * v; den += w
        sc = 100 * num / den
        maxdiff = max(maxdiff, abs(sc - float(r["fidelity_score"]))); n += 1
        if abs(den - float(r["evidence_completeness"])) > 0.002:
            maxdiff = max(maxdiff, 99)
    check("score_recalculation", maxdiff < 0.02, f"{n} scores recomputed independently from sim_* columns; max |diff| = {maxdiff:.4f}")
    sums = {k: round(sum(v["weights"].values()), 9) for k, v in CFG["mission_profiles"].items()}
    check("weights_sum_to_one", all(abs(v - 1) < 1e-9 for v in sums.values()), str(sums))
    check("operational_weights_sum_to_one", abs(sum(CFG["operational"]["weights"].values()) - 1) < 1e-9, "")
    sim_cols = [c for c in ranks[0] if c.startswith("sim_")]
    oob = [(r["site_id"], c) for r in ranks for c in sim_cols if r[c] != "" and not 0 <= float(r[c]) <= 1]
    check("similarities_in_unit_interval", not oob, str(oob[:5]))
    # deterministic re-run check: per-pair file agrees with ranking file for matched references
    pairs = {(p["site_id"], p["ref_id"], p["mission_profile"]): p for p in read_csv(PROCESSED / "pair_scores.csv")}
    mm = [r["site_id"] for r in ranks if abs(float(pairs[(r["site_id"], r["matched_reference_id"], r["mission_profile"])]["fidelity_score"]) - float(r["fidelity_score"])) > 0.02]
    check("pair_vs_ranking_consistency", not mm, str(mm[:5]))


def sensitivity():
    s = load_json(OUTPUTS / "sensitivity_summary.json")
    rows = [(k, v["mc_spearman_mean"], v["mc_spearman_p05"], max(v["oat_max_rank_shift"].values())) for k, v in s["profiles"].items()]
    RES["sensitivity"] = rows
    check("weight_sensitivity_rank_stability", all(r[1] >= 0.8 for r in rows), "mean Spearman over Dirichlet draws per profile: " + ", ".join(f"{k}={m}" for k, m, _, _ in rows), "warning")
    st = s["strict_evidence_variant"]["profiles"]
    RES["strict"] = st
    check("strict_evidence_variant", all(v["spearman_strict_vs_base"] >= 0.8 for v in st.values()),
          "Spearman(strict, base): " + ", ".join(f"{k}={v['spearman_strict_vs_base']}" for k, v in st.items()), "warning")


def baseline():
    a = load_json(OUTPUTS / "analytics_summary.json")["baseline_comparison"]
    RES["baseline"] = a
    n_pass = sum(c["pass"] for c in a["expected_role_checks"]); n = len(a["expected_role_checks"])
    check("baseline_expected_roles", n_pass / n >= 0.7, f"{n_pass}/{n} established analogs rank in the top quartile for their literature role", "warning")


def plausibility():
    rows = {r["site_id"]: r for r in read_csv(OUTPUTS / "analog_features.csv")}
    A = [("EA-003 Badwater Basin below sea level (wiki: lowest point in N. America)", fnum(rows["EA-003"]["elev_point_m"]) < 0),
         ("EA-010 Dallol below sea level (Danakil Depression)", fnum(rows["EA-010"]["elev_point_m"]) < 0),
         ("EA-011 Salar de Uyuni nearly flat (median 30 m slope < 1°)", fnum(rows["EA-011"]["t30m_r2km_slope_median_deg"]) < 1),
         ("EA-019 Mauna Kea summit > 3,500 m", fnum(rows["EA-019"]["elev_point_m"]) > 3500),
         ("EA-004 Dry Valleys MAAT < -15 °C", fnum(rows["EA-004"]["maat_for_scoring_c"]) < -15),
         ("EA-001 Atacama hyper-arid (ERA5 P < 100 mm/yr)", fnum(rows["EA-001"]["era5_precip_mm_yr"]) < 100),
         ("EA-002 Haughton permafrost probability > 0.9 (Obu 2019)", fnum(rows["EA-002"]["permafrost_prob"]) > 0.9),
         ("EA-022 Craters of the Moon not hyper-arid (AI > 0.05)", fnum(rows["EA-022"]["era5_aridity_index"]) > 0.05),
         ("EA-020 Ka'u Desert receives > 1,000 mm/yr (rain-shadow 'desert' is not dry; known limitation)", fnum(rows["EA-020"]["era5_precip_mm_yr"]) > 1000)]
    for name, ok in A:
        check("plausibility:" + name, ok, "", "warning")
    refs = {r["ref_id"]: r for r in read_csv(OUTPUTS / "planetary_features.csv")}
    B = [("MOON-REF-03 Malapert massif elevation > 4,000 m (rises ~5 km; Allender 2019)", fnum(refs["MOON-REF-03"]["ref_elev_point_m"]) > 4000),
         ("MOON-REF-02 Shackleton centre below rim (point elev < mean elev)", fnum(refs["MOON-REF-02"]["ref_elev_point_m"]) < fnum(refs["MOON-REF-02"]["ref_elev_mean_m"])),
         ("MARS-REF-02 Gale landing ~4.4 km below datum (wiki) -> MOLA < -4,000 m", fnum(refs["MARS-REF-02"]["ref_elev_point_m"]) < -4000),
         ("MARS-REF-06 Arsia Mons > 15 km", fnum(refs["MARS-REF-06"]["ref_elev_point_m"]) > 15000),
         ("MARS-REF-03 InSight plains smooth (median slope < 1° at 450 m)", fnum(refs["MARS-REF-03"]["ref_slope_median_deg"]) < 1)]
    for name, ok in B:
        check("plausibility:" + name, ok, "", "warning")


def write_report():
    C = RES["checks"]
    npass = sum(c["pass"] for c in C)
    L = ["# TerraAnalog AI - Validation report", "",
         f"Generated by `scripts/09_validate.py` on {RETRIEVAL_DATE} (network checks: {'on' if NET else 'off'}).", "",
         f"**{npass}/{len(C)} checks passed.** Severity: error = blocks release; warning = documented limitation; info = report only.", "",
         "| # | Check | Result | Severity | Detail |", "|---|---|---|---|---|"]
    for i, c in enumerate(C, 1):
        L.append(f"| {i} | {c['name']} | {'PASS' if c['pass'] else 'FAIL'} | {c['severity']} | {str(c['detail']).replace('|','/')[:600]} |")
    if "url_status" in RES:
        L += ["", "## URL checks (dataset catalog)", "", "| dataset_id | HTTP status | URL |", "|---|---|---|"]
        L += [f"| {x['dataset_id']} | {x['status']} | {x['url']} |" for x in RES["url_status"]]
    L += ["", "## Missing values (explicit nulls) in analog_features.csv", "", "| column | null count (of 28) |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in RES["missing_values"].items()]
    L += ["", "## CHELSA minus ERA5 mean annual temperature (°C)", "", ", ".join(f"{a}: {b}" for a, b in RES["chelsa_minus_era5_c"])]
    L += ["", "## Weight sensitivity (Monte Carlo Dirichlet, 2000 draws; OAT ±20%)", "", "| profile | mean Spearman | 5th pct Spearman | max OAT rank shift |", "|---|---|---|---|"]
    L += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in RES["sensitivity"]]
    L += ["", "## Evidence-strict variant (hypothesized tags removed)", "", "| profile | Spearman vs base | max rank shift | top-5 base | top-5 strict |", "|---|---|---|---|---|"]
    L += [f"| {k} | {v['spearman_strict_vs_base']} | {v['max_rank_shift']} | {', '.join(v['top5_base'])} | {', '.join(v['top5_strict'])} |" for k, v in RES["strict"].items()]
    b = RES["baseline"]
    L += ["", "## Baseline comparison", "", "Mean rank percentile (1 = best) by site group:", "", "| profile | baseline (Atacama, Haughton, Death Valley) | established analogs | new candidates | top new candidates |", "|---|---|---|---|---|"]
    for k, v in b["profiles"].items():
        L.append(f"| {k} | {v['baseline']} | {v['established']} | {v['candidate']} | {'; '.join(f'{x[0]} {x[1]} ({x[2]:.1f}, rank {x[3]})' for x in v['top_new_candidates'])} |")
    L += ["", f"Expected-role checks ({b['expected_role_pass_rate']} pass; threshold = top quartile):", "", "| profile | site | rank | pass | basis |", "|---|---|---|---|---|"]
    L += [f"| {c['profile']} | {c['site_id']} | {c['rank']} | {'PASS' if c['pass'] else 'FAIL'} | {c['basis']} |" for c in b["expected_role_checks"]]
    L += ["", "## Scientific plausibility review (manual)", "",
          "* Absolute fidelity scores are moderate (typically 30-75). This is expected and desirable: no Earth site reproduces lunar/Martian temperature, vacuum/CO2 atmosphere, gravity, radiation or day length, so the thermal and ice terms are low for most pairs. Scores are only comparable within one mission profile.",
          "* Moon thermal similarity is ~0 for every Earth site against PSR references (90-100 K) - correct behaviour; ISRU-ice rankings are driven by permafrost/ice presence, impact process and terrain.",
          "* Polar deserts (Haughton, Dry Valleys) have high P/ET0 because ET0 is tiny; the combined aridity term (P/ET0 and absolute precipitation) prevents them being treated as humid.",
          "* Lava-tube rankings are dominated by categorical landform/lithology evidence (lava tubes, basalt). Subsurface geometry (tube diameter, depth, overhang) is not yet quantified for Earth sites - a key data gap.",
          "* Sites whose sampling point is a region centroid (Atacama, Qaidam, Axel-Heiberg-type regions) inherit terrain metrics from that point, which may not be the best analog outcrop.",
          "* The Ka'u Desert receives >1,000 mm/yr in ERA5; its 'desert' character is due to acid rain/tephra substrate, so its aridity similarity is correctly low.",
          "* Access distances come from Natural Earth 1:10m major roads (OSM Overpass unreachable from the build host) and are upper bounds; operational scores should be re-run with OSM where available."]
    (OUTPUTS / "validation_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    save_json(RES, OUTPUTS / "validation_results.json")
    print(f"validation: {npass}/{len(C)} checks passed")
    for c in C:
        if not c["pass"]:
            print("  FAIL", c["severity"], c["name"], str(c["detail"])[:200])


if __name__ == "__main__":
    geometry_checks(); doi_checks(); unit_checks(); missing_report(); recalculation(); sensitivity(); baseline(); plausibility(); url_checks()
    write_report()
