"""Final sanity audit of the committed research contract. No network or raw-raster claims.
Run: python app/scripts/submission_sanity.py [--json OUTPUT]
"""
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
sys.path.insert(0, str(APP / 'backend'))
from app.config import RESEARCH_DATA_DIR, CONTRACT_FILES
from app.loader import load_store
from app.scoring import rank_sites, effective_weights
from app.case_studies import build_case_studies


def audit():
    st = load_store(RESEARCH_DATA_DIR)
    cfg = st.scoring
    checks = []
    def check(name, passed, details):
        checks.append({'name': name, 'passed': bool(passed), 'details': details})
    status = st.data_status()
    check('contract_valid', status['error_count'] == 0 and status['warning_count'] == 0, {'errors': status['error_count'], 'warnings': status['warning_count']})
    check('research_not_synthetic', not st.is_synthetic, status['label'])
    check('catalog_counts', len(st.sites) == 28 and len(st.references) == 14, status['counts'])
    check('mission_profiles', len([o for o in cfg.objectives if o.id != 'general']) == 10 and any(o.id == 'general' for o in cfg.objectives), '10 specialized profiles plus general mode')
    values = [v for site in st.features.values() for v in site.values()]
    counts = Counter(v.value_type for v in values)
    check('feature_counts', len(values) == 4340 and counts['missing'] == 378 and counts['synthetic'] == 0, dict(counts))
    check('missing_values_preserved', all((v.value is None) == (v.value_type == 'missing') for v in values), 'Missing is null; known values are never marked missing.')
    check('finite_feature_ranges', all(v.value is None or (math.isfinite(v.value) and cfg.scale_min <= v.value <= cfg.scale_max) for v in values), [cfg.scale_min, cfg.scale_max])
    check('earth_coordinate_ranges', all(-90 <= s.lat <= 90 and -180 <= s.lon <= 180 for s in st.sites.values()), 'WGS84 latitude/longitude ranges')
    check('planet_coordinate_conventions', all(-90 <= r.lat <= 90 and -180 <= r.lon_east <= 180 and 'WGS84' not in r.coordinate_system for r in st.references.values()), 'Body-fixed planetocentric coordinates, east-positive longitude')
    earth = json.loads((RESEARCH_DATA_DIR / 'earth_analog_sites.geojson').read_text())['features']
    check('earth_geometry_agrees_with_properties', all(f['geometry']['coordinates'] == [st.sites[f['properties']['site_id']].lon, st.sites[f['properties']['site_id']].lat] for f in earth), 'Geometry order is longitude, latitude.')
    groups = Counter(getattr(s, 'group', None) for s in st.sites.values())
    check('catalog_labels', groups == {'baseline': 3, 'established': 10, 'candidate': 15}, dict(groups))
    problems, pairs, total = [], 0, 0
    for ref in st.references.values():
        for objective in cfg.objectives:
            if objective.body_key not in (None, ref.body):
                continue
            pairs += 1
            weights = effective_weights(cfg, ref, objective.id)
            if weights.get('operational_suitability', 0) != 0:
                problems.append('operational score leaked into fidelity')
            results = rank_sites(st, ref, objective.id)
            total += len(results)
            ranks = [r.rank for r in results if r.rank is not None]
            if ranks != list(range(1, len(ranks) + 1)):
                problems.append('non-contiguous ranking')
            for r in results:
                if not (0 <= r.completeness <= 1 and 0 <= r.confidence <= 1 and 0 <= r.score_low <= r.score_high <= 100):
                    problems.append(f'{r.site_id}: invalid bounds/confidence')
                if r.score is not None and not (r.score_low - .11 <= r.score <= r.score_high + .11):
                    problems.append(f'{r.site_id}: score outside missing-data bounds')
    check('all_compatible_rankings', not problems, {'reference_objective_pairs': pairs, 'site_scores_checked': total, 'issues': problems[:10]})
    cases = build_case_studies(st)['cases']
    check('three_reviewed_cases', len(cases) == 3, [c['id'] for c in cases])
    check('same_reference_benchmarks', all(len(c['comparisons']) == 4 and all(r['result']['ref_id'] == c['ref_id'] and r['stress_result']['ref_id'] == c['ref_id'] for r in c['comparisons']) for c in cases), 'Case site and three benchmarks share the same target and objective.')
    check('case_sources_and_novelty', all(c['sources'] and 'discover' not in c['novelty_status'].lower() and all(s['url'].startswith('https://') for s in c['sources']) for c in cases), 'Novelty is bounded and sources remain attributed.')
    spec = importlib.util.spec_from_file_location('measurements', APP / 'scripts/build_case_measurements.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    saved = json.loads((RESEARCH_DATA_DIR / 'supplementary/case_study_measurements.json').read_text())
    check('measurement_export_reproduces', module.build() == saved, 'Deterministic export of committed research CSV values, preserving nulls.')
    check('image_credits', all(not s.imagery or (s.imagery.credit and s.imagery.license and s.imagery.attribution_page) for s in st.sites.values()), 'Each catalog image has author/license attribution and source page.')
    fingerprints = {str((RESEARCH_DATA_DIR / f).relative_to(ROOT)): hashlib.sha256((RESEARCH_DATA_DIR / f).read_bytes()).hexdigest() for f in CONTRACT_FILES}
    return {'scope': 'Committed contract and derived outputs; no new field validation or raw-raster retrieval.', 'checks': checks, 'passed': sum(c['passed'] for c in checks), 'failed': sum(not c['passed'] for c in checks), 'input_sha256': fingerprints}

if __name__ == '__main__':
    result = audit()
    if '--json' in sys.argv:
        path = Path(sys.argv[sys.argv.index('--json') + 1]); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'input_sha256'}, indent=2))
    sys.exit(bool(result['failed']))
