"""Step 6 - exploratory analytics (unsupervised only; no labelled data -> no supervised ML claims).

  * PCA + k-means / Ward clustering of Earth sites on real numeric features -> analog classes
  * site x reference equal-weight similarity matrix; site x site similarity matrix
  * radar-chart data for the top sites per mission profile
  * baseline comparison (established analogs vs new candidates; expected-role checks)
  * data-gap table and recommended field measurements
  * figures: site map, PCA plot, radar charts, sensitivity rank intervals
Run:  python scripts/06_analytics.py
"""
import csv, json, math, requests
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score, adjusted_rand_score
from common import *
from similarity import FEATURES

CFG = scoring_config()
NUM = [("t90m_r5km_slope_median_deg", "slope_med_90m_deg", None), ("t90m_r5km_slope_p90_deg", "slope_p90_90m_deg", None),
       ("t90m_r5km_tri_median_m", "log_TRI_90m", "log"), ("t450m_r15km_relief_m", "log_relief_15km", "log"),
       ("temperature_K", "MAAT_K", None), ("era5_aridity_index", "log_aridity", "log"), ("ice_indicator", "ice_indicator", None),
       ("abiotic_fraction_r5km", "abiotic_fraction", None), ("era5_freeze_thaw_days_yr", "freeze_thaw_days", None),
       ("era5_diurnal_range_c", "diurnal_range_C", None)]
EXPECTED_ROLES = {
    "MARS_ISRU_ICE": ["EA-004", "EA-002"],
    "MOON_LAVA_TUBE": ["EA-009", "EA-016", "EA-021", "EA-022"],
    "MARS_LAVA_TUBE": ["EA-009", "EA-016", "EA-021", "EA-022"],
    "MARS_ASTROBIO_SEDIMENTS": ["EA-001", "EA-026", "EA-018", "EA-010"],
    "MOON_FIELD_GEOLOGY": ["EA-024", "EA-023", "EA-025"],
}
EXPECTED_SOURCE = {
    "MARS_ISRU_ICE": "Dry Valleys permafrost drilling for Mars (wiki:McMurdo Dry Valleys); Haughton permafrost 'cold, wet Mars' analogue (wiki:Haughton impact crater)",
    "MOON_LAVA_TUBE": "Lava-tube analog literature (Sauro et al. 2020, doi:10.1016/j.earscirev.2020.103288); sites contain mapped lava tubes (wiki)",
    "MARS_LAVA_TUBE": "as above",
    "MARS_ASTROBIO_SEDIMENTS": "Atacama Mars-like soils (Navarro-Gonzalez 2003); Rio Tinto Meridiani comparison (wiki); Qaidam Mars analogue (Xiao et al. 2017); Dallol polyextreme brines (wiki)",
    "MOON_FIELD_GEOLOGY": "Apollo/Artemis astronaut geology training at Meteor Crater, Sudbury, Mistastin (wiki)",
}
FIELD_MEASUREMENTS = {
    "thermal": "in-situ ground/rock surface temperature loggers (diurnal + seasonal), cave air temperature where applicable",
    "dust_sediment": "grain-size distribution (laser diffraction / sieving) of surface fines; dust lofting tests",
    "ice": "ice-table depth and ice content (probe, GPR, cores)",
    "lithology": "field spectroscopy (VNIR/SWIR), XRD on representative samples to confirm mapped lithology",
    "resource": "volatile/hydrated-mineral assays (TGA/EGA) for ISRU-relevant phases",
    "slope": "UAV photogrammetry DEM (<=0.5 m) to resolve rover-scale slopes",
    "ruggedness": "rock-abundance counts (rocks >0.2 m per m2) for hazard modelling",
    "abiotic_surface": "ground-truth vegetation/biological soil crust cover transects",
    "aridity": "on-site meteorological station (precipitation, RH, wind) for >=1 year",
}


def tr(v, kind):
    if v is None or v == "":
        return np.nan
    v = float(v)
    return math.log10(max(v, 1e-3)) if kind == "log" else v


def main():
    feats = load_json(PROCESSED / "features.json")
    E = feats["earth"]; R = feats["references"]
    ids = [e["site_id"] for e in E]
    X = np.array([[tr(e.get(k), kind) for k, _, kind in NUM] for e in E])
    n_missing = int(np.isnan(X).sum())
    med = np.nanmedian(X, axis=0)
    Xi = np.where(np.isnan(X), med, X)
    Z = StandardScaler().fit_transform(Xi)
    pca = PCA(n_components=min(5, Z.shape[1])).fit(Z)
    P = pca.transform(Z)
    sil = {}
    for k in range(2, 7):
        lab = KMeans(n_clusters=k, n_init=50, random_state=0).fit_predict(Z)
        sil[k] = float(silhouette_score(Z, lab))
    kbest = max(sil, key=sil.get)
    km = KMeans(n_clusters=kbest, n_init=50, random_state=0).fit(Z)
    ward = AgglomerativeClustering(n_clusters=kbest, linkage="ward").fit_predict(Z)
    ari = float(adjusted_rand_score(km.labels_, ward))
    # describe clusters by their standardized centroids
    names = [n for _, n, _ in NUM]
    clusters = {}
    for c in range(kbest):
        members = [ids[i] for i in range(len(ids)) if km.labels_[i] == c]
        cen = km.cluster_centers_[c]
        top = sorted(zip(names, cen), key=lambda t: -abs(t[1]))[:3]
        clusters[f"C{c+1}"] = {"members": members, "defining_features_z": {n: round(float(v), 2) for n, v in top}}
    analytics = {
        "note": "Unsupervised, exploratory. n=28 sites is small; clusters describe environmental similarity in the measured/modelled feature space only and are not validated analog classes.",
        "features_used": names, "imputed_missing_values": n_missing, "imputation": "column median (on transformed scale)",
        "pca_explained_variance_ratio": [round(float(v), 3) for v in pca.explained_variance_ratio_],
        "pca_loadings": {f"PC{i+1}": {n: round(float(v), 3) for n, v in zip(names, pca.components_[i])} for i in range(3)},
        "kmeans_silhouette_by_k": {str(k): round(v, 3) for k, v in sil.items()}, "k_selected": kbest,
        "kmeans_vs_ward_adjusted_rand_index": round(ari, 3), "clusters": clusters,
        "site_coordinates_pca": {ids[i]: {"PC1": round(float(P[i, 0]), 3), "PC2": round(float(P[i, 1]), 3), "cluster": f"C{km.labels_[i]+1}"} for i in range(len(ids))}}
    # ---- similarity matrices ----
    pairs = list(csv.DictReader(open(PROCESSED / "pair_scores.csv", encoding="utf-8")))
    refs = [r["ref_id"] for r in R]
    eq = {}
    for p in pairs:
        sims = [float(p[f"sim_{f}"]) for f in FEATURES if p[f"sim_{f}"] != ""]
        eq[(p["site_id"], p["ref_id"])] = 100 * sum(sims) / len(sims) if sims else None
    # include references that are not in any profile's ref list (all are; keep generic)
    with open(OUTPUTS / "similarity_matrix_site_x_reference.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["site_id"] + refs)
        for sid in ids:
            w.writerow([sid] + ["" if eq.get((sid, r)) is None else round(eq[(sid, r)], 2) for r in refs])
    Zn = Z / np.linalg.norm(Z, axis=1, keepdims=True)
    C = Zn @ Zn.T
    with open(OUTPUTS / "similarity_matrix_site_x_site.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["site_id"] + ids)
        for i, sid in enumerate(ids):
            w.writerow([sid] + [round(float(v), 3) for v in C[i]])
    # ---- radar data ----
    ranks = list(csv.DictReader(open(OUTPUTS / "analog_rankings.csv", encoding="utf-8")))
    radar = {"features": FEATURES, "note": "Per-feature similarity (0-1) to the matched reference; null = unavailable.", "profiles": {}}
    for pname in CFG["mission_profiles"]:
        rows = sorted([r for r in ranks if r["mission_profile"] == pname], key=lambda r: int(r["fidelity_rank"]))[:5]
        radar["profiles"][pname] = [{"site_id": r["site_id"], "name": r["name"], "matched_reference_id": r["matched_reference_id"],
                                     "fidelity_score": float(r["fidelity_score"]),
                                     "values": {f: (None if r[f"sim_{f}"] == "" else float(r[f"sim_{f}"])) for f in FEATURES}} for r in rows]
    save_json(radar, OUTPUTS / "radar_chart_data.json")
    # ---- baseline comparison ----
    groups = {e["site_id"]: e["group"] for e in E}
    base = {"groups": {"baseline": [i for i in ids if groups[i] == "baseline"], "established": [i for i in ids if groups[i] == "established"],
                       "candidate": [i for i in ids if groups[i] == "candidate"]}, "profiles": {}, "expected_role_checks": []}
    for pname in CFG["mission_profiles"]:
        rows = [r for r in ranks if r["mission_profile"] == pname]
        pct = {r["site_id"]: 1 - (int(r["fidelity_rank"]) - 1) / (len(rows) - 1) for r in rows}
        base["profiles"][pname] = {g: round(float(np.mean([pct[i] for i in base["groups"][g]])), 3) for g in ("baseline", "established", "candidate")}
        best_new = sorted([r for r in rows if groups[r["site_id"]] == "candidate"], key=lambda r: int(r["fidelity_rank"]))[:3]
        base["profiles"][pname]["top_new_candidates"] = [(r["site_id"], r["name"], float(r["fidelity_score"]), int(r["fidelity_rank"])) for r in best_new]
    q = math.ceil(len(ids) / 4)
    for pname, exp in EXPECTED_ROLES.items():
        rows = {r["site_id"]: int(r["fidelity_rank"]) for r in ranks if r["mission_profile"] == pname}
        for sid in exp:
            base["expected_role_checks"].append({"profile": pname, "site_id": sid, "rank": rows[sid], "top_quartile_threshold": q,
                                                 "pass": rows[sid] <= q, "basis": EXPECTED_SOURCE[pname]})
    npass = sum(c["pass"] for c in base["expected_role_checks"])
    base["expected_role_pass_rate"] = f"{npass}/{len(base['expected_role_checks'])}"
    analytics["baseline_comparison"] = base
    # ---- data gaps ----
    gaps = []
    for e in E:
        missing = []
        for col in ("temperature_K", "era5_aridity_index", "permafrost_prob", "fine_fraction", "abiotic_fraction_r5km", "road_distance_m",
                    "t90m_r5km_slope_median_deg", "t450m_r15km_slope_median_deg", "macrostrat_lith"):
            if e.get(col) in (None, ""):
                missing.append(col)
        hyp = []
        ev = load_json(OUTPUTS / "site_evidence.json")["earth_sites"][e["site_id"]]
        for f in ("lithology", "process", "landform", "resource"):
            hyp += [f"{f}:{x['tag']}" for x in ev[f] if x["provenance"] == "hypothesized"]
        rec = ["thermal", "dust_sediment", "lithology", "slope", "ruggedness"]
        if (e.get("ice_indicator") or 0) > 0.2:
            rec.insert(1, "ice")
        if "lava_tube_cave" in (e.get("landform_tags") or ""):
            rec.append("thermal")
        gaps.append({"site_id": e["site_id"], "name": e["name"], "missing_numeric": ";".join(missing), "hypothesized_tags": ";".join(hyp),
                     "permafrost_source": e.get("permafrost_source"), "data_confidence": e.get("data_confidence"),
                     "recommended_field_measurements": " | ".join(dict.fromkeys(FIELD_MEASUREMENTS[k] for k in rec))})
    with open(OUTPUTS / "data_gaps.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(gaps[0].keys())); w.writeheader(); w.writerows(gaps)
    save_json(analytics, OUTPUTS / "analytics_summary.json")
    figures(E, R, P, km.labels_, pca, ranks, radar)
    print("k =", kbest, "silhouette", round(sil[kbest], 3), "ARI", round(ari, 3), "| expected-role checks", base["expected_role_pass_rate"])


def land_polygons():
    p = RAW / "basemap" / "ne_110m_land.geojson"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            r = requests.get("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson", timeout=60)
            r.raise_for_status(); p.write_bytes(r.content)
        except Exception:
            return []
    polys = []
    for f in load_json(p)["features"]:
        g = f["geometry"]
        rings = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in rings:
            polys.append(np.array(poly[0]))
    return polys


def figures(E, R, P, labels, pca, ranks, radar):
    colors = {"baseline": "#d62728", "established": "#1f77b4", "candidate": "#2ca02c"}
    # site map
    fig, ax = plt.subplots(figsize=(14, 7.2))
    for poly in land_polygons():
        ax.fill(poly[:, 0], poly[:, 1], color="#e8e4da", lw=0.3, ec="#9a958a")
    for g, c in colors.items():
        xs = [e["lon"] for e in E if e["group"] == g]; ys = [e["lat"] for e in E if e["group"] == g]
        ax.scatter(xs, ys, s=46, c=c, edgecolor="k", lw=0.5, label=f"{g} ({len(xs)})", zorder=3)
    for e in E:
        ax.annotate(e["site_id"].replace("EA-0", ""), (e["lon"], e["lat"]), xytext=(3, 3), textcoords="offset points", fontsize=7, zorder=4)
    ax.set_xlim(-180, 180); ax.set_ylim(-90, 90); ax.set_aspect("equal")
    ax.set_xlabel("Longitude (°E, WGS84)"); ax.set_ylabel("Latitude (°N, WGS84)")
    ax.set_title("TerraAnalog AI - Earth analog candidate sites (n=%d); labels = EA-0xx" % len(E))
    ax.grid(alpha=0.3); ax.legend(loc="lower left", fontsize=9)
    fig.text(0.01, 0.01, "Basemap: Natural Earth 1:110m land (public domain). Points: sampling coordinates from site_evidence.json.", fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "site_map.png", dpi=150); fig.savefig(FIG / "site_map.svg"); plt.close(fig)
    # PCA
    fig, ax = plt.subplots(figsize=(9, 7))
    sc = ax.scatter(P[:, 0], P[:, 1], c=labels, cmap="tab10", s=60, edgecolor="k")
    for i, e in enumerate(E):
        ax.annotate(e["site_id"], (P[i, 0], P[i, 1]), xytext=(3, 3), textcoords="offset points", fontsize=7)
    ev = pca.explained_variance_ratio_
    ax.set_xlabel(f"PC1 ({ev[0]*100:.1f}% var)"); ax.set_ylabel(f"PC2 ({ev[1]*100:.1f}% var)")
    ax.set_title("PCA of standardized Earth-site features (colour = k-means cluster)\nexploratory; n=28")
    ax.grid(alpha=0.3); fig.tight_layout(); fig.savefig(FIG / "pca_clusters.png", dpi=150); fig.savefig(FIG / "pca_clusters.svg"); plt.close(fig)
    # radar charts: best 3 for each of two headline profiles per body
    for pname in ("MOON_ROVER_MOBILITY", "MOON_LAVA_TUBE", "MOON_ISRU_ICE", "MARS_ASTROBIO_SEDIMENTS", "MARS_ISRU_ICE", "MARS_LAVA_TUBE"):
        items = radar["profiles"][pname][:3]
        feats = [f for f in FEATURES if f in CFG["mission_profiles"][pname]["weights"] and CFG["mission_profiles"][pname]["weights"][f] > 0]
        ang = np.linspace(0, 2 * np.pi, len(feats), endpoint=False).tolist(); ang += ang[:1]
        fig = plt.figure(figsize=(7, 7)); ax = fig.add_subplot(111, polar=True)
        for it in items:
            vals = [it["values"][f] if it["values"][f] is not None else 0 for f in feats]; vals += vals[:1]
            ax.plot(ang, vals, lw=1.6, label=f"{it['site_id']} {it['name'][:28]} ({it['fidelity_score']:.1f})")
            ax.fill(ang, vals, alpha=0.08)
        ax.set_xticks(ang[:-1]); ax.set_xticklabels(feats, fontsize=8); ax.set_ylim(0, 1)
        ax.set_title(f"{pname}: per-feature similarity of top-3 sites\n(missing features plotted as 0; see radar_chart_data.json)", fontsize=10)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), fontsize=8)
        fig.tight_layout(); fig.savefig(FIG / f"radar_{pname}.png", dpi=130); fig.savefig(FIG / f"radar_{pname}.svg"); plt.close(fig)
    # sensitivity rank intervals for two profiles
    fig, axes = plt.subplots(1, 2, figsize=(13, 7))
    for ax, pname in zip(axes, ("MOON_ROVER_MOBILITY", "MARS_ASTROBIO_SEDIMENTS")):
        rows = sorted([r for r in ranks if r["mission_profile"] == pname], key=lambda r: int(r["fidelity_rank"]))
        y = np.arange(len(rows))
        ax.hlines(y, [int(r["mc_rank_p05"]) for r in rows], [int(r["mc_rank_p95"]) for r in rows], color="gray")
        ax.scatter([int(r["fidelity_rank"]) for r in rows], y, c="k", s=14, zorder=3)
        ax.set_yticks(y); ax.set_yticklabels([f"{r['site_id']} {r['name'][:22]}" for r in rows], fontsize=7); ax.invert_yaxis()
        ax.set_xlabel("rank (dot = base weights; bar = 5-95% over 2000 Dirichlet weight draws)"); ax.set_title(pname, fontsize=10)
        ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG / "sensitivity_rank_intervals.png", dpi=130); fig.savefig(FIG / "sensitivity_rank_intervals.svg"); plt.close(fig)


if __name__ == "__main__":
    main()
