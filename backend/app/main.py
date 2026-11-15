"""TerraAnalog AI — FastAPI data & scoring service."""
from __future__ import annotations

import csv
import io
import math
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from . import config
from .analysis import clusters, sensitivity
from .loader import DataStore, get_store
from .models import RecommendRequest
from .recommend import recommend
from .report import build_compare_pdf
from .scoring import ScoringError, effective_weights, parse_weights, rank_sites, score_site

VERSION = "1.0.0"
app = FastAPI(title="TerraAnalog AI API", version=VERSION,
              description="Earth analog site data, transparent scoring and recommendations for Moon & Mars mission testing.")
app.add_middleware(CORSMiddleware, allow_origins=config.cors_origins(), allow_methods=["GET", "POST"], allow_headers=["*"])

ID_RE = r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$"


@app.exception_handler(ScoringError)
async def _scoring_error(_, exc: ScoringError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# ---- helpers -------------------------------------------------------------------------
def _store() -> DataStore:
    return get_store()


def _need_scoring(st: DataStore) -> None:
    if st.scoring is None:
        raise HTTPException(503, detail="scoring_config.json is missing or invalid; scores unavailable. See /api/validation.")


def _ref(st: DataStore, ref_id: Optional[str], body: Optional[str] = None):
    if ref_id:
        r = st.references.get(ref_id)
        if r is None:
            raise HTTPException(404, detail=f"planetary reference '{ref_id}' not found")
        return r
    if body and st.scoring and st.scoring.default_reference.get(body) in st.references:
        return st.references[st.scoring.default_reference[body]]
    return None


def _objective(st: DataStore, objective: Optional[str]) -> str:
    _need_scoring(st)
    obj = objective or st.scoring.default_objective
    if obj not in {o.id for o in st.scoring.objectives}:
        raise HTTPException(422, detail=f"unknown objective '{obj}'")
    return obj


def _weights(st: DataStore, raw: Optional[str]) -> dict[str, float]:
    if not st.scoring:
        return {}
    valid = {c.id for c in st.scoring.criteria} | {c.feature_id for c in st.scoring.criteria}
    return parse_weights(raw, valid)


def _ref_context(st: DataStore, ref, ref_id: Optional[str], objective: Optional[str] = None) -> dict:
    """Explain which reference/criteria are in use: defaulted reference, per-reference criteria, objective/body mismatch."""
    out: dict = {"reference_defaulted": ref is not None and not ref_id, "notes": []}
    if ref is not None and not ref_id:
        out["notes"].append(f"No planetary reference selected; using the {ref.body.title()} default reference {ref.name} ({ref.ref_id}).")
    cfg = st.scoring
    if cfg and ref is not None:
        out["criteria_mode"] = "per_reference" if cfg.per_reference else "shared"
        if objective:
            o = next((x for x in cfg.objectives if x.id == objective), None)
            if o is not None and o.body_key and o.body_key != ref.body:
                out["notes"].append(f"Objective {o.label} is a {o.body_key.title()} mission profile but {ref.name} is a "
                                    f"{ref.body.title()} reference; its feature weights are applied here for exploration only.")
            if o is not None and o.published_references and ref.ref_id not in o.published_references:
                out["notes"].append(f"Published {o.label} scores exist for {', '.join(o.published_references)}; scores against "
                                    f"{ref.ref_id} are computed live with the same method.")
    return out


def _feature_label_map(st: DataStore) -> dict[str, str]:
    return {f["id"]: f["label"] for f in st.scoring.features()} if st.scoring else {}


def _fidelity_criteria(st: DataStore, ref) -> list:
    """Active criteria for a reference that can carry fidelity weight (excludes always-zero ones like operational)."""
    cfg = st.scoring
    return [c for c in cfg.active_criteria(ref.ref_id) if cfg.body_weights.get(ref.body, {}).get(c.id, 0) > 0]


def _site_summary(st: DataStore, sid: str) -> dict:
    s = st.sites[sid]
    d = s.model_dump()
    d["feature_count"] = sum(1 for fv in st.features.get(sid, {}).values() if fv.value is not None)
    return d


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    # Earth only (mean radius 6371.0088 km). Never used for Moon/Mars geometry.
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ---- endpoints -----------------------------------------------------------------------
@app.get("/api/health")
def health():
    st = _store()
    return {"status": "ok", "version": VERSION, "synthetic": st.is_synthetic, "sites": len(st.sites),
            "references": len(st.references), "errors": sum(1 for i in st.issues if i.level == "error")}


@app.get("/api/meta")
def meta():
    st = _store()
    cfg = st.scoring
    return {
        "data_status": st.data_status(),
        "criteria": [c.model_dump() for c in cfg.criteria] if cfg else [],
        "objectives": [o.model_dump() for o in cfg.objectives] if cfg else [],
        "default_objective": cfg.default_objective if cfg else None,
        "default_reference": cfg.default_reference if cfg else {},
        "body_weights": cfg.body_weights if cfg else {},
        "reference_multipliers": cfg.reference_multipliers if cfg else {},
        "min_completeness": cfg.min_completeness if cfg else None,
        "value_type_confidence": cfg.value_type_confidence if cfg else {},
        "non_replicable": cfg.non_replicable if cfg else {},
        "analog_types": cfg.analog_types if cfg else {},
        "scoring_meta": cfg.meta if cfg else {},
        "features": cfg.features() if cfg else [],
        "criteria_mode": ("per_reference" if cfg.per_reference else "shared") if cfg else None,
        "objective_bodies": {o.id: o.body_key for o in cfg.objectives} if cfg else {},
        "objective_published_references": {o.id: o.published_references for o in cfg.objectives} if cfg else {},
        "objective_feature_weights": _objective_feature_weights(st) if cfg else {},
        "body_feature_weights": _body_feature_weights(st) if cfg else {},
        "default_compare_ids": _default_compare_ids(st),
        "notice": (cfg.meta.get("notice") if cfg and isinstance(cfg.meta, dict) else None),
        "climates": sorted({s.climate for s in st.sites.values() if s.climate}),
        "countries": sorted({s.country for s in st.sites.values() if s.country}),
    }


def _default_ref(st: DataStore, body: str):
    cfg = st.scoring
    rid = cfg.default_reference.get(body) if cfg else None
    return st.references.get(rid) if rid else next((r for r in st.references.values() if r.body == body), None)


def _objective_feature_weights(st: DataStore) -> dict[str, dict[str, float]]:
    """Objective multipliers collapsed to features (read from the body's default reference for per-reference configs)."""
    cfg = st.scoring
    out = {}
    for o in cfg.objectives:
        ref = _default_ref(st, o.body_key or "moon") if cfg.per_reference else None
        crit = cfg.active_criteria(ref.ref_id if ref else None) if cfg.per_reference else cfg.criteria
        out[o.id] = {c.feature_id: o.multipliers[c.id] for c in crit if c.id in o.multipliers}
    return out


def _body_feature_weights(st: DataStore) -> dict[str, dict[str, float]]:
    cfg = st.scoring
    out = {}
    for body, w in cfg.body_weights.items():
        ref = _default_ref(st, body) if cfg.per_reference else None
        crit = cfg.active_criteria(ref.ref_id if ref else None) if cfg.per_reference else cfg.criteria
        out[body] = {c.feature_id: w.get(c.id, 0.0) for c in crit}
    return out


def _default_compare_ids(st: DataStore, n: int = 3) -> list[str]:
    cfg = st.scoring
    if not cfg or not st.sites:
        return sorted(st.sites)[:n]
    ref = _default_ref(st, "moon")
    if ref is None:
        return sorted(st.sites)[:n]
    try:
        return [r.site_id for r in rank_sites(st, ref, cfg.default_objective) if r.rank][:n]
    except ScoringError:
        return sorted(st.sites)[:n]


@app.get("/api/validation")
def validation():
    return _store().data_status()


@app.get("/api/sites")
def list_sites(
    body: Optional[str] = Query(None, pattern="^(moon|mars)$"),
    analog_type: Optional[str] = Query(None, max_length=64),
    climate: Optional[str] = Query(None, max_length=64),
    geology: Optional[str] = Query(None, max_length=64),
    objective: Optional[str] = Query(None, pattern=ID_RE, description="scoring objective"),
    mission_objective: Optional[str] = Query(None, pattern=ID_RE, description="filter: site supports this objective"),
    ref_id: Optional[str] = Query(None, pattern=ID_RE),
    min_confidence: float = Query(0.0, ge=0, le=1),
    min_score: float = Query(0.0, ge=0, le=100),
    q: Optional[str] = Query(None, max_length=100),
    near: Optional[str] = Query(None, pattern=r"^-?\d+(\.\d+)?,-?\d+(\.\d+)?$", description="lat,lon"),
    radius_km: float = Query(2000, gt=0, le=20040),
    include_insufficient: bool = True,
    sort: str = Query("score", pattern="^(score|name|confidence|completeness|lat|distance)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    weights: Optional[str] = Query(None, max_length=400),
):
    st = _store()
    ref = _ref(st, ref_id, body)
    if body and ref and ref.body != body:
        raise HTTPException(422, detail=f"ref_id '{ref.ref_id}' is a {ref.body} reference but body={body}")
    obj = _objective(st, objective) if st.scoring else None
    uw = _weights(st, weights)
    scores = {}
    if ref and st.scoring:
        scores = {r.site_id: r for r in rank_sites(st, ref, obj, uw, body_relevant_only=False)}
    elif (min_score > 0 or min_confidence > 0 or sort in ("score", "confidence", "completeness")) and not ref:
        if min_score > 0 or min_confidence > 0:
            raise HTTPException(422, detail="ref_id (or body) is required to filter by score/confidence")
    nlat = nlon = None
    if near:
        nlat, nlon = (float(x) for x in near.split(","))
        if not (-90 <= nlat <= 90 and -180 <= nlon <= 180):
            raise HTTPException(422, detail="near must be a valid Earth lat,lon")

    out = []
    for sid, s in st.sites.items():
        if body and body not in s.target_bodies:
            continue
        if analog_type and analog_type not in s.analog_types:
            continue
        if climate and climate.lower() not in s.climate.lower():
            continue
        if geology and geology.lower() not in s.geology.lower():
            continue
        if mission_objective and mission_objective not in s.mission_objectives:
            continue
        if q:
            hay = " ".join([s.name, s.country, s.region, s.site_id, " ".join(s.analog_types)]).lower()
            if not all(tok in hay for tok in q.lower().split()):
                continue
        item = _site_summary(st, sid)
        r = scores.get(sid)
        if r:
            item.update({"score": r.score, "score_low": r.score_low, "score_high": r.score_high, "rank": r.rank,
                         "completeness": r.completeness, "confidence": r.confidence, "status": r.status,
                         "trait_matches": r.trait_matches, "missing_criteria": r.missing_criteria})
            if r.score is None and not include_insufficient:
                continue
            if min_score > 0 and (r.score is None or r.score < min_score):
                continue
            if r.confidence < min_confidence:
                continue
        if nlat is not None:
            dist = _haversine_km(nlat, nlon, s.lat, s.lon)
            if dist > radius_km:
                continue
            item["distance_km"] = round(dist, 1)
        out.append(item)

    def key(it):
        if sort == "name":
            return (it["name"].lower(),)
        if sort == "lat":
            return (it["lat"],)
        if sort == "distance":
            return (it.get("distance_km", 1e9),)
        v = it.get(sort)
        return (v is None, -(v or 0) if order == "desc" else (v or 0), it["name"])

    if sort in ("score", "confidence", "completeness"):
        out.sort(key=key)
    else:
        out.sort(key=key, reverse=(order == "desc"))
    return {"count": len(out), "ref_id": ref.ref_id if ref else None, "objective": obj, "synthetic": st.is_synthetic,
            **(_ref_context(st, ref, ref_id, obj) if ref else {}), "sites": out}


@app.get("/api/sites/{site_id}")
def get_site(site_id: str, ref_id: Optional[str] = Query(None, pattern=ID_RE), objective: Optional[str] = Query(None, pattern=ID_RE),
             weights: Optional[str] = Query(None, max_length=400)):
    st = _store()
    s = st.sites.get(site_id)
    if s is None:
        raise HTTPException(404, detail=f"site '{site_id}' not found")
    out = _site_summary(st, site_id)
    out["features"] = {c: fv.model_dump() for c, fv in st.features.get(site_id, {}).items()}
    evidence = st.evidence.get(site_id, {})
    published = [r.model_dump() for r in st.published_rankings if r.site_id == site_id]
    out["published_rankings"] = published
    if st.scoring and st.references:
        obj = _objective(st, objective)
        uw = _weights(st, weights)
        ref = _ref(st, ref_id) or _ref(st, None, s.target_bodies[0] if s.target_bodies else "moon")
        if ref:
            ranked = rank_sites(st, ref, obj, uw, body_relevant_only=False)
            out["score"] = next(r.as_dict() for r in ranked if r.site_id == site_id)
            out["ref_id"] = ref.ref_id
            out.update(_ref_context(st, ref, ref_id, obj))
            active = st.scoring.active_criteria(ref.ref_id)
            out["active_criteria"] = [{"criterion_id": c.id, "feature": c.feature_id, "label": c.feature_label,
                                       "earth_proxy": c.earth_proxy, "description": c.description} for c in active]
            evidence = {c.id: evidence[c.id] for c in active if c.id in evidence}
        per_ref = []
        for r in st.references.values():
            res = next(x for x in rank_sites(st, r, obj, uw, body_relevant_only=False) if x.site_id == site_id)
            per_ref.append({"ref_id": r.ref_id, "name": r.name, "body": r.body, "score": res.score, "rank": res.rank,
                            "completeness": res.completeness, "status": res.status, "body_relevant": res.body_relevant})
        out["reference_scores"] = per_ref
        bodies = s.target_bodies or ["moon", "mars"]
        out["cannot_replicate_on_earth"] = {b: st.scoring.non_replicable.get(b, []) for b in bodies}
    out["evidence"] = {c: [e.model_dump() for e in items] for c, items in evidence.items()}
    return out


@app.get("/api/planetary-references")
def list_references(body: Optional[str] = Query(None, pattern="^(moon|mars)$")):
    st = _store()
    refs = [r.model_dump() for r in st.references.values() if not body or r.body == body]
    return {"count": len(refs), "references": refs,
            "coordinate_convention": "Planetocentric latitude, east-positive longitude (IAU). Moon/Mars coordinates are NOT WGS84."}


@app.get("/api/planetary-references/{ref_id}")
def get_reference(ref_id: str, objective: Optional[str] = Query(None, pattern=ID_RE), top_k: int = Query(10, ge=1, le=100)):
    st = _store()
    ref = _ref(st, ref_id)
    out = ref.model_dump()
    if st.scoring:
        obj = _objective(st, objective)
        ranked = rank_sites(st, ref, obj)
        out["matches"] = [{**r.as_dict(), "name": st.sites[r.site_id].name, "lat": st.sites[r.site_id].lat,
                           "lon": st.sites[r.site_id].lon, "analog_types": st.sites[r.site_id].analog_types} for r in ranked[:top_k]]
        # per-reference configs zero every other reference's criteria; that is a selection, not a weighting worth listing
        out["multipliers"] = {} if st.scoring.per_reference else st.scoring.reference_multipliers.get(ref.ref_id, {})
        out["active_features"] = [{"criterion_id": c.id, "feature": c.feature_id, "label": c.feature_label}
                                  for c in st.scoring.active_criteria(ref.ref_id)]
        out["cannot_replicate_on_earth"] = st.scoring.non_replicable.get(ref.body, [])
    return out


@app.get("/api/rankings")
def rankings(ref_id: Optional[str] = Query(None, pattern=ID_RE), body: Optional[str] = Query(None, pattern="^(moon|mars)$"),
             objective: Optional[str] = Query(None, pattern=ID_RE), weights: Optional[str] = Query(None, max_length=400),
             include_irrelevant: bool = False):
    st = _store()
    _need_scoring(st)
    ref = _ref(st, ref_id, body or "moon")
    if ref is None:
        raise HTTPException(503, detail="no planetary references loaded")
    obj = _objective(st, objective)
    uw = _weights(st, weights)
    ranked = rank_sites(st, ref, obj, uw, body_relevant_only=not include_irrelevant)
    published = {(r.site_id): r for r in st.published_rankings if r.ref_id == ref.ref_id and r.objective == obj}
    rows = []
    for r in ranked:
        d = r.as_dict()
        s = st.sites[r.site_id]
        d.update({"name": s.name, "country": s.country, "lat": s.lat, "lon": s.lon, "analog_types": s.analog_types})
        p = published.get(r.site_id)
        d["published"] = p.model_dump() if p else None
        rows.append(d)
    from .scoring import effective_weights
    ew = effective_weights(st.scoring, ref, obj, uw)
    return {"ref_id": ref.ref_id, "reference_name": ref.name, "body": ref.body, "objective": obj, "user_weights": uw,
            "effective_weights": ew, "effective_feature_weights": st.scoring.feature_weights(ref.ref_id, ew),
            "min_completeness": st.scoring.min_completeness, "synthetic": st.is_synthetic,
            **_ref_context(st, ref, ref_id, obj), "rankings": rows}


def _compare(st: DataStore, ids: str, ref_id: Optional[str], objective: Optional[str], weights: Optional[str]):
    _need_scoring(st)
    sids = [x.strip() for x in ids.split(",") if x.strip()]
    if not 1 <= len(sids) <= 6:
        raise HTTPException(422, detail="provide between 1 and 6 comma-separated site ids")
    unknown = [x for x in sids if x not in st.sites]
    if unknown:
        raise HTTPException(404, detail=f"unknown site ids: {', '.join(unknown)}")
    ref = _ref(st, ref_id, "moon")
    obj = _objective(st, objective)
    uw = _weights(st, weights)
    ranked = {r.site_id: r for r in rank_sites(st, ref, obj, uw, body_relevant_only=False)}
    return sids, ref, obj, ranked


@app.get("/api/compare")
def compare(ids: str = Query(..., max_length=400), ref_id: Optional[str] = Query(None, pattern=ID_RE),
            objective: Optional[str] = Query(None, pattern=ID_RE), weights: Optional[str] = Query(None, max_length=400)):
    st = _store()
    sids, ref, obj, ranked = _compare(st, ids, ref_id, objective, weights)
    active = st.scoring.active_criteria(ref.ref_id)
    crit = [c.model_dump() for c in active]
    ew = effective_weights(st.scoring, ref, obj, _weights(st, weights))
    sites = []
    for sid in sids:
        s = st.sites[sid]
        ev = st.evidence.get(sid, {})
        sites.append({**_site_summary(st, sid), "result": ranked[sid].as_dict(),
                      "evidence": {c.id: [e.model_dump() for e in ev.get(c.id, [])] for c in active}})
    matrix = []
    for c in active:
        row = {"criterion_id": c.id, "feature": c.feature_id, "label": c.feature_label, "in_score": ew.get(c.id, 0) > 0,
               "effective_weight": round(ew.get(c.id, 0.0), 4)}
        vals = []
        for sid in sids:
            fv = st.features.get(sid, {}).get(c.id)
            row[sid] = fv.value if fv else None
            row[f"{sid}__type"] = fv.value_type if fv else "missing"
            if fv and fv.value is not None:
                vals.append(fv.value)
        row["spread"] = round(max(vals) - min(vals), 6) if len(vals) >= 2 else None
        matrix.append(row)
    return {"ref_id": ref.ref_id, "reference_name": ref.name, "objective": obj, "criteria": crit, "sites": sites,
            "matrix": matrix, "synthetic": st.is_synthetic, **_ref_context(st, ref, ref_id, obj)}


@app.get("/api/export/compare.csv")
def export_compare(ids: str = Query(..., max_length=400), ref_id: Optional[str] = Query(None, pattern=ID_RE),
                   objective: Optional[str] = Query(None, pattern=ID_RE), weights: Optional[str] = Query(None, max_length=400)):
    st = _store()
    sids, ref, obj, ranked = _compare(st, ids, ref_id, objective, weights)
    buf = io.StringIO()
    w = csv.writer(buf)
    if st.is_synthetic:
        w.writerow(["# SYNTHETIC FIXTURE DATA — NOT REAL MEASUREMENTS"])
    w.writerow(["# TerraAnalog AI comparison", f"reference={ref.ref_id}", f"objective={obj}"])
    w.writerow(["site_id", "name", "lat", "lon", "rank", "score", "score_low", "score_high", "completeness", "confidence", "status",
                "criterion_id", "feature", "value", "value_type", "effective_weight", "contribution", "source_id"])
    for sid in sids:
        r, s = ranked[sid], st.sites[sid]
        for b in r.breakdown:
            w.writerow([sid, s.name, s.lat, s.lon, r.rank or "", r.score if r.score is not None else "", r.score_low, r.score_high,
                        r.completeness, r.confidence, r.status, b.criterion_id, b.feature, "" if b.value is None else b.value, b.value_type,
                        round(b.effective_weight, 4), "" if b.contribution is None else b.contribution, b.source_id])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="terraanalog_compare_{ref.ref_id}_{obj}.csv"'})


@app.get("/api/export/compare.pdf")
def export_compare_pdf(ids: str = Query(..., max_length=400), ref_id: Optional[str] = Query(None, pattern=ID_RE),
                       objective: Optional[str] = Query(None, pattern=ID_RE), weights: Optional[str] = Query(None, max_length=400)):
    """Site Comparison Report as a generated PDF (same data and validation as /api/compare)."""
    st = _store()
    sids, ref, obj, ranked = _compare(st, ids, ref_id, objective, weights)
    pdf = build_compare_pdf(st, sids, ref, obj, ranked, _weights(st, weights))
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="terraanalog_report_{ref.ref_id}_{obj}.pdf"'})


@app.get("/api/datasets")
def datasets():
    st = _store()
    return {"count": len(st.datasets), "datasets": [d.model_dump() for d in st.datasets], "data_status": st.data_status()}


@app.get("/api/docs/{doc}")
def docs(doc: str):
    st = _store()
    if doc == "methodology":
        text = st.methodology_md
    elif doc == "references":
        text = st.references_md
    else:
        raise HTTPException(404, detail="unknown document")
    if not text:
        raise HTTPException(404, detail=f"{doc} document not available in data directory")
    return PlainTextResponse(text, media_type="text/markdown")


@app.post("/api/recommend")
def post_recommend(req: RecommendRequest):
    st = _store()
    _need_scoring(st)
    return recommend(st, req)


@app.get("/api/sensitivity")
def get_sensitivity(ref_id: Optional[str] = Query(None, pattern=ID_RE), objective: Optional[str] = Query(None, pattern=ID_RE),
                    criterion: Optional[str] = Query(None, pattern=ID_RE), top_n: int = Query(6, ge=1, le=20),
                    weights: Optional[str] = Query(None, max_length=400)):
    st = _store()
    _need_scoring(st)
    ref = _ref(st, ref_id, "moon")
    feats = [c.feature_id for c in _fidelity_criteria(st, ref)]
    if criterion and criterion not in feats and criterion not in {c.id for c in st.scoring.criteria}:
        raise HTTPException(422, detail=f"unknown criterion '{criterion}'")
    crit = next((c.feature_id for c in st.scoring.criteria if c.id == criterion), criterion) if criterion else None
    obj = _objective(st, objective)
    return {**sensitivity(st, ref, obj, crit, top_n, _weights(st, weights), feats), **_ref_context(st, ref, ref_id, obj)}


@app.get("/api/clusters")
def get_clusters(k: int = Query(4, ge=1, le=10), ref_id: Optional[str] = Query(None, pattern=ID_RE)):
    st = _store()
    _need_scoring(st)
    ref = _ref(st, ref_id, "moon")
    crit = _fidelity_criteria(st, ref) if ref else st.scoring.criteria
    return {**clusters(st, k, crit), "ref_id": ref.ref_id if ref else None, **(_ref_context(st, ref, ref_id) if ref else {})}


@app.get("/api/features")
def get_features(ref_id: Optional[str] = Query(None, pattern=ID_RE)):
    """Criterion values per site (with value types) for distribution plots, keyed by FEATURE for the selected reference
    (per-reference configs) or by criterion (shared configs, where feature == criterion). Missing values are null."""
    st = _store()
    ref = _ref(st, ref_id, "moon") if st.scoring else None
    if st.scoring:
        active = st.scoring.active_criteria(ref.ref_id if ref else None)
        crit = [(c.id, c.feature_id) for c in active]
    else:
        crit = [(c, c) for c in sorted({c for d in st.features.values() for c in d})]
    out = []
    for sid, s in st.sites.items():
        feats = st.features.get(sid, {})
        out.append({"site_id": sid, "name": s.name, "values": {f: {"value": feats[c].value if c in feats else None,
                                                                    "value_type": feats[c].value_type if c in feats else "missing",
                                                                    "criterion_id": c} for c, f in crit}})
    return {"criteria": [f for _, f in crit], "ref_id": ref.ref_id if ref else None, "sites": out, "synthetic": st.is_synthetic,
            **(_ref_context(st, ref, ref_id) if ref else {})}
