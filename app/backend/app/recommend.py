"""Explainable recommendation engine.

Deterministic keyword/intent parsing maps a free-text query onto STRUCTURED filters (body, mission objective,
analog types, planetary reference). Results come only from the loaded site data and the documented scoring
function; nothing is generated. Every explanation is assembled from stored values, evidence and config text.
"""
from __future__ import annotations

import re
from typing import Optional

from .loader import DataStore
from .models import RecommendRequest
from .scoring import ScoringError, rank_sites

BODY_KEYWORDS = {
    "moon": ["moon", "lunar", "selen", "artemis", "regolith", "south pole", "south-pole", "psr", "permanently shadowed", "mare", "maria"],
    "mars": ["mars", "martian", "red planet", "jezero", "gale", "elysium", "utopia", "arsia", "meridiani"],
}
OBJECTIVE_KEYWORDS = {
    "rover_mobility": ["rover", "mobility", "traverse", "trafficab", "driving", "wheel"],
    "drilling": ["drill", "core", "coring", "subsurface sampling", "auger"],
    "isru": ["isru", "resource", "prospect", "in-situ", "in situ", "water extraction", "volatile", "mining"],
    "habitat": ["habitat", "shelter", "base", "outpost", "construction", "living"],
    "cave_exploration": ["cave", "lava tube", "subsurface robot", "skylight", "pit", "underground", "subsurface"],
    "astronaut_field_ops": ["astronaut", "eva", "field op", "spacesuit", "crew", "geolog training", "field training"],
}
TYPE_KEYWORDS = {
    "polar_desert": ["polar", "polar desert", "arctic", "antarctic", "cold desert"],
    "permafrost_ice": ["ice", "permafrost", "frozen", "glacier", "cold trap", "volatile"],
    "basaltic_volcanic": ["basalt", "volcanic", "lava", "volcano", "mare", "plains"],
    "impact_crater": ["impact", "crater", "ejecta", "shock"],
    "lava_tube_cave": ["cave", "lava tube", "tube", "skylight", "pit"],
    "hyperarid_desert": ["hyperarid", "hyper-arid", "arid", "desert", "dust", "dry"],
    "acidic_aqueous": ["acid", "aqueous", "sulfate", "jarosite", "mineral", "water-altered", "delta", "lake"],
    "high_altitude": ["high altitude", "high-altitude", "summit", "uv"],
    # research-dataset analog types
    "aqueous_alteration": ["aqueous", "hydrothermal", "acid", "sulfate", "jarosite", "water-altered", "delta", "lake", "clay"],
    "evaporite_basin": ["evaporite", "salt", "playa", "salar", "brine", "sediment"],
    "arid_desert": ["arid", "hyperarid", "hyper-arid", "desert", "dust", "dry"],
}
# Intent → tokens used to find the matching objective when the dataset uses mission-profile ids (e.g. MOON_ROVER_MOBILITY)
INTENT_OBJECTIVE_TOKENS = {
    "rover_mobility": ["rover_mobility", "rover", "mobility"],
    "drilling": ["drilling", "drill", "isru"],
    "isru": ["isru", "resource"],
    "habitat": ["habitat"],
    "cave_exploration": ["cave_exploration", "lava_tube", "cave"],
    "astronaut_field_ops": ["astronaut_field_ops", "eva", "field_geology"],
    "field_geology": ["field_geology", "geology"],
    "astrobiology": ["astrobio", "sediment"],
}
EXTRA_OBJECTIVE_KEYWORDS = {
    "field_geology": ["field geology", "geolog", "sampling"],
    "astrobiology": ["astrobio", "biosignature", "life detection", "habitability"],
}
REF_NAME_STOPWORDS = {"lunar", "mare", "planitia", "planum", "mons", "base", "crater", "region", "plains", "south", "north", "polar",
                      "pole", "the", "and", "rim", "vicinity", "landing", "site", "field", "dome", "pit", "deposits", "layered",
                      "highlands", "candidate", "regions", "containing", "artemis", "iii", "permanently", "shadowed", "flank",
                      "cave", "skylights", "tubes", "lava", "basaltic", "volcanic", "mid-latitude", "ground", "ice", "massif",
                      "periglacial", "regolith", "delta", "impact", "hills", "pole-centred", "mission"}
REF_KEYWORDS = {
    "moon-shackleton": ["shackleton"],
    "moon-malapert": ["malapert"],
    "moon-de-gerlache": ["de gerlache", "gerlache"],
    "moon-mare-tranquillitatis": ["tranquillitatis", "tranquility", "apollo 11"],
    "moon-marius-hills": ["marius"],
    "moon-rima-hadley": ["hadley", "apollo 15", "rille"],
    "mars-jezero": ["jezero", "perseverance", "delta"],
    "mars-gale": ["gale", "curiosity", "mount sharp", "aeolis"],
    "mars-elysium-planitia": ["elysium", "insight", "volcanic plains"],
    "mars-utopia-planitia": ["utopia", "ground ice", "buried ice"],
    "mars-arsia-mons": ["arsia", "tharsis"],
    "mars-planum-australe": ["planum australe", "south polar cap", "polar layered"],
    "mars-meridiani-planum": ["meridiani", "opportunity", "hematite"],
}
# reference hints by (body, analog type) when no reference was named
TYPE_REF_HINT = {
    ("moon", "polar_desert"): "moon-south-pole-region",
    ("moon", "permafrost_ice"): "moon-shackleton",
    ("moon", "basaltic_volcanic"): "moon-mare-tranquillitatis",
    ("moon", "lava_tube_cave"): "moon-marius-hills",
    ("moon", "impact_crater"): "moon-shackleton",
    ("mars", "basaltic_volcanic"): "mars-elysium-planitia",
    ("mars", "lava_tube_cave"): "mars-arsia-mons",
    ("mars", "permafrost_ice"): "mars-utopia-planitia",
    ("mars", "polar_desert"): "mars-planum-australe",
    ("mars", "acidic_aqueous"): "mars-meridiani-planum",
    ("mars", "hyperarid_desert"): "mars-gale",
    ("mars", "impact_crater"): "mars-gale",
}


def _has(text: str, kw: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(kw), text) is not None


def _ref_keywords(store: Optional[DataStore]) -> dict[str, list[str]]:
    """Static keywords for known fixture ids plus proper nouns taken from each loaded reference's own name."""
    out = {k: list(v) for k, v in REF_KEYWORDS.items()}
    if store is not None:
        for r in store.references.values():
            words = re.findall(r"[A-Za-z][A-Za-z\-]+", r.name)
            kws = [w.lower() for w in words if w[0].isupper() and w.lower() not in REF_NAME_STOPWORDS and len(w) > 3]
            out.setdefault(r.ref_id, [])
            out[r.ref_id] += [k for k in kws if k not in out[r.ref_id]]
    return out


def parse_query(query: str, store: Optional[DataStore] = None) -> dict:
    t = " " + query.lower() + " "
    types_kw = TYPE_KEYWORDS
    if store is not None and store.scoring is not None:
        known = set(store.scoring.analog_types) | {ty for s in store.sites.values() for ty in s.analog_types}
        types_kw = {k: v for k, v in TYPE_KEYWORDS.items() if k in known}
    ref_kw = _ref_keywords(store)
    obj_kw = {**OBJECTIVE_KEYWORDS, **EXTRA_OBJECTIVE_KEYWORDS}
    bodies = [b for b, kws in BODY_KEYWORDS.items() if any(_has(t, k) for k in kws)]
    objs = [o for o, kws in obj_kw.items() if any(_has(t, k) for k in kws)]
    types = [ty for ty, kws in types_kw.items() if any(_has(t, k) for k in kws)]
    refs = [r for r, kws in ref_kw.items() if any(_has(t, k) for k in kws)]
    matched_terms = sorted({k for kws in list(BODY_KEYWORDS.values()) + list(obj_kw.values()) + list(types_kw.values()) + list(ref_kw.values()) for k in kws if _has(t, k)})
    return {"bodies": bodies, "objectives": objs, "analog_types": types, "references": refs, "matched_terms": matched_terms}


def _resolve_objective(cfg, intents: list[str], body: str) -> Optional[str]:
    """Map parsed intents onto the dataset's objectives: exact id first, else a profile for this body whose id contains a token."""
    ids = {o.id for o in cfg.objectives}
    for intent in intents:
        if intent in ids:
            return intent
        for tok in INTENT_OBJECTIVE_TOKENS.get(intent, [intent]):
            for o in cfg.objectives:
                if (o.body_key in (None, body)) and o.id != "general" and tok in o.id.lower():
                    return o.id
    return None


def recommend(store: DataStore, req: RecommendRequest) -> dict:
    cfg = store.scoring
    if cfg is None or not store.sites or not store.references:
        raise ScoringError("data not available: scoring config, sites and references are all required")
    parsed = parse_query(req.query, store)
    notes: list[str] = []

    # resolve reference + body
    ref = None
    if req.ref_id:
        ref = store.references.get(req.ref_id)
        if ref is None:
            raise ScoringError(f"unknown ref_id '{req.ref_id}'")
    elif parsed["references"]:
        ref = next((store.references[r] for r in parsed["references"] if r in store.references), None)
    body = req.body or (ref.body if ref else (parsed["bodies"][0] if len(parsed["bodies"]) == 1 else None))
    if len(parsed["bodies"]) > 1 and not req.body and not ref:
        notes.append("Query mentions both Moon and Mars; defaulting to Moon. Select a body to override.")
        body = "moon"
    if body is None:
        body = "moon"
        notes.append("No planetary body detected; defaulting to Moon. Add 'lunar' or 'Mars' to the query to change.")
    types = req.analog_types or parsed["analog_types"]
    obj_ids = {o.id for o in cfg.objectives}
    objective = req.objective or _resolve_objective(cfg, parsed["objectives"], body) or cfg.default_objective
    if objective not in obj_ids:
        raise ScoringError(f"unknown objective '{objective}'")
    obj_obj = next(o for o in cfg.objectives if o.id == objective)
    if ref is None and obj_obj.published_references:
        cands = [store.references[r] for r in obj_obj.published_references if r in store.references and store.references[r].body == body]
        typed_c = [r for r in cands if set(types) & set(r.analog_type_affinity)]
        ref = (typed_c or cands or [None])[0]
        if ref is not None:
            notes.append(f"{obj_obj.label} is published against {', '.join(obj_obj.published_references)}; using {ref.name}.")
    if ref is None:
        hinted = next((TYPE_REF_HINT[(body, ty)] for ty in types if (body, ty) in TYPE_REF_HINT and TYPE_REF_HINT[(body, ty)] in store.references), None)
        if hinted is None:
            # data-driven hint: a reference of this body whose analog-type affinity matches a requested type
            hinted = next((r.ref_id for ty in types for r in store.references.values() if r.body == body and ty in r.analog_type_affinity), None)
        ref = store.references.get(hinted or cfg.default_reference.get(body, ""))
        if ref is None:
            ref = next((r for r in store.references.values() if r.body == body), None)
        if ref is None:
            raise ScoringError(f"no planetary reference available for {body}")
    if ref.body != body:
        notes.append(f"Reference {ref.name} is on {ref.body}; using that body.")
        body = ref.body

    ranked = rank_sites(store, ref, objective)
    pool = ranked
    if types:
        typed = [r for r in ranked if set(store.sites[r.site_id].analog_types) & set(types)]
        if typed:
            pool = typed
        else:
            notes.append("No site matches the requested environment types; showing best overall matches instead.")
    scored = [r for r in pool if r.score is not None]
    insufficient = [r for r in pool if r.score is None]
    top = scored[: req.top_k]

    obj_label = next(o.label for o in cfg.objectives if o.id == objective)
    crit_label = {c.id: c.feature_label for c in cfg.criteria}
    results = []
    for r in top:
        site = store.sites[r.site_id]
        contrib = sorted((b for b in r.breakdown if b.contribution and b.in_score), key=lambda b: -(b.contribution or 0))
        in_w = [b.effective_weight for b in r.breakdown if b.in_score]
        mean_w = (sum(in_w) / len(in_w)) if in_w else 0.0
        strengths = [f"{b.label}: {round(b.value, 2):g}/5 ({b.value_type})" for b in contrib[:3]]
        weak = [f"{b.label}: {round(b.value, 2):g}/5" for b in r.breakdown if not b.missing and b.value is not None and b.value <= 2 and b.in_score and b.effective_weight >= mean_w]
        why = [f"Ranked #{r.rank} of {sum(1 for x in ranked if x.rank)} for {obj_label} against {ref.name} (score {r.score}/100; plausible range {r.score_low}–{r.score_high} given missing data)."]
        if r.trait_matches:
            why.append("Shares environment traits with the reference: " + ", ".join(t.replace("_", " ") for t in r.trait_matches) + ".")
        if strengths:
            why.append("Largest score contributions — " + "; ".join(strengths) + ".")
        if weak:
            why.append("Weak points — " + "; ".join(weak) + ".")
        caveats = []
        if r.missing_criteria:
            caveats.append("Missing evidence (not imputed): " + ", ".join(crit_label.get(c, c) for c in r.missing_criteria) + ".")
        vt = {b.value_type for b in r.breakdown if not b.missing}
        if vt & {"synthetic", "provisional"}:
            caveats.append("Some inputs are " + " / ".join(sorted(vt & {"synthetic", "provisional"})) + " values — not measurements.")
        results.append({
            "site_id": r.site_id, "name": site.name, "country": site.country, "lat": site.lat, "lon": site.lon,
            "analog_types": site.analog_types, "score": r.score, "score_low": r.score_low, "score_high": r.score_high,
            "rank": r.rank, "completeness": r.completeness, "confidence": r.confidence,
            "why": why, "caveats": caveats, "site_limitations": site.limitations,
            "breakdown": [b.__dict__ for b in r.breakdown],
        })
    return {
        "query": req.query,
        "interpretation": {
            "body": body, "ref_id": ref.ref_id, "reference_name": ref.name, "objective": objective,
            "objective_label": obj_label, "analog_types": types, "matched_terms": parsed["matched_terms"],
            "method": "deterministic keyword parsing → structured filters → documented weighted scoring (no generative model)",
        },
        "results": results,
        "excluded_insufficient_evidence": [{"site_id": r.site_id, "completeness": r.completeness} for r in insufficient],
        "cannot_replicate_on_earth": cfg.non_replicable.get(body, []),
        "notes": notes,
    }
