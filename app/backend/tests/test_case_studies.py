"""Case studies cannot invent metrics, ranks, strict scores, or novelty claims."""
import importlib.util
import json
from pathlib import Path
import pytest
from app.scoring import rank_sites

ROOT = Path(__file__).resolve().parents[3]


def test_cases_are_research_only(research_client):
    assert research_client.get('/api/case-studies').json()['available'] is True


def test_fixture_dataset_has_no_research_cases(client):
    data = client.get('/api/case-studies').json()
    assert data['available'] is False and data['cases'] == []


def test_measurements_are_reproducible_subsets_of_source_csvs():
    spec = importlib.util.spec_from_file_location('case_export', ROOT / 'app/scripts/build_case_measurements.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    saved = json.loads((ROOT / 'app/data/research/supplementary/case_study_measurements.json').read_text())
    assert module.build() == saved
    holuhraun = saved['cases']['holuhraun-mobility']
    assert holuhraun['comparison_grid_m'] == 450 and holuhraun['radius_m'] == 15000
    assert saved['cases']['undara-cave-robotics']['metrics'][0]['earth'] == 1.2003


@pytest.mark.parametrize('index', range(3))
def test_case_benchmarks_and_stress_tests_use_same_reference(research_client, research_store, index):
    case = research_client.get('/api/case-studies').json()['cases'][index]
    ref = research_store.references[case['ref_id']]
    baseline = {r.site_id: r.as_dict() for r in rank_sites(research_store, ref, case['objective'])}
    stressed = {r.site_id: r.as_dict() for r in rank_sites(research_store, ref, case['objective'], case['stress_weights'])}
    assert len(case['comparisons']) == 4
    for row in case['comparisons']:
        assert row['result'] == baseline[row['site_id']]
        assert row['stress_result'] == stressed[row['site_id']]
    original = research_store.sensitivity_summary['strict_evidence_variant']['profiles'][case['objective']]
    for key, value in original.items():
        assert case['strict_evidence'][key] == value
    assert 'not fixed-reference scores' in case['strict_evidence']['scope']
    assert 'strict_score' not in case
    assert all(s['url'].startswith('https://') for s in case['sources'])


def test_no_new_discovery_or_direct_cave_temperature_is_claimed(research_client):
    cases = research_client.get('/api/case-studies').json()['cases']
    assert cases[0]['novelty_status'] == 'Previously published analog'
    assert cases[0]['exploratory_reference'] is True
    assert cases[1]['stress_weights'] == {'thermal': 0}
    assert any('not a measured cave temperature' in text for text in cases[1]['limits'])
    assert any(m['planet'] is None for m in cases[0]['measurements']['metrics'])
