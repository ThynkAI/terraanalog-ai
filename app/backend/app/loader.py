"""Loads and validates the 9 data-contract files. Each file is loaded independently: a missing or invalid
file is reported as an issue and treated as empty, so the API degrades gracefully instead of crashing."""
from __future__ import annotations

import csv
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from pydantic import ValidationError

from . import config
from .models import (
    DatasetEntry,
    EarthSite,
    EvidenceItem,
    FeatureValue,
    PlanetaryReference,
    PublishedRanking,
    ScoringConfig,
)


@dataclass
class Issue:
    level: str  # "error" | "warning" | "info"
    file: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"level": self.level, "file": self.file, "message": self.message}


@dataclass
class DataStore:
    data_dir: Path
    sites: dict[str, EarthSite] = field(default_factory=dict)
    references: dict[str, PlanetaryReference] = field(default_factory=dict)
    features: dict[str, dict[str, FeatureValue]] = field(default_factory=dict)
    published_rankings: list[PublishedRanking] = field(default_factory=list)
    datasets: list[DatasetEntry] = field(default_factory=list)
    evidence: dict[str, dict[str, list[EvidenceItem]]] = field(default_factory=dict)
    scoring: Optional[ScoringConfig] = None
    methodology_md: str = ""
    references_md: str = ""
    file_status: dict[str, str] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    collection_meta: dict[str, Any] = field(default_factory=dict)

    # ---- derived helpers -------------------------------------------------------------
    @property
    def is_synthetic(self) -> bool:
        if any(s.provenance == "synthetic" for s in self.sites.values()):
            return True
        if any(fv.value_type == "synthetic" for d in self.features.values() for fv in d.values()):
            return True
        return bool(self.collection_meta.get("synthetic"))

    def data_status(self) -> dict[str, Any]:
        value_types: dict[str, int] = {}
        for d in self.features.values():
            for fv in d.values():
                value_types[fv.value_type] = value_types.get(fv.value_type, 0) + 1
        return {
            "synthetic": self.is_synthetic,
            "label": "Synthetic fixture data" if self.is_synthetic else "Research dataset",
            "data_dir_name": self.data_dir.name,
            "files": self.file_status,
            "counts": {
                "earth_sites": len(self.sites),
                "planetary_references": len(self.references),
                "feature_values": sum(len(d) for d in self.features.values()),
                "published_rankings": len(self.published_rankings),
                "datasets": len(self.datasets),
            },
            "value_types": value_types,
            "issues": [i.as_dict() for i in self.issues],
            "error_count": sum(1 for i in self.issues if i.level == "error"),
            "warning_count": sum(1 for i in self.issues if i.level == "warning"),
            "collection_meta": self.collection_meta,
        }


def _num(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() in {"na", "nan", "null", "none", "missing"}:
        return None
    return float(s)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_store(data_dir: Optional[Path] = None) -> DataStore:
    ddir = Path(data_dir) if data_dir else config.data_dir()
    st = DataStore(data_dir=ddir)
    if not ddir.exists():
        st.issues.append(Issue("error", str(ddir.name), "data directory does not exist"))
        for f in config.CONTRACT_FILES:
            st.file_status[f] = "missing"
        return st

    def present(name: str) -> Optional[Path]:
        p = ddir / name
        if not p.exists():
            st.file_status[name] = "missing"
            st.issues.append(Issue("warning", name, "file missing; treated as empty"))
            return None
        return p

    def fail(name: str, msg: str) -> None:
        st.file_status[name] = "invalid"
        st.issues.append(Issue("error", name, msg[:500]))

    # scoring_config.json --------------------------------------------------------------
    name = "scoring_config.json"
    if p := present(name):
        try:
            st.scoring = ScoringConfig.model_validate(json.loads(_read_text(p)))
            st.file_status[name] = "ok"
        except (ValidationError, ValueError) as e:
            fail(name, f"invalid scoring config: {e}")

    # earth_analog_sites.geojson -------------------------------------------------------
    name = "earth_analog_sites.geojson"
    if p := present(name):
        try:
            gj = json.loads(_read_text(p))
            if gj.get("type") != "FeatureCollection":
                raise ValueError("expected a GeoJSON FeatureCollection")
            st.collection_meta = gj.get("metadata", {}) or {}
            bad = 0
            for i, feat in enumerate(gj.get("features", [])):
                try:
                    geom = feat.get("geometry") or {}
                    if geom.get("type") != "Point":
                        raise ValueError("geometry must be a Point")
                    lon, lat = geom["coordinates"][:2]
                    site = EarthSite.model_validate({**(feat.get("properties") or {}), "lat": lat, "lon": lon})
                    if site.site_id in st.sites:
                        raise ValueError(f"duplicate site_id {site.site_id}")
                    st.sites[site.site_id] = site
                except (ValidationError, ValueError, KeyError, TypeError) as e:
                    bad += 1
                    st.issues.append(Issue("error", name, f"feature #{i} rejected: {e}"))
            st.file_status[name] = "ok" if bad == 0 else "partial"
        except (ValueError, json.JSONDecodeError) as e:
            fail(name, str(e))

    # planetary_reference_sites.geojson ------------------------------------------------
    name = "planetary_reference_sites.geojson"
    if p := present(name):
        try:
            gj = json.loads(_read_text(p))
            if gj.get("type") != "FeatureCollection":
                raise ValueError("expected a GeoJSON FeatureCollection")
            bad = 0
            for i, feat in enumerate(gj.get("features", [])):
                try:
                    lon, lat = feat["geometry"]["coordinates"][:2]
                    ref = PlanetaryReference.model_validate({**(feat.get("properties") or {}), "lat": lat, "lon_east": lon})
                    if ref.ref_id in st.references:
                        raise ValueError(f"duplicate ref_id {ref.ref_id}")
                    st.references[ref.ref_id] = ref
                except (ValidationError, ValueError, KeyError, TypeError) as e:
                    bad += 1
                    st.issues.append(Issue("error", name, f"feature #{i} rejected: {e}"))
            st.file_status[name] = "ok" if bad == 0 else "partial"
        except (ValueError, json.JSONDecodeError) as e:
            fail(name, str(e))

    # analog_features.csv --------------------------------------------------------------
    name = "analog_features.csv"
    if p := present(name):
        try:
            bad = 0
            with p.open(newline="", encoding="utf-8") as fh:
                rows = [r for r in csv.DictReader(_strip_comments(fh))]
            for i, r in enumerate(rows):
                try:
                    fv = FeatureValue.model_validate({
                        "site_id": (r.get("site_id") or "").strip(),
                        "criterion_id": (r.get("criterion_id") or "").strip(),
                        "value": _num(r.get("value")),
                        "unit": (r.get("unit") or "score_0_5").strip(),
                        "value_type": (r.get("value_type") or "synthetic").strip() or "synthetic",
                        "confidence": _num(r.get("confidence")),
                        "source_id": (r.get("source_id") or "").strip(),
                        "notes": (r.get("notes") or "").strip(),
                    })
                    if st.scoring and fv.value is not None and not (st.scoring.scale_min <= fv.value <= st.scoring.scale_max):
                        raise ValueError(f"value {fv.value} outside scale [{st.scoring.scale_min}, {st.scoring.scale_max}]")
                    st.features.setdefault(fv.site_id, {})[fv.criterion_id] = fv
                except (ValidationError, ValueError) as e:
                    bad += 1
                    st.issues.append(Issue("error", name, f"row {i + 2} rejected: {e}"))
            st.file_status[name] = "ok" if bad == 0 else "partial"
        except (OSError, csv.Error) as e:
            fail(name, str(e))

    # analog_rankings.csv --------------------------------------------------------------
    name = "analog_rankings.csv"
    if p := present(name):
        try:
            bad = 0
            with p.open(newline="", encoding="utf-8") as fh:
                for i, r in enumerate(csv.DictReader(_strip_comments(fh))):
                    try:
                        st.published_rankings.append(PublishedRanking.model_validate({
                            **{k: (v.strip() if isinstance(v, str) else v) for k, v in r.items() if k},
                            "score": _num(r.get("score")),
                            "rank": int(r["rank"]) if (r.get("rank") or "").strip() else None,
                            "completeness": _num(r.get("completeness")),
                        }))
                    except (ValidationError, ValueError) as e:
                        bad += 1
                        st.issues.append(Issue("error", name, f"row {i + 2} rejected: {e}"))
            st.file_status[name] = "ok" if bad == 0 else "partial"
        except (OSError, csv.Error) as e:
            fail(name, str(e))

    # dataset_catalog.csv --------------------------------------------------------------
    name = "dataset_catalog.csv"
    if p := present(name):
        try:
            with p.open(newline="", encoding="utf-8") as fh:
                for i, r in enumerate(csv.DictReader(_strip_comments(fh))):
                    try:
                        st.datasets.append(DatasetEntry.model_validate({k: (v or "").strip() for k, v in r.items() if k}))
                    except ValidationError as e:
                        st.issues.append(Issue("error", name, f"row {i + 2} rejected: {e}"))
            st.file_status[name] = "ok"
        except (OSError, csv.Error) as e:
            fail(name, str(e))

    # site_evidence.json ---------------------------------------------------------------
    name = "site_evidence.json"
    if p := present(name):
        try:
            raw = json.loads(_read_text(p))
            ev = raw.get("evidence", raw)
            for sid, crit in ev.items():
                if sid == "meta":
                    continue
                for cid, items in (crit or {}).items():
                    st.evidence.setdefault(sid, {})[cid] = [EvidenceItem.model_validate(x) for x in items]
            st.file_status[name] = "ok"
        except (ValidationError, ValueError, AttributeError, json.JSONDecodeError) as e:
            fail(name, f"invalid evidence file: {e}")

    for name, attr in (("scientific_methodology.md", "methodology_md"), ("source_references.md", "references_md")):
        if p := present(name):
            setattr(st, attr, _read_text(p))
            st.file_status[name] = "ok"

    _cross_check(st)
    return st


def _strip_comments(fh):
    """Allow '#'-prefixed banner lines (used for SYNTHETIC warnings) at the top of CSV files."""
    for line in fh:
        if line.lstrip().startswith("#"):
            continue
        yield line


def _cross_check(st: DataStore) -> None:
    """ID consistency across datasets (Phase 7)."""
    site_ids, ref_ids = set(st.sites), set(st.references)
    crit_ids = {c.id for c in st.scoring.criteria} if st.scoring else set()
    obj_ids = {o.id for o in st.scoring.objectives} if st.scoring else set()
    ds_ids = {d.source_id for d in st.datasets}

    for sid in sorted(set(st.features) - site_ids):
        st.issues.append(Issue("error", "analog_features.csv", f"site_id '{sid}' not found in earth_analog_sites.geojson"))
    for sid in sorted(site_ids - set(st.features)):
        st.issues.append(Issue("warning", "analog_features.csv", f"site '{sid}' has no feature values; it cannot be scored"))
    if crit_ids:
        for sid, d in st.features.items():
            for cid in sorted(set(d) - crit_ids):
                st.issues.append(Issue("warning", "analog_features.csv", f"criterion '{cid}' (site {sid}) is not defined in scoring_config.json; ignored"))
    for r in st.published_rankings:
        if r.site_id not in site_ids:
            st.issues.append(Issue("error", "analog_rankings.csv", f"site_id '{r.site_id}' unknown"))
        if r.ref_id not in ref_ids:
            st.issues.append(Issue("error", "analog_rankings.csv", f"ref_id '{r.ref_id}' unknown"))
        if obj_ids and r.objective not in obj_ids:
            st.issues.append(Issue("error", "analog_rankings.csv", f"objective '{r.objective}' unknown"))
    for sid in sorted(set(st.evidence) - site_ids):
        st.issues.append(Issue("error", "site_evidence.json", f"site_id '{sid}' unknown"))
    if st.scoring:
        for rid in sorted(set(st.scoring.reference_multipliers) - ref_ids):
            st.issues.append(Issue("warning", "scoring_config.json", f"reference_multipliers for unknown ref_id '{rid}'"))
        for body, rid in st.scoring.default_reference.items():
            if ref_ids and rid not in ref_ids:
                st.issues.append(Issue("error", "scoring_config.json", f"default_reference[{body}] '{rid}' unknown"))
    if ds_ids:
        used = {fv.source_id for d in st.features.values() for fv in d.values() if fv.source_id}
        used |= {e.source_id for d in st.evidence.values() for items in d.values() for e in items if e.source_id}
        for s in sorted(used - ds_ids):
            st.issues.append(Issue("warning", "dataset_catalog.csv", f"source_id '{s}' referenced but not catalogued"))


# ---- cached access with hot reload when files change -----------------------------------
_lock = threading.Lock()
_cache: dict[str, Any] = {"sig": None, "store": None}


def _signature(ddir: Path) -> tuple:
    out = [str(ddir)]
    for f in config.CONTRACT_FILES:
        p = ddir / f
        out.append((f, p.stat().st_mtime_ns if p.exists() else None))
    return tuple(out)


def get_store() -> DataStore:
    ddir = config.data_dir()
    sig = _signature(ddir)
    with _lock:
        if _cache["sig"] != sig or _cache["store"] is None:
            _cache["store"] = load_store(ddir)
            _cache["sig"] = sig
        return _cache["store"]
