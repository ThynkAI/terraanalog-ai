"""Empty and missing data must degrade gracefully, never crash."""
import json

from fastapi.testclient import TestClient

from app.loader import load_store


def _client():
    from app.main import app
    return TestClient(app)


def test_nonexistent_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TERRA_DATA_DIR", str(tmp_path / "does-not-exist"))
    c = _client()
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/sites").json()["count"] == 0
    assert c.get("/api/planetary-references").json()["count"] == 0
    assert c.get("/api/rankings").status_code == 503
    assert c.post("/api/recommend", json={"query": "mars"}).status_code == 503
    v = c.get("/api/validation").json()
    assert v["error_count"] >= 1 and all(s == "missing" for s in v["files"].values())


def test_empty_feature_collections(tmp_data):
    for f in ["earth_analog_sites.geojson", "planetary_reference_sites.geojson"]:
        (tmp_data / f).write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    c = _client()
    assert c.get("/api/sites").json()["count"] == 0
    assert c.get("/api/rankings").status_code == 503
    assert c.post("/api/recommend", json={"query": "moon"}).status_code == 422


def test_missing_optional_files(tmp_data):
    for f in ["analog_rankings.csv", "site_evidence.json", "dataset_catalog.csv", "scientific_methodology.md"]:
        (tmp_data / f).unlink()
    c = _client()
    r = c.get("/api/rankings", params={"ref_id": "moon-shackleton"}).json()
    assert r["rankings"] and all(x["published"] is None for x in r["rankings"])
    assert c.get("/api/sites/CA-HAU").json()["evidence"] == {}
    assert c.get("/api/datasets").json()["count"] == 0
    assert c.get("/api/docs/methodology").status_code == 404
    v = c.get("/api/validation").json()
    assert v["files"]["analog_rankings.csv"] == "missing"


def test_missing_scoring_config(tmp_data):
    (tmp_data / "scoring_config.json").unlink()
    c = _client()
    assert c.get("/api/sites").json()["count"] == 15  # sites still browsable
    assert c.get("/api/rankings").status_code == 503
    assert c.get("/api/compare", params={"ids": "CA-HAU"}).status_code == 503


def test_corrupt_json(tmp_data):
    (tmp_data / "earth_analog_sites.geojson").write_text("{not json")
    st = load_store(tmp_data)
    assert st.file_status["earth_analog_sites.geojson"] == "invalid" and not st.sites
    assert _client().get("/api/health").status_code == 200


def test_site_without_features_is_no_data(tmp_data):
    p = tmp_data / "analog_features.csv"
    p.write_text("\n".join(l for l in p.read_text().splitlines() if not l.startswith("US-MET")) + "\n")
    c = _client()
    r = c.get("/api/rankings", params={"ref_id": "moon-shackleton"}).json()
    met = next(x for x in r["rankings"] if x["site_id"] == "US-MET")
    assert met["status"] == "no_data" and met["score"] is None
    assert any("US-MET" in i["message"] for i in c.get("/api/validation").json()["issues"])


def test_hot_reload_on_file_change(tmp_data):
    c = _client()
    assert c.get("/api/sites").json()["count"] == 15
    p = tmp_data / "earth_analog_sites.geojson"
    gj = json.loads(p.read_text())
    gj["features"] = gj["features"][:3]
    p.write_text(json.dumps(gj))
    import os, time
    os.utime(p, (time.time() + 5, time.time() + 5))
    assert c.get("/api/sites").json()["count"] == 3
