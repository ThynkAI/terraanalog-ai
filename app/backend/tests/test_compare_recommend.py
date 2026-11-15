"""Site comparison behaviour and the explainable recommendation engine."""


def test_compare_basic(client):
    r = client.get("/api/compare", params={"ids": "CA-HAU,AQ-MDV,US-LBN", "ref_id": "moon-shackleton", "objective": "rover_mobility"})
    d = r.json()
    assert r.status_code == 200 and [s["site_id"] for s in d["sites"]] == ["CA-HAU", "AQ-MDV", "US-LBN"]
    assert len(d["matrix"]) == 8
    row = next(m for m in d["matrix"] if m["criterion_id"] == "illumination")
    assert row["CA-HAU"] == 5 and row["CA-HAU__type"] == "provisional"
    assert row["spread"] == max(row[s] for s in ["CA-HAU", "AQ-MDV", "US-LBN"]) - min(row[s] for s in ["CA-HAU", "AQ-MDV", "US-LBN"])


def test_compare_missing_values_marked(client):
    d = client.get("/api/compare", params={"ids": "ES-RIO,CA-HAU", "ref_id": "mars-jezero"}).json()
    row = next(m for m in d["matrix"] if m["criterion_id"] == "ice_permafrost")
    assert row["ES-RIO"] is None and row["ES-RIO__type"] == "missing"


def test_compare_validation(client):
    assert client.get("/api/compare", params={"ids": ""}).status_code == 422
    assert client.get("/api/compare", params={"ids": "A,B,C,D,E,F,G"}).status_code == 422
    assert client.get("/api/compare", params={"ids": "CA-HAU,NOPE"}).status_code == 404


def test_compare_csv_export(client):
    r = client.get("/api/export/compare.csv", params={"ids": "CA-HAU,AQ-MDV", "ref_id": "moon-shackleton"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.splitlines()
    assert lines[0].startswith("# SYNTHETIC")
    assert sum(1 for l in lines if l.startswith("CA-HAU")) == 8


def test_recommend_examples(client):
    cases = {
        "Find Earth environments suitable for testing lunar polar rovers.": ("moon", "rover_mobility"),
        "Identify basaltic terrain analogous to Martian volcanic plains.": ("mars", None),
        "Compare Earth sites for Mars drilling equipment testing.": ("mars", "drilling"),
        "Find polar desert environments relevant to lunar resource prospecting.": ("moon", "isru"),
        "Identify cave environments suitable for subsurface robotics tests.": (None, "cave_exploration"),
    }
    for q, (body, obj) in cases.items():
        d = client.post("/api/recommend", json={"query": q}).json()
        it = d["interpretation"]
        if body:
            assert it["body"] == body, q
        if obj:
            assert it["objective"] == obj, q
        assert d["results"], q
        assert d["cannot_replicate_on_earth"], q
        for res in d["results"]:
            assert res["why"] and res["score"] is not None
    d = client.post("/api/recommend", json={"query": "Identify basaltic terrain analogous to Martian volcanic plains."}).json()
    assert d["interpretation"]["ref_id"] == "mars-elysium-planitia"
    assert all("basaltic_volcanic" in r["analog_types"] for r in d["results"])
    d = client.post("/api/recommend", json={"query": "cave robotics", "body": "mars"}).json()
    assert d["results"][0]["site_id"] in {"US-LBN", "ES-LAN"}


def test_recommend_only_returns_known_sites(client, store):
    d = client.post("/api/recommend", json={"query": "anything at all on mars", "top_k": 50}).json()
    assert {r["site_id"] for r in d["results"]} <= set(store.sites)


def test_recommend_validation(client):
    assert client.post("/api/recommend", json={"query": "x" * 600}).status_code == 422
    assert client.post("/api/recommend", json={"query": "x", "body": "venus"}).status_code == 422
    assert client.post("/api/recommend", json={"query": "x", "ref_id": "nope"}).status_code == 422
    assert client.post("/api/recommend", json={"query": "x", "top_k": 0}).status_code == 422
