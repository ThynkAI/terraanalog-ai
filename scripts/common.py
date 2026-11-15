"""Shared paths and helpers for TerraAnalog AI.

All scripts are run from the package root:  python scripts/<name>.py
"""
from __future__ import annotations
import json, math, os, re, time, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
FIG = OUTPUTS / "figures"
LIT = RAW / "literature"
RETRIEVAL_DATE = os.environ.get("TA_RETRIEVAL_DATE", "2026-11-15")
USER_AGENT = "TerraAnalogAI/1.0 (open research; https://github.com/ThynkAI/terraanalog-ai)"

for p in (PROCESSED, OUTPUTS, FIG):
    p.mkdir(parents=True, exist_ok=True)

PROVENANCE_CLASSES = ("measured", "derived", "modeled", "literature", "hypothesized", "unavailable")
# Default per-value confidence by provenance class (documented in scientific_methodology.md)
PROVENANCE_CONFIDENCE = {"measured": 0.95, "derived": 0.85, "modeled": 0.70,
                         "literature": 0.75, "hypothesized": 0.30, "unavailable": 0.0}


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, p, indent=1):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=indent, ensure_ascii=False, allow_nan=False, default=_default)


def _default(o):
    try:
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:
        pass
    raise TypeError(type(o))


def clean(v, nd=4):
    """Round floats, convert NaN/inf to None (explicit null)."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    if not math.isfinite(f):
        return None
    return round(f, nd)


def earth_sites():
    return load_json(CONFIG / "earth_sites_master.json")["sites"]


def planetary_refs():
    return load_json(CONFIG / "planetary_references.json")["references"]


def scoring_config():
    return load_json(CONFIG / "scoring_config.json")


def parse_tag(s):
    """'tag:keyword' -> (tag, keyword, hypothesized_flag)."""
    tag, _, kw = s.partition(":")
    hyp = kw.endswith("?") or kw == ""
    return tag, kw.rstrip("?"), hyp


def wiki_file(title):
    idx = load_json(LIT / "wikipedia_extracts_index.json")
    if title not in idx:
        return None, None
    return LIT / idx[title]["file"], idx[title]


def find_sentence(text, kw):
    if not kw:
        return None
    for sent in re.split(r"(?<=[.!?])\s+|\n+", text):
        if kw.lower() in sent.lower():
            s = sent.strip()
            return s[:400]
    return None


def lon180(lon):
    return ((lon + 180.0) % 360.0) - 180.0
