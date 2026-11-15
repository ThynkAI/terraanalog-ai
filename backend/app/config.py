"""Runtime configuration. All values come from environment variables; no secrets are required."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RESEARCH_DATA_DIR = REPO_ROOT / "data" / "research"  # real research outputs (default)
FIXTURE_DATA_DIR = REPO_ROOT / "data" / "fixtures"  # synthetic fallback
DEFAULT_DATA_DIR = RESEARCH_DATA_DIR if (RESEARCH_DATA_DIR / "scoring_config.json").exists() else FIXTURE_DATA_DIR


def data_dir() -> Path:
    """Directory holding the 9 data-contract files. Default: data/research (falls back to the synthetic data/fixtures
    if the research files are absent). Override with TERRA_DATA_DIR."""
    return Path(os.environ.get("TERRA_DATA_DIR", str(DEFAULT_DATA_DIR))).expanduser().resolve()


def cors_origins() -> list[str]:
    raw = os.environ.get("TERRA_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]


CONTRACT_FILES = [
    "earth_analog_sites.geojson",
    "planetary_reference_sites.geojson",
    "analog_features.csv",
    "analog_rankings.csv",
    "dataset_catalog.csv",
    "site_evidence.json",
    "scoring_config.json",
    "scientific_methodology.md",
    "source_references.md",
]
