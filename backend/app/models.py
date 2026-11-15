"""Typed data models + validation schemas for the TerraAnalog data contract (see docs/DATA_INTEGRATION.md)."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Body = Literal["moon", "mars"]
ValueType = Literal["measured", "modeled", "provisional", "synthetic", "missing"]
Provenance = Literal["measured", "modeled", "provisional", "synthetic", "mixed", "published"]
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$"


class Imagery(BaseModel):
    url: str
    credit: str
    license: str


class EarthSite(BaseModel):
    """One Earth analog site (a GeoJSON Point feature, WGS84 lon/lat per RFC 7946)."""

    model_config = ConfigDict(extra="allow")
    site_id: str = Field(pattern=ID_PATTERN)
    name: str = Field(min_length=1)
    country: str = ""
    region: str = ""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    analog_types: list[str] = Field(default_factory=list)
    climate: str = ""
    geology: str = ""
    target_bodies: list[Body] = Field(default_factory=list)
    mission_objectives: list[str] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
    elevation_m: Optional[float] = None
    description: str = ""
    limitations: list[str] = Field(default_factory=list)
    imagery: Optional[Imagery] = None
    provenance: Provenance = "synthetic"
    coordinate_note: str = ""


class PlanetaryReference(BaseModel):
    """Moon/Mars reference region. Coordinates are planetocentric/IAU body-fixed, NOT Earth WGS84."""

    model_config = ConfigDict(extra="allow")
    ref_id: str = Field(pattern=ID_PATTERN)
    body: Body
    name: str
    region_type: str = ""
    lat: float = Field(ge=-90, le=90)
    lon_east: float = Field(ge=-180, le=180, description="East-positive longitude in [-180, 180]")
    lon_east_360: Optional[float] = Field(default=None, ge=0, lt=360)
    coordinate_system: str = ""
    body_radius_km: float = Field(gt=0)
    diameter_km: Optional[float] = Field(default=None, ge=0)
    gazetteer_feature_id: Optional[str] = None
    description: str = ""
    traits: list[str] = Field(default_factory=list)
    analog_type_affinity: list[str] = Field(default_factory=list)
    citation: str = "citation pending from research dataset"
    provenance: Provenance = "published"

    @model_validator(mode="after")
    def _lon_consistency(self) -> "PlanetaryReference":
        if self.lon_east_360 is not None:
            back = self.lon_east_360 - 360 if self.lon_east_360 > 180 else self.lon_east_360
            if abs(back - self.lon_east) > 1e-6:
                raise ValueError(f"lon_east ({self.lon_east}) and lon_east_360 ({self.lon_east_360}) disagree")
        return self


class FeatureValue(BaseModel):
    site_id: str = Field(pattern=ID_PATTERN)
    criterion_id: str
    value: Optional[float] = None
    unit: str = "score_0_5"
    value_type: ValueType = "synthetic"
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    source_id: str = ""
    notes: str = ""

    @model_validator(mode="after")
    def _missing_consistency(self) -> "FeatureValue":
        if self.value is None:
            self.value_type = "missing"
        elif self.value_type == "missing":
            raise ValueError("value_type 'missing' but a value was supplied")
        return self


class PublishedRanking(BaseModel):
    ref_id: str = Field(pattern=ID_PATTERN)
    objective: str
    site_id: str = Field(pattern=ID_PATTERN)
    score: Optional[float] = Field(default=None, ge=0, le=100)
    rank: Optional[int] = Field(default=None, ge=1)
    completeness: Optional[float] = Field(default=None, ge=0, le=1)
    method_version: str = ""
    provenance: Provenance = "synthetic"


class DatasetEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    source_id: str = Field(pattern=ID_PATTERN)
    name: str
    provider: str = ""
    url: str = ""
    license: str = ""
    data_type: str = ""
    usage: str = ""
    status: str = ""
    provenance: str = ""
    notes: str = ""


class EvidenceItem(BaseModel):
    statement: str
    source_id: str = ""
    value_type: ValueType = "synthetic"
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    citation: str = "citation pending from research dataset"


class Criterion(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    label: str
    description: str = ""
    earth_proxy: str = ""
    source_families: list[str] = Field(default_factory=list)


class Objective(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    label: str
    description: str = ""
    multipliers: dict[str, float] = Field(default_factory=dict)

    @field_validator("multipliers")
    @classmethod
    def _nonneg(cls, v: dict[str, float]) -> dict[str, float]:
        for k, x in v.items():
            if x < 0:
                raise ValueError(f"negative multiplier for {k}")
        return v


class ScoringConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    meta: dict[str, Any] = Field(default_factory=dict)
    scale_min: float = 0
    scale_max: float = 5
    min_completeness: float = Field(default=0.7, ge=0, le=1)
    criteria: list[Criterion]
    body_weights: dict[Body, dict[str, float]]
    reference_multipliers: dict[str, dict[str, float]] = Field(default_factory=dict)
    objectives: list[Objective]
    default_objective: str = "general"
    default_reference: dict[Body, str] = Field(default_factory=dict)
    value_type_confidence: dict[str, float] = Field(default_factory=dict)
    non_replicable: dict[Body, list[str]] = Field(default_factory=dict)
    analog_types: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> "ScoringConfig":
        if self.scale_max <= self.scale_min:
            raise ValueError("scale_max must exceed scale_min")
        ids = {c.id for c in self.criteria}
        if len(ids) != len(self.criteria):
            raise ValueError("duplicate criterion ids")
        for body, w in self.body_weights.items():
            unknown = set(w) - ids
            if unknown:
                raise ValueError(f"body_weights[{body}] references unknown criteria {sorted(unknown)}")
            if any(x < 0 for x in w.values()):
                raise ValueError("weights must be non-negative")
        for o in self.objectives:
            unknown = set(o.multipliers) - ids
            if unknown:
                raise ValueError(f"objective {o.id} references unknown criteria {sorted(unknown)}")
        if self.default_objective not in {o.id for o in self.objectives}:
            raise ValueError("default_objective must be one of objectives")
        return self


class RecommendRequest(BaseModel):
    query: str = Field(default="", max_length=500)
    body: Optional[Body] = None
    objective: Optional[str] = Field(default=None, pattern=ID_PATTERN)
    ref_id: Optional[str] = Field(default=None, pattern=ID_PATTERN)
    analog_types: list[str] = Field(default_factory=list, max_length=20)
    top_k: int = Field(default=5, ge=1, le=50)
