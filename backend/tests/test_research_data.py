"""Integration tests against the real research outputs (data/research): per-reference criteria grouping,
published-score reproduction, value types, and the never-impute rule."""
import csv
import io
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIDELITY_FEATURES = {"lithology", "process", "landform", "resource", "slope", "ruggedness", "thermal", "aridity", "ice",
                     "abiotic_surface", "dust_sediment"}


def test_research_dataset_loads_without_synthetic_flag(research_client):
    h = research_client.get("/api/health").json()
    assert h == {**h, "status": "ok", "synthetic": False, "sites": 28, "references": 14, "errors": 0}
    m = research_client.get("/api/meta").json()
    assert m["data_status"]["synthetic"] is False and m["data_status"]["label"] == "Research dataset"
    assert m["criteria_mode"] == "per_reference"
    assert len(m["criteria"]) == 155  # 11 features x 14 references + operational_suitability


def test_store_counts_and_value_types(research_store):
    st = research_store
    assert len(st.sites) == 28 and len(st.references) == 14
    vt = Counter(fv.value_type for feats in st.features.values() for fv in feats.values())
    assert sum(vt.values()) == 4340
    assert set(vt) <= {"measured", "modeled", "provisional", "missing"} and "synthetic" not in vt
    assert vt["missing"] == 460


def test_missing_values_are_never_imputed(research_store):
    for feats in research_store.features.values():
        for fv in feats.values():
            if fv.value_type == "missing":
                assert fv.value is None
            else:
                assert fv.value is not None


def test_active_criteria_are_per_reference(research_store):
    cfg = research_store.scoring
    assert cfg.per_reference
    for ref_id in research_store.references:
        active = cfg.active_criteria(ref_id)
        ids = {c.id for c in active}
        assert len(active) == 12, ref_id
        assert ids - {"operational_suitability"} == {f"{ref_id}.{f}" for f in FIDELITY_FEATURES}
        assert {c.feature_id for c in active} == FIDELITY_FEATURES | {"operational"}
        assert all(c.ref_id in (None, ref_id) for c in active)


def test_features_are_grouped_with_readable_labels(research_store):
    feats = {f["id"]: f for f in research_store.scoring.features()}
    assert set(feats) == FIDELITY_FEATURES | {"operational"}
    assert feats["ice"]["label"] == "Ice / permafrost agreement"
    assert feats["slope"]["label"] == "Slope similarity"
    assert feats["operational"]["in_fidelity_score"] is False
    for f in feats.values():
        assert "REF-" not in f["label"]


def test_compare_uses_only_the_selected_reference(research_client):
    r = research_client.get("/api/compare", params={"ids": "EA-002,EA-004", "ref_id": "MOON-REF-02", "objective": "MOON_ISRU_ICE"}).json()
    rows = r["matrix"]
    assert len(rows) == 12
    assert all(row["criterion_id"].startswith("MOON-REF-02.") or row["criterion_id"] == "operational_suitability" for row in rows)
    op = next(row for row in rows if row["criterion_id"] == "operational_suitability")
    assert op["in_score"] is False
    assert {row["feature"] for row in rows} == FIDELITY_FEATURES | {"operational"}
    for s in r["sites"]:
        for b in s["result"]["breakdown"]:
            assert b["criterion_id"].startswith("MOON-REF-02.") or b["criterion_id"] == "operational_suitability"


def test_default_reference_is_used_and_explained(research_client):
    r = research_client.get("/api/rankings").json()
    assert r["ref_id"] == "MOON-REF-01"
    assert r["reference_defaulted"] is True
    assert any("No planetary reference selected" in n for n in r["notes"])
    r2 = research_client.get("/api/rankings", params={"ref_id": "MARS-REF-02"}).json()
    assert r2["reference_defaulted"] is False


def test_objective_body_mismatch_is_noted(research_client):
    r = research_client.get("/api/rankings", params={"ref_id": "MARS-REF-01", "objective": "MOON_ISRU_ICE"}).json()
    assert any("Moon mission profile" in n for n in r["notes"])


def test_site_detail_missing_value_shown_not_imputed(research_client):
    d = research_client.get("/api/sites/EA-004", params={"ref_id": "MOON-REF-01"}).json()
    b = {x["criterion_id"]: x for x in d["score"]["breakdown"]}
    dust = b["MOON-REF-01.dust_sediment"]
    assert dust["value"] is None and dust["value_type"] == "missing" and dust["missing"] is True
    assert dust["contribution"] is None
    assert {c["criterion_id"] for c in d["active_criteria"]} == set(b)


def test_sensitivity_and_clusters_are_feature_keyed(research_client):
    s = research_client.get("/api/sensitivity", params={"ref_id": "MARS-REF-02"}).json()
    assert {x["criterion"] for x in s["stability"]} == FIDELITY_FEATURES
    c = research_client.get("/api/clusters", params={"ref_id": "MARS-REF-02", "k": 4}).json()
    assert c["ref_id"] == "MARS-REF-02" and sum(len(x["members"]) for x in c["clusters"]) == 28


def test_csv_has_feature_column_and_no_synthetic_banner(research_client):
    text = research_client.get("/api/export/compare.csv", params={"ids": "EA-004", "ref_id": "MOON-REF-01"}).text
    first, rest = text.split("\n", 1)
    assert "SYNTHETIC" not in first
    rows = list(csv.DictReader(io.StringIO(rest)))
    dust = next(r for r in rows if r["criterion_id"] == "MOON-REF-01.dust_sediment")
    assert dust["feature"] == "dust_sediment" and dust["value"] == "" and dust["value_type"] == "missing"


def test_pdf_report_from_research_data(research_client):
    from pypdf import PdfReader
    r = research_client.get("/api/export/compare.pdf", params={"ids": "EA-002,EA-004", "ref_id": "MOON-REF-01", "objective": "MOON_ROVER_MOBILITY"})
    assert r.status_code == 200 and r.content[:5] == b"%PDF-"
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "Real TerraAnalog AI research outputs" in text and "SYNTHETIC" not in text.upper()
    assert "Feature" in text and "Ice / permafrost agreement" in text and "not in score" in text
    assert "MOON-REF-02" not in text


def test_every_published_score_is_reproduced(research_store):
    """All 588 published (reference, objective, site) rows: |engine - published| <= 0.05 and identical completeness."""
    from app.scoring import rank_sites
    st = research_store
    pub = st.published_rankings
    assert len(pub) == 588
    by_pair = {}
    for row in pub:
        by_pair.setdefault((row.ref_id, row.objective), []).append(row)
    diffs = []
    for (ref_id, obj), rows in by_pair.items():
        ranked = {r.site_id: r for r in rank_sites(st, st.references[ref_id], obj)}
        for row in rows:
            res = ranked[row.site_id]
            assert res.score_raw is not None and row.score is not None
            diffs.append(abs(res.score_raw - row.score))
            assert abs(res.completeness - row.completeness) < 1e-6
    assert len(diffs) == 588
    assert max(diffs) <= 0.05
    assert sum(diffs) / len(diffs) <= 0.01


def test_verify_published_script(tmp_path):
    out = tmp_path / "r.json"
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_published.py"), str(ROOT / "data" / "research"), "--json", str(out)],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    import json
    d = json.loads(out.read_text())
    assert d["rows_compared"] == 588 and d["rows_unscorable"] == 0 and d["score_abs_diff_unrounded"]["max"] <= 0.05


def test_recommend_picks_published_reference(research_client):
    r = research_client.post("/api/recommend", json={"query": "lava tube caves on the Moon"}).json()
    assert r["interpretation"]["ref_id"] == "MOON-REF-05" and r["interpretation"]["objective"] == "MOON_LAVA_TUBE"
    assert r["results"][0]["site_id"] == "EA-009"


def test_reference_status_class_present(research_client):
    for ref in research_client.get("/api/planetary-references").json()["references"]:
        assert ref["status_class"] in {"candidate_region", "representative_region", "verified_mission_site"}
