"""Data schema validation + ID consistency."""
import json

import pytest
from pydantic import ValidationError

from app.loader import load_store
from app.models import EarthSite, FeatureValue, PlanetaryReference, ScoringConfig
from app import config


def test_fixtures_load_without_errors(store):
    st = store.data_status()
    assert st["error_count"] == 0, st["issues"]
    assert all(store.file_status[f] == "ok" for f in config.CONTRACT_FILES)
    assert len(store.sites) >= 10 and len(store.references) >= 6


def test_fixtures_are_flagged_synthetic(store, fixture_dir):
    assert store.is_synthetic
    assert all(s.provenance == "synthetic" for s in store.sites.values())
    for f in ["analog_features.csv", "analog_rankings.csv"]:
        assert "SYNTHETIC" in (fixture_dir / f).read_text().splitlines()[0]
    for f in ["scientific_methodology.md", "source_references.md"]:
        assert "SYNTHETIC" in (fixture_dir / f).read_text()[:300]
    gj = json.loads((fixture_dir / "earth_analog_sites.geojson").read_text())
    assert gj["metadata"]["synthetic"] is True


def test_value_types_only_allowed(store):
    allowed = {"measured", "modeled", "provisional", "synthetic", "missing"}
    vts = {fv.value_type for d in store.features.values() for fv in d.values()}
    assert vts <= allowed
    assert "measured" not in vts, "fixtures must not claim measured values"


def test_id_consistency(store):
    sites, refs = set(store.sites), set(store.references)
    assert set(store.features) <= sites
    assert set(store.evidence) <= sites
    assert {r.site_id for r in store.published_rankings} <= sites
    assert {r.ref_id for r in store.published_rankings} <= refs
    assert set(store.scoring.reference_multipliers) <= refs
    crit = {c.id for c in store.scoring.criteria}
    assert {c for d in store.features.values() for c in d} <= crit


def test_required_references_present(store):
    names = " ".join(r.name.lower() for r in store.references.values())
    for k in ["shackleton", "malapert", "mare", "jezero", "gale", "elysium planitia", "south polar"]:
        assert k in names, k


def test_bad_site_rejected():
    with pytest.raises(ValidationError):
        EarthSite(site_id="bad id!", name="x", lat=10, lon=10)
    with pytest.raises(ValidationError):
        EarthSite(site_id="X-1", name="x", lat=95, lon=10)
    with pytest.raises(ValidationError):
        EarthSite(site_id="X-1", name="x", lat=10, lon=10, target_bodies=["venus"])


def test_feature_value_missing_semantics():
    fv = FeatureValue(site_id="A", criterion_id="terrain", value=None, value_type="synthetic")
    assert fv.value_type == "missing"
    with pytest.raises(ValidationError):
        FeatureValue(site_id="A", criterion_id="terrain", value=3, value_type="missing")


def test_scoring_config_rejects_unknown_criteria(fixture_dir):
    raw = json.loads((fixture_dir / "scoring_config.json").read_text())
    raw["body_weights"]["moon"]["gravity"] = 1.0
    with pytest.raises(ValidationError):
        ScoringConfig.model_validate(raw)


def test_invalid_rows_reported_not_fatal(tmp_data):
    p = tmp_data / "analog_features.csv"
    p.write_text(p.read_text() + "CA-HAU,terrain,9,score_0_5,synthetic,0.2,SYN-FIXTURE,out of range\nNOPE-1,terrain,3,score_0_5,synthetic,0.2,SYN-FIXTURE,unknown site\n")
    st = load_store(tmp_data)
    msgs = " ".join(i.message for i in st.issues)
    assert "outside scale" in msgs
    assert "NOPE-1" in msgs
    assert st.file_status["analog_features.csv"] == "partial"
    assert len(st.sites) == 15


def test_duplicate_site_rejected(tmp_data):
    p = tmp_data / "earth_analog_sites.geojson"
    gj = json.loads(p.read_text())
    gj["features"].append(gj["features"][0])
    p.write_text(json.dumps(gj))
    st = load_store(tmp_data)
    assert any("duplicate site_id" in i.message for i in st.issues)
