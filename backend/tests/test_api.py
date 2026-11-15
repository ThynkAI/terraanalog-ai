"""API responses, parameter validation, filtering and sorting."""


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["synthetic"] is True


def test_meta(client):
    m = client.get("/api/meta").json()
    assert len(m["criteria"]) == 8 and m["default_objective"] == "general"
    assert {o["id"] for o in m["objectives"]} >= {"rover_mobility", "drilling", "isru", "habitat", "cave_exploration", "astronaut_field_ops"}
    assert m["data_status"]["synthetic"] is True and m["data_status"]["label"] == "Synthetic fixture data"


def test_sites_list_with_scores(client):
    r = client.get("/api/sites", params={"ref_id": "moon-shackleton"}).json()
    assert r["count"] == 15 and r["synthetic"] is True
    scored = [s for s in r["sites"] if s["score"] is not None]
    assert all(a["score"] >= b["score"] for a, b in zip(scored, scored[1:]))


def test_filters(client):
    g = lambda **p: client.get("/api/sites", params=p).json()["sites"]
    assert all("mars" in s["target_bodies"] for s in g(body="mars"))
    assert {s["site_id"] for s in g(analog_type="lava_tube_cave")} == {"US-LBN", "ES-LAN"}
    assert all("desert" in s["climate"].lower() for s in g(climate="desert"))
    assert all("basalt" in s["geology"].lower() for s in g(geology="basalt"))
    assert all("cave_exploration" in s["mission_objectives"] for s in g(mission_objective="cave_exploration"))
    hi = g(ref_id="mars-jezero", min_score=70)
    assert hi and all(s["score"] >= 70 for s in hi)
    assert all(s["confidence"] >= 0.4 for s in g(ref_id="mars-jezero", min_confidence=0.4))
    assert [s["site_id"] for s in g(q="devon")] == ["CA-HAU"]
    assert g(q="zzzz-no-match") == []


def test_sorting(client):
    names = [s["name"] for s in client.get("/api/sites", params={"sort": "name", "order": "asc"}).json()["sites"]]
    assert names == sorted(names, key=str.lower)
    lats = [s["lat"] for s in client.get("/api/sites", params={"sort": "lat", "order": "desc"}).json()["sites"]]
    assert lats == sorted(lats, reverse=True)


def test_validation_errors(client):
    assert client.get("/api/sites", params={"body": "venus"}).status_code == 422
    assert client.get("/api/sites", params={"min_score": 150}).status_code == 422
    assert client.get("/api/sites", params={"min_score": 10}).status_code == 422  # needs ref
    assert client.get("/api/sites", params={"near": "abc"}).status_code == 422
    assert client.get("/api/sites", params={"near": "95,10"}).status_code == 422
    assert client.get("/api/sites", params={"body": "mars", "ref_id": "moon-shackleton"}).status_code == 422
    assert client.get("/api/rankings", params={"ref_id": "nope"}).status_code == 404
    assert client.get("/api/rankings", params={"ref_id": "mars-gale", "objective": "fly"}).status_code == 422
    assert client.get("/api/rankings", params={"ref_id": "mars-gale", "weights": "terrain:99"}).status_code == 422
    assert client.get("/api/rankings", params={"ref_id": "../etc"}).status_code == 422


def test_site_detail(client):
    r = client.get("/api/sites/CA-HAU", params={"ref_id": "moon-shackleton", "objective": "rover_mobility"})
    d = r.json()
    assert r.status_code == 200 and d["site_id"] == "CA-HAU"
    assert d["score"]["ref_id"] == "moon-shackleton" and d["score"]["breakdown"]
    assert "terrain" in d["evidence"] and d["evidence"]["terrain"][0]["citation"]
    assert len(d["reference_scores"]) == 14
    assert d["cannot_replicate_on_earth"]["moon"]
    assert client.get("/api/sites/NOPE").status_code == 404


def test_planetary_references(client):
    r = client.get("/api/planetary-references", params={"body": "mars"}).json()
    assert r["count"] == 7 and all(x["body"] == "mars" for x in r["references"])
    assert "NOT WGS84" in r["coordinate_convention"]
    d = client.get("/api/planetary-references/mars-jezero", params={"top_k": 3}).json()
    assert len(d["matches"]) == 3 and d["matches"][0]["rank"] == 1
    assert client.get("/api/planetary-references/nope").status_code == 404


def test_rankings_custom_weights(client):
    a = client.get("/api/rankings", params={"ref_id": "moon-shackleton"}).json()
    b = client.get("/api/rankings", params={"ref_id": "moon-shackleton", "weights": "operational:5,illumination:0"}).json()
    assert b["user_weights"] == {"operational": 5.0, "illumination": 0.0}
    assert [x["site_id"] for x in a["rankings"]] != [x["site_id"] for x in b["rankings"]]
    assert all(x["published"] is not None for x in a["rankings"])


def test_datasets_and_docs(client):
    d = client.get("/api/datasets").json()
    assert d["count"] >= 5 and any(x["source_id"] == "USGS-GAZ" for x in d["datasets"])
    assert "SYNTHETIC" in client.get("/api/docs/methodology").text
    assert client.get("/api/docs/references").status_code == 200
    assert client.get("/api/docs/secrets").status_code == 404


def test_sensitivity_and_clusters(client):
    s = client.get("/api/sensitivity", params={"ref_id": "mars-gale", "criterion": "geology"}).json()
    assert s["sweeps"]["geology"][0]["multiplier"] == 0.0 and len(s["tracked_sites"]) > 0
    assert client.get("/api/sensitivity", params={"criterion": "nope"}).status_code == 422
    c = client.get("/api/clusters", params={"k": 3}).json()
    members = [m for cl in c["clusters"] for m in cl["members"]]
    assert sorted(members) == sorted(set(members)) and len(members) == 15


def test_no_secret_leakage(client):
    body = client.get("/api/meta").text + client.get("/api/validation").text
    assert "/workspace" not in body and "TERRA_DATA_DIR" not in body


def test_features_endpoint(client):
    d = client.get("/api/features").json()
    assert len(d["criteria"]) == 8 and len(d["sites"]) == 15
    rio = next(s for s in d["sites"] if s["site_id"] == "ES-RIO")
    assert rio["values"]["ice_permafrost"] == {"value": None, "value_type": "missing", "criterion_id": "ice_permafrost"}
