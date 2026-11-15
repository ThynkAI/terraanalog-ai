"""Discovery uses the curated labels without altering fidelity scores or implying novelty."""
import pytest


@pytest.mark.parametrize("group", ["baseline", "established", "candidate"])
def test_catalog_group_preserves_scores_and_full_catalog_rank(research_client, group):
    params = {"ref_id": "MOON-REF-01", "objective": "MOON_ROVER_MOBILITY"}
    all_sites = research_client.get("/api/sites", params=params).json()["sites"]
    expected = [s for s in all_sites if s.get("group") == group]
    filtered = research_client.get("/api/sites", params={**params, "catalog_group": group})
    assert filtered.status_code == 200
    assert filtered.json()["sites"] == expected
    assert filtered.json()["count"] == len(expected) > 0


def test_catalog_group_rejects_unsupported_validation_claim(research_client):
    assert research_client.get("/api/sites?catalog_group=validated").status_code == 422


def test_candidate_filter_combines_with_geography(research_client):
    sites = research_client.get("/api/sites?catalog_group=candidate&q=Iceland").json()["sites"]
    assert [s["site_id"] for s in sites] == ["EA-006"]
