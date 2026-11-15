"""Sensitivity analysis and analog clustering (deterministic, dependency-free)."""
from __future__ import annotations

import math
from typing import Optional

from .loader import DataStore
from .models import PlanetaryReference
from .scoring import rank_sites

MULTIPLIERS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]


def sensitivity(store: DataStore, ref: PlanetaryReference, objective: str, criterion: Optional[str], top_n: int = 6,
                base_user: Optional[dict[str, float]] = None, features: Optional[list[str]] = None) -> dict:
    """Sweep one FEATURE's user multiplier (feature == criterion id for shared configs; for per-reference configs the
    multiplier applies to the selected reference's criterion for that feature)."""
    cfg = store.scoring
    assert cfg is not None
    base_user = base_user or {}
    baseline = rank_sites(store, ref, objective, base_user)
    base_rank = {r.site_id: r.rank for r in baseline}
    tracked = [r.site_id for r in baseline if r.rank is not None][:top_n]
    crits = [criterion] if criterion else (features if features is not None else [c.feature_id for c in cfg.criteria])

    sweeps = {}
    stability = []
    for cid in crits:
        series = []
        for m in MULTIPLIERS:
            uw = {**base_user, cid: base_user.get(cid, 1.0) * m}
            res = {r.site_id: r for r in rank_sites(store, ref, objective, uw)}
            series.append({"multiplier": m, **{sid: (res[sid].score if sid in res else None) for sid in tracked},
                           **{f"rank:{sid}": (res[sid].rank if sid in res else None) for sid in tracked}})
        sweeps[cid] = series
        # rank stability under +/-50% perturbation of this criterion's weight
        for m in (0.5, 1.5):
            uw = {**base_user, cid: base_user.get(cid, 1.0) * m}
            for r in rank_sites(store, ref, objective, uw):
                if r.site_id in tracked and r.rank is not None and base_rank.get(r.site_id):
                    stability.append({"criterion": cid, "multiplier": m, "site_id": r.site_id,
                                      "rank_shift": r.rank - base_rank[r.site_id]})
    max_shift: dict[str, int] = {}
    for s in stability:
        k = s["criterion"]
        max_shift[k] = max(max_shift.get(k, 0), abs(s["rank_shift"]))
    return {"ref_id": ref.ref_id, "objective": objective, "tracked_sites": tracked, "multipliers": MULTIPLIERS,
            "sweeps": sweeps, "max_rank_shift_by_criterion": max_shift, "stability": stability}


def _dist(a: dict[str, float], b: dict[str, float]) -> Optional[float]:
    shared = [k for k in a if k in b]
    if not shared:
        return None
    return math.sqrt(sum((a[k] - b[k]) ** 2 for k in shared) / len(shared))


def clusters(store: DataStore, k: int = 4, criteria: Optional[list] = None, iters: int = 25) -> dict:
    """Mask-aware k-means on feature vectors: distance uses only features present in both vectors, so missing
    values are never imputed. Deterministic farthest-point initialisation. `criteria` = Criterion objects to use
    (for per-reference configs: the selected reference's fidelity criteria); vectors are keyed by feature id."""
    cfg = store.scoring
    use = criteria if criteria is not None else (cfg.criteria if cfg else [])
    fmap = {c.id: c.feature_id for c in use}
    crit = list(dict.fromkeys(fmap.values()))
    vecs = {sid: {fmap[c]: fv.value for c, fv in store.features.get(sid, {}).items() if fv.value is not None and c in fmap}
            for sid in sorted(store.sites)}
    vecs = {s: v for s, v in vecs.items() if v}
    ids = list(vecs)
    if not ids:
        return {"k": 0, "clusters": [], "assignments": {}}
    k = max(1, min(k, len(ids)))
    centroids = [dict(vecs[ids[0]])]
    while len(centroids) < k:
        far = max(ids, key=lambda s: min((_dist(vecs[s], c) or 0.0) for c in centroids))
        centroids.append(dict(vecs[far]))
    assign: dict[str, int] = {}
    for _ in range(iters):
        new = {s: min(range(k), key=lambda j: (_dist(vecs[s], centroids[j]) if _dist(vecs[s], centroids[j]) is not None else 1e9)) for s in ids}
        for j in range(k):
            members = [vecs[s] for s in ids if new[s] == j]
            if not members:
                continue
            centroids[j] = {c: sum(m[c] for m in members if c in m) / n for c in crit
                            if (n := sum(1 for m in members if c in m))}
        if new == assign:
            break
        assign = new
    out = []
    for j in range(k):
        members = [s for s in ids if assign[s] == j]
        if not members:
            continue
        cen = {c: round(v, 2) for c, v in centroids[j].items()}
        top = sorted(cen.items(), key=lambda kv: -kv[1])[:3]
        types: dict[str, int] = {}
        for s in members:
            for t in store.sites[s].analog_types:
                types[t] = types.get(t, 0) + 1
        dominant = sorted(types.items(), key=lambda kv: (-kv[1], kv[0]))[:2]
        out.append({"cluster": j, "members": members, "centroid": cen, "defining_criteria": [t[0] for t in top],
                    "dominant_analog_types": [d[0] for d in dominant],
                    "label": " / ".join(d[0].replace("_", " ") for d in dominant) or f"cluster {j}"})
    return {"k": len(out), "clusters": out, "assignments": assign, "method": "mask-aware k-means (no imputation)"}
