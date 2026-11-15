"""Step 5 - MCDA similarity engine, operational suitability and sensitivity analysis.

Outputs:
  outputs/analog_rankings.csv          one row per (Earth site, mission profile)
  data/processed/pair_scores.csv       every (site, reference, profile) score with per-feature similarities
  outputs/sensitivity_summary.json     Monte Carlo (Dirichlet) + one-at-a-time + leave-one-feature-out results
Run:  python scripts/05_score.py
"""
import csv
import numpy as np
from common import *
from similarity import *

CFG = scoring_config()
EQ = CFG["tag_equivalences"]
FEAT = CFG["features"]
PC = CFG["provenance_confidence"]


def tagset(row, f):
    v = row.get(f"{f}_tags") or ""
    return [t for t in v.split(";") if t]


def tag_conf(evidence_list):
    if not evidence_list:
        return 0.0
    return sum(PC[e["provenance"]] for e in evidence_list) / len(evidence_list)


STRICT = False  # when True, categorical tags with provenance 'hypothesized' are ignored (evidence-strict variant)


def strict_tags(row, f, ev):
    if not STRICT:
        return tagset(row, f)
    ok = {x["tag"] for x in ev[f] if x["provenance"] != "hypothesized"}
    return [t for t in tagset(row, f) if t in ok]


def pair_similarities(e, r, ev_e, ev_r):
    body = r["body"]
    base = FEAT["slope"]["baseline"][body]
    sims, conf = {}, {}
    for f in ("lithology", "process", "landform", "resource"):
        sims[f] = jaccard(strict_tags(e, f, ev_e), strict_tags(r, f, ev_r), EQ)
        conf[f] = min(tag_conf(ev_e[f]), tag_conf(ev_r[f]))
    sims["slope"] = slope_sim(e.get(f"{base}_slope_median_deg"), e.get(f"{base}_slope_p90_deg"),
                              r.get("ref_slope_median_deg"), r.get("ref_slope_p90_deg"),
                              FEAT["slope"]["sigma_median_deg"], FEAT["slope"]["sigma_p90_deg"])
    conf["slope"] = PC["derived"]
    sims["ruggedness"] = log_ratio(e.get(f"{base}_tri_median_m"), r.get("ref_tri_median_m"), FEAT["ruggedness"]["scale_ln"])
    conf["ruggedness"] = PC["derived"]
    sims["thermal"] = gaussian(e.get("temperature_K"), r.get("temperature_K"), FEAT["thermal"]["sigma_K"])
    conf["thermal"] = min(PC["modeled"], PC.get(r.get("temperature_provenance") or "unavailable", 0))
    A = FEAT["aridity"]
    sims["aridity"] = aridity_combined(e.get("era5_aridity_index"), e.get("era5_precip_mm_yr"), A["threshold"], A["decay"],
                                       A["precip_threshold_mm"], A["precip_decay_mm"])
    conf["aridity"] = PC["modeled"]
    sims["ice"] = agreement(e.get("ice_indicator"), r.get("ice_indicator"))
    conf["ice"] = PC["modeled"] * (1.0 if e.get("permafrost_source") == "Obu2019_PERPROB" else 0.6)
    sims["abiotic_surface"] = e.get("abiotic_fraction_r5km")
    conf["abiotic_surface"] = PC["derived"]
    sims["dust_sediment"] = gaussian(e.get("fine_fraction"), r.get("fine_fraction"), FEAT["dust_sediment"]["sigma"])
    conf["dust_sediment"] = min(PC["modeled"], PC["derived"])
    for f in FEATURES:
        if sims.get(f) is None:
            conf[f] = 0.0
    return sims, conf


def score(sims, conf, weights):
    num = den = cw = 0.0
    total = sum(weights.values())
    for f, w in weights.items():
        if w <= 0:
            continue
        s = sims.get(f)
        if s is None:
            continue
        num += w * s; den += w; cw += w * conf[f]
    if den == 0:
        return None, 0.0, 0.0
    return 100.0 * num / den, den / total, cw / den


def operational(e):
    o = CFG["operational"]
    comp = {}
    d = e.get("road_distance_m")
    if d is not None:
        comp["access"] = float(np.exp(-d / o["access"]["scale_m"]))
    elif e.get("road_distance_censored_gt_m"):
        comp["access"] = float(np.exp(-e["road_distance_censored_gt_m"] / o["access"]["scale_m"]))
    else:
        comp["access"] = None
    comp["trafficability"] = e.get("t30m_r2km_slope_frac_lt15")
    comp["climate_workability"] = e.get("climate_workable_month_fraction")
    comp["regulatory"] = o["regulatory"].get(e.get("regulatory_class"))
    comp["infrastructure"] = o["infrastructure"].get(e.get("infrastructure_class"))
    num = den = 0.0
    for k, w in o["weights"].items():
        if comp.get(k) is not None:
            num += w * comp[k]; den += w
    return (100 * num / den if den else None), den, comp


def rank_desc(v):
    v = np.where(np.isnan(v), -np.inf, v)
    order = np.argsort(-v, kind="stable")
    r = np.empty(len(v), int); r[order] = np.arange(1, len(v) + 1)
    return r


def spearman(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    return float(np.corrcoef(a, b)[0, 1])


def strict_comparison(E, R, ev):
    """Re-rank every profile using only literature-supported tags; report rank agreement with the base run."""
    global STRICT
    out = {}
    for pname, prof in CFG["mission_profiles"].items():
        res = {}
        for mode in (False, True):
            STRICT = mode
            best = []
            for e in E:
                sc = [score(*pair_similarities(e, R[rid], ev["earth_sites"][e["site_id"]], ev["planetary_references"][rid]), prof["weights"])[0] for rid in prof["references"]]
                sc = [x for x in sc if x is not None]
                best.append(max(sc) if sc else np.nan)
            res[mode] = rank_desc(np.array(best, float))
        STRICT = False
        ids = np.array([e["site_id"] for e in E])
        out[pname] = {"spearman_strict_vs_base": clean(spearman(res[True], res[False]), 3),
                      "top5_base": list(ids[np.argsort(res[False])[:5]]), "top5_strict": list(ids[np.argsort(res[True])[:5]]),
                      "max_rank_shift": int(np.max(np.abs(res[True] - res[False])))}
    return out


def main():
    feats = load_json(PROCESSED / "features.json")
    ev = load_json(OUTPUTS / "site_evidence.json")
    E, R = feats["earth"], {r["ref_id"]: r for r in feats["references"]}
    sens_cfg = CFG["sensitivity"]
    rng = np.random.default_rng(sens_cfg["seed"])
    pair_rows, rank_rows, sens = [], [], {"method": {
        "monte_carlo": f"{sens_cfg['n_draws']} Dirichlet draws per profile, alpha = {sens_cfg['dirichlet_concentration']} * w (features with w>0)",
        "oat": f"each weight x(1 +/- {sens_cfg['oat_perturbation']}), renormalised to 1",
        "lofo": "leave-one-feature-out (weight set to 0, renormalised)"}, "profiles": {}}
    ops = {e["site_id"]: operational(e) for e in E}
    for pname, prof in CFG["mission_profiles"].items():
        W = prof["weights"]
        fnames = [f for f, w in W.items() if w > 0]
        w0 = np.array([W[f] for f in fnames])
        # similarity tensors: refs x sites x features
        S = np.full((len(prof["references"]), len(E), len(fnames)), np.nan)
        Cf = np.zeros_like(S)
        for i, rid in enumerate(prof["references"]):
            r = R[rid]
            for j, e in enumerate(E):
                sims, conf = pair_similarities(e, r, ev["earth_sites"][e["site_id"]], ev["planetary_references"][rid])
                sc, comp, cfd = score(sims, conf, W)
                for k, f in enumerate(fnames):
                    S[i, j, k] = np.nan if sims.get(f) is None else sims[f]
                    Cf[i, j, k] = conf[f]
                pair_rows.append({"site_id": e["site_id"], "ref_id": rid, "mission_profile": pname, "body": prof["body"],
                                  "fidelity_score": clean(sc, 2), "evidence_completeness": clean(comp, 3), "confidence": clean(cfd, 3),
                                  **{f"sim_{f}": clean(sims.get(f), 4) for f in FEATURES}})

        def profile_scores(w):
            avail = ~np.isnan(S)
            num = np.nansum(S * w, axis=2)
            den = np.sum(avail * w, axis=2)
            sc = np.where(den > 0, 100 * num / np.where(den > 0, den, 1), np.nan)
            best = np.nanmax(sc, axis=0)
            arg = np.nanargmax(np.where(np.isnan(sc), -1, sc), axis=0)
            return best, arg, den / w.sum()

        base, arg, compl = profile_scores(w0)
        base_rank = rank_desc(base)
        # Monte Carlo weight perturbation
        alpha = sens_cfg["dirichlet_concentration"] * w0
        draws = rng.dirichlet(alpha, sens_cfg["n_draws"])
        ranks = np.zeros((len(draws), len(E)), int); scores = np.zeros((len(draws), len(E)))
        rhos = []
        for d, w in enumerate(draws):
            sc, _, _ = profile_scores(w)
            scores[d] = sc; ranks[d] = rank_desc(sc); rhos.append(spearman(ranks[d], base_rank))
        topk = sens_cfg["top_k"]
        # OAT and LOFO
        oat, lofo = {}, {}
        for k, f in enumerate(fnames):
            worst = 0
            for sgn in (-1, 1):
                w = w0.copy(); w[k] *= 1 + sgn * sens_cfg["oat_perturbation"]; w /= w.sum()
                sc, _, _ = profile_scores(w); worst = max(worst, int(np.max(np.abs(rank_desc(sc) - base_rank))))
            oat[f] = worst
            w = w0.copy(); w[k] = 0
            if w.sum() > 0:
                w /= w.sum(); sc, _, _ = profile_scores(w); rr = rank_desc(sc)
                lofo[f] = {"spearman_vs_base": clean(spearman(rr, base_rank), 3),
                           "top5_changed": sorted(set(np.array([e['site_id'] for e in E])[base_rank <= topk]) ^ set(np.array([e['site_id'] for e in E])[rr <= topk]))}
        sens["profiles"][pname] = {"mc_spearman_mean": clean(np.mean(rhos), 3), "mc_spearman_p05": clean(np.percentile(rhos, 5), 3),
                                   "oat_max_rank_shift": oat, "lofo": lofo,
                                   "top5_base": [E[j]["site_id"] for j in np.argsort(base_rank)[:topk]]}
        for j, e in enumerate(E):
            rid = prof["references"][arg[j]]
            i = arg[j]
            fw = np.array([W[f] for f in fnames])
            av = ~np.isnan(S[i, j]); cfd = float(np.sum(fw[av] * Cf[i, j][av]) / np.sum(fw[av])) if av.any() else 0.0
            opv, opcomp, _ = ops[e["site_id"]]
            rank_rows.append({
                "site_id": e["site_id"], "name": e["name"], "group": e["group"], "body": prof["body"], "mission_profile": pname,
                "matched_reference_id": rid, "fidelity_score": clean(base[j], 2), "fidelity_rank": int(base_rank[j]),
                "evidence_completeness": clean(compl[i, j], 3), "confidence": clean(cfd, 3),
                "operational_score": clean(opv, 2), "operational_completeness": clean(opcomp, 3),
                "mc_score_p05": clean(np.percentile(scores[:, j], 5), 2), "mc_score_p95": clean(np.percentile(scores[:, j], 95), 2),
                "mc_rank_p05": int(np.percentile(ranks[:, j], 5)), "mc_rank_p95": int(np.percentile(ranks[:, j], 95)),
                "mc_top5_probability": clean(np.mean(ranks[:, j] <= topk), 3),
                **{f"sim_{f}": (clean(S[i, j, fnames.index(f)], 4) if f in fnames else None) for f in FEATURES}})
    # write
    for rows, p in ((rank_rows, OUTPUTS / "analog_rankings.csv"), (pair_rows, PROCESSED / "pair_scores.csv")):
        rows.sort(key=lambda r: (r["mission_profile"], r.get("fidelity_rank", 0), r.get("ref_id", "")))
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader()
            for r in rows:
                w.writerow({k: ("" if v is None else v) for k, v in r.items()})
    sens["operational_components"] = {sid: {k: clean(v, 3) for k, v in o[2].items()} for sid, o in ops.items()}
    sens["strict_evidence_variant"] = {"method": "categorical tags with provenance 'hypothesized' removed", "profiles": strict_comparison(E, R, ev)}
    save_json(sens, OUTPUTS / "sensitivity_summary.json")
    for pname in CFG["mission_profiles"]:
        top = [r for r in rank_rows if r["mission_profile"] == pname][:5]
        print(pname, " | ".join(f"{r['site_id']} {r['fidelity_score']} ({r['evidence_completeness']})" for r in top),
              "rho", sens["profiles"][pname]["mc_spearman_mean"])


if __name__ == "__main__":
    main()
