"""Scoring consistency, missing-data honesty, weights."""
import pytest

from app.scoring import ScoringError, effective_weights, parse_weights, rank_sites, score_site


def ref(store, rid="moon-shackleton"):
    return store.references[rid]


def test_score_bounds_and_range(store):
    for r in rank_sites(store, ref(store), "general", body_relevant_only=False):
        assert 0 <= r.score_low <= r.score_high <= 100
        if r.score is not None:
            assert r.score_low - 0.05 <= r.score <= r.score_high + 0.05
        assert 0 <= r.completeness <= 1 and 0 <= r.confidence <= 1


def test_complete_site_has_degenerate_range(store):
    r = score_site(store, store.sites["CA-HAU"], ref(store), "general")
    assert r.completeness == 1.0 and r.score_low == r.score_high == r.score


def test_manual_weighted_mean(store):
    rf = ref(store)
    w = effective_weights(store.scoring, rf, "general")
    feats = store.features["CA-HAU"]
    expected = 100 * sum(w[c] * feats[c].value / 5 for c in w) / sum(w.values())
    assert score_site(store, store.sites["CA-HAU"], rf, "general").score == pytest.approx(expected, abs=0.05)


def test_contributions_sum_to_score(store):
    r = score_site(store, store.sites["AQ-MDV"], ref(store, "mars-jezero"), "drilling")
    assert sum(b.contribution for b in r.breakdown if b.contribution is not None) == pytest.approx(r.score, abs=0.1)


def test_missing_values_reduce_completeness_and_are_not_imputed(store):
    r = score_site(store, store.sites["ES-RIO"], ref(store, "mars-jezero"), "general")
    assert r.completeness < 1
    assert set(r.missing_criteria) == {"ice_permafrost", "subsurface_access"}
    assert r.score_low < r.score_high


def test_insufficient_evidence_has_no_point_score(store):
    ranked = rank_sites(store, ref(store, "mars-arsia-mons"), "cave_exploration")
    insufficient = [r for r in ranked if r.status == "insufficient_evidence"]
    assert insufficient, "fixture should exercise the insufficient-evidence path"
    for r in insufficient:
        assert r.score is None and r.rank is None and r.completeness < store.scoring.min_completeness
    # unranked sites are listed after ranked ones
    statuses = [r.status for r in ranked]
    assert statuses.index("insufficient_evidence") > max(i for i, s in enumerate(statuses) if s == "scored")


def test_ranks_are_contiguous_and_sorted(store):
    ranked = [r for r in rank_sites(store, ref(store), "isru") if r.rank]
    assert [r.rank for r in ranked] == list(range(1, len(ranked) + 1))
    assert all(a.score >= b.score for a, b in zip(ranked, ranked[1:]))


def test_matches_published_rankings_fixture(store):
    pub = {(p.ref_id, p.objective, p.site_id): p for p in store.published_rankings}
    for rid, rf in store.references.items():
        for o in store.scoring.objectives:
            for r in rank_sites(store, rf, o.id):
                p = pub[(rid, o.id, r.site_id)]
                assert p.score == r.score and p.rank == r.rank


def test_user_weight_zero_removes_criterion(store):
    rf = ref(store)
    base = score_site(store, store.sites["US-LBN"], rf, "general")
    zero = score_site(store, store.sites["US-LBN"], rf, "general", {"illumination": 0})
    assert next(b for b in zero.breakdown if b.criterion_id == "illumination").effective_weight == 0
    assert zero.score != base.score


def test_increasing_weight_moves_score_toward_that_value(store):
    rf = ref(store)
    s = store.sites["CA-HAU"]  # illumination 5/5 => more weight should raise the score
    assert score_site(store, s, rf, "general", {"illumination": 2}).score > score_site(store, s, rf, "general").score


def test_objective_changes_ranking(store):
    rf = ref(store, "moon-marius-hills")
    top_cave = rank_sites(store, rf, "cave_exploration")[0].site_id
    assert top_cave in {"US-LBN", "ES-LAN"}


def test_parse_weights_validation():
    assert parse_weights("terrain:1.5, geology:0", {"terrain", "geology"}) == {"terrain": 1.5, "geology": 0.0}
    for bad in ["terrain", "nope:1", "terrain:x", "terrain:9"]:
        with pytest.raises(ScoringError):
            parse_weights(bad, {"terrain", "geology"})


def test_unknown_objective(store):
    with pytest.raises(ScoringError):
        score_site(store, store.sites["CA-HAU"], ref(store), "teleportation")
