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
from .scoring import ScoringError, parse_weights, rank_sites, score_site

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
    return parse_weights(raw, {c.id for c in st.scoring.criteria}) if st.scoring else {}


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
        "climates": sorted({s.climate for s in st.sites.values() if s.climate}),
        "countries": sorted({s.country for s in st.sites.values() if s.country}),
    }


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
    return {"count": len(out), "ref_id": ref.ref_id if ref else None, "objective": obj, "synthetic": st.is_synthetic, "sites": out}


@app.get("/api/sites/{site_id}")
def get_site(site_id: str, ref_id: Optional[str] = Query(None, pattern=ID_RE), objective: Optional[str] = Query(None, pattern=ID_RE),
             weights: Optional[str] = Query(None, max_length=400)):
    st = _store()
    s = st.sites.get(site_id)
    if s is None:
        raise HTTPException(404, detail=f"site '{site_id}' not found")
    out = _site_summary(st, site_id)
    out["features"] = {c: fv.model_dump() for c, fv in st.features.get(site_id, {}).items()}
    out["evidence"] = {c: [e.model_dump() for e in items] for c, items in st.evidence.get(site_id, {}).items()}
    published = [r.model_dump() for r in st.published_rankings if r.site_id == site_id]
    out["published_rankings"] = published
    if st.scoring and st.references:
        obj = _objective(st, objective)
        uw = _weights(st, weights)
        ref = _ref(st, ref_id) or _ref(st, None, s.target_bodies[0] if s.target_bodies else "moon")
        if ref:
            ranked = rank_sites(st, ref, obj, uw, body_relevant_only=False)
            out["score"] = next(r.as_dict() for r in ranked if r.site_id == site_id)
        per_ref = []
        for r in st.references.values():
            res = next(x for x in rank_sites(st, r, obj, uw, body_relevant_only=False) if x.site_id == site_id)
            per_ref.append({"ref_id": r.ref_id, "name": r.name, "body": r.body, "score": res.score, "rank": res.rank,
                            "completeness": res.completeness, "status": res.status, "body_relevant": res.body_relevant})
        out["reference_scores"] = per_ref
        bodies = s.target_bodies or ["moon", "mars"]
        out["cannot_replicate_on_earth"] = {b: st.scoring.non_replicable.get(b, []) for b in bodies}
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
        out["multipliers"] = st.scoring.reference_multipliers.get(ref.ref_id, {})
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
    return {"ref_id": ref.ref_id, "reference_name": ref.name, "body": ref.body, "objective": obj, "user_weights": uw,
            "effective_weights": effective_weights(st.scoring, ref, obj, uw), "min_completeness": st.scoring.min_completeness,
            "synthetic": st.is_synthetic, "rankings": rows}


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
    crit = [c.model_dump() for c in st.scoring.criteria]
    sites = []
    for sid in sids:
        s = st.sites[sid]
        sites.append({**_site_summary(st, sid), "result": ranked[sid].as_dict(),
                      "evidence": {c: [e.model_dump() for e in items] for c, items in st.evidence.get(sid, {}).items()}})
    matrix = []
    for c in st.scoring.criteria:
        row = {"criterion_id": c.id, "label": c.label}
        vals = []
        for sid in sids:
            fv = st.features.get(sid, {}).get(c.id)
            row[sid] = fv.value if fv else None
            row[f"{sid}__type"] = fv.value_type if fv else "missing"
            if fv and fv.value is not None:
                vals.append(fv.value)
        row["spread"] = (max(vals) - min(vals)) if len(vals) >= 2 else None
        matrix.append(row)
    return {"ref_id": ref.ref_id, "reference_name": ref.name, "objective": obj, "criteria": crit, "sites": sites,
            "matrix": matrix, "synthetic": st.is_synthetic}


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
                "criterion_id", "value", "value_type", "effective_weight", "contribution", "source_id"])
    for sid in sids:
        r, s = ranked[sid], st.sites[sid]
        for b in r.breakdown:
            w.writerow([sid, s.name, s.lat, s.lon, r.rank or "", r.score if r.score is not None else "", r.score_low, r.score_high,
                        r.completeness, r.confidence, r.status, b.criterion_id, "" if b.value is None else b.value, b.value_type,
                        round(b.effective_weight, 4), "" if b.contribution is None else b.contribution, b.source_id])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="terraanalog_compare_{ref.ref_id}_{obj}.csv"'})


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
    if criterion and criterion not in {c.id for c in st.scoring.criteria}:
        raise HTTPException(422, detail=f"unknown criterion '{criterion}'")
    return sensitivity(st, ref, _objective(st, objective), criterion, top_n, _weights(st, weights))


@app.get("/api/clusters")
def get_clusters(k: int = Query(4, ge=1, le=10)):
    st = _store()
    _need_scoring(st)
    return clusters(st, k)


@app.get("/api/features")
def get_features():
    """All criterion values per site (with value types) for distribution plots. Missing values are null."""
    st = _store()
    crit = [c.id for c in st.scoring.criteria] if st.scoring else sorted({c for d in st.features.values() for c in d})
    out = []
    for sid, s in st.sites.items():
        feats = st.features.get(sid, {})
        out.append({"site_id": sid, "name": s.name, "values": {c: {"value": feats[c].value if c in feats else None,
                                                                    "value_type": feats[c].value_type if c in feats else "missing"} for c in crit}})
    return {"criteria": crit, "sites": out, "synthetic": st.is_synthetic}
