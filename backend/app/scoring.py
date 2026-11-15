"""Transparent, documented weighted scoring (see scientific_methodology.md / docs/ARCHITECTURE.md).

score(site | reference r, objective o) = 100 * sum_c(w_c * x_c) / (sum_c_present(w_c) * scale_max)
  where  w_c = body_weight[r.body][c] * reference_multiplier[r][c] * objective_multiplier[o][c] * user_multiplier[c]

Missing values are NEVER imputed into the score:
  * evidence completeness = sum(w_c for present c) / sum(w_c for all c)
  * if completeness < min_completeness the site is reported as 'insufficient_evidence' with score = None
  * the score is always accompanied by a bounding range [missing=min, missing=max] so the uncertainty
    caused by missing criteria is explicit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .loader import DataStore
from .models import EarthSite, PlanetaryReference, ScoringConfig

DEFAULT_CONF = {"measured": 0.9, "modeled": 0.7, "provisional": 0.5, "synthetic": 0.25, "missing": 0.0}


class ScoringError(ValueError):
    pass


@dataclass
class CriterionBreakdown:
    criterion_id: str
    label: str
    value: Optional[float]
    value_type: str
    confidence: Optional[float]
    base_weight: float
    effective_weight: float
    contribution: Optional[float]  # points out of 100 contributed by this criterion
    share: Optional[float]  # fraction of the score coming from this criterion
    missing: bool
    source_id: str = ""


@dataclass
class ScoreResult:
    site_id: str
    ref_id: str
    objective: str
    score: Optional[float]
    score_low: float
    score_high: float
    completeness: float
    confidence: float
    status: str  # scored | insufficient_evidence | no_data
    breakdown: list[CriterionBreakdown] = field(default_factory=list)
    missing_criteria: list[str] = field(default_factory=list)
    trait_matches: list[str] = field(default_factory=list)
    body_relevant: bool = True
    rank: Optional[int] = None

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["breakdown"] = [b.__dict__ for b in self.breakdown]
        return d


def effective_weights(cfg: ScoringConfig, ref: PlanetaryReference, objective: str, user: Optional[dict[str, float]] = None) -> dict[str, float]:
    obj = next((o for o in cfg.objectives if o.id == objective), None)
    if obj is None:
        raise ScoringError(f"unknown objective '{objective}'")
    bw = cfg.body_weights.get(ref.body, {})
    rm = cfg.reference_multipliers.get(ref.ref_id, {})
    user = user or {}
    out: dict[str, float] = {}
    for c in cfg.criteria:
        out[c.id] = bw.get(c.id, 0.0) * rm.get(c.id, 1.0) * obj.multipliers.get(c.id, 1.0) * max(0.0, user.get(c.id, 1.0))
    return out


def score_site(store: DataStore, site: EarthSite, ref: PlanetaryReference, objective: str, user_weights: Optional[dict[str, float]] = None) -> ScoreResult:
    cfg = store.scoring
    if cfg is None:
        raise ScoringError("scoring_config.json is missing or invalid")
    weights = effective_weights(cfg, ref, objective, user_weights)
    base = cfg.body_weights.get(ref.body, {})
    conf_map = {**DEFAULT_CONF, **cfg.value_type_confidence}
    feats = store.features.get(site.site_id, {})
    total_w = sum(weights.values())
    smax, smin = cfg.scale_max, cfg.scale_min
    span = smax - smin

    present_w = 0.0
    weighted_sum = 0.0
    conf_sum = 0.0
    missing_w = 0.0
    rows: list[CriterionBreakdown] = []
    missing: list[str] = []
    for c in cfg.criteria:
        w = weights[c.id]
        fv = feats.get(c.id)
        val = fv.value if fv is not None else None
        if val is None:
            if w > 0:
                missing.append(c.id)
            missing_w += w
            rows.append(CriterionBreakdown(c.id, c.label, None, "missing", None, base.get(c.id, 0.0), w, None, None, True,
                                           fv.source_id if fv else ""))
            continue
        conf = fv.confidence if fv.confidence is not None else conf_map.get(fv.value_type, 0.25)
        norm = (val - smin) / span
        present_w += w
        weighted_sum += w * norm
        conf_sum += w * conf
        rows.append(CriterionBreakdown(c.id, c.label, val, fv.value_type, conf, base.get(c.id, 0.0), w, None, None, False, fv.source_id))

    trait_matches = sorted(set(site.analog_types) & set(ref.analog_type_affinity))
    body_rel = ref.body in site.target_bodies if site.target_bodies else True

    if total_w <= 0 or present_w <= 0:
        return ScoreResult(site.site_id, ref.ref_id, objective, None, 0.0, 100.0, 0.0, 0.0, "no_data", rows, missing, trait_matches, body_rel)

    completeness = present_w / total_w
    score = 100.0 * weighted_sum / present_w
    low = 100.0 * weighted_sum / total_w
    high = 100.0 * (weighted_sum + missing_w) / total_w
    confidence = completeness * (conf_sum / present_w)
    for r in rows:
        if not r.missing and r.value is not None:
            pts = 100.0 * r.effective_weight * ((r.value - smin) / span) / present_w
            r.contribution = round(pts, 2)
            r.share = round(pts / score, 4) if score > 0 else 0.0
    status = "scored" if completeness + 1e-9 >= cfg.min_completeness else "insufficient_evidence"
    return ScoreResult(
        site.site_id, ref.ref_id, objective,
        round(score, 1) if status == "scored" else None,
        round(low, 1), round(high, 1), round(completeness, 3), round(confidence, 3), status,
        rows, missing, trait_matches, body_rel,
    )


def rank_sites(store: DataStore, ref: PlanetaryReference, objective: str, user_weights: Optional[dict[str, float]] = None,
               site_ids: Optional[list[str]] = None, body_relevant_only: bool = True) -> list[ScoreResult]:
    sites = [store.sites[s] for s in (site_ids or list(store.sites)) if s in store.sites]
    results = [score_site(store, s, ref, objective, user_weights) for s in sites]
    if body_relevant_only:
        results = [r for r in results if r.body_relevant]
    scored = sorted((r for r in results if r.score is not None), key=lambda r: (-r.score, -r.completeness, r.site_id))
    rest = sorted((r for r in results if r.score is None), key=lambda r: (-r.completeness, r.site_id))
    for i, r in enumerate(scored, start=1):
        r.rank = i
    return scored + rest


def parse_weights(raw: Optional[str], valid: set[str]) -> dict[str, float]:
    """Parse 'terrain:1.5,geology:0.5' into user multipliers (0..5)."""
    if not raw:
        return {}
    out: dict[str, float] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise ScoringError(f"bad weight '{part}', expected criterion:multiplier")
        k, v = part.split(":", 1)
        k = k.strip()
        if k not in valid:
            raise ScoringError(f"unknown criterion '{k}'")
        try:
            x = float(v)
        except ValueError as e:
            raise ScoringError(f"bad multiplier for {k}") from e
        if not 0 <= x <= 5:
            raise ScoringError(f"multiplier for {k} must be between 0 and 5")
        out[k] = x
    return out
