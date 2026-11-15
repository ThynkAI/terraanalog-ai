"""Reviewed narratives with live, same-reference benchmark comparisons.

No new scientific measurement is introduced. Published evidence-strict summaries use
best-of-reference profile rankings and must not be confused with the fixed-reference live scores.
"""
import json
from .scoring import rank_sites


def build_case_studies(store):
    root = store.data_dir / 'supplementary'
    briefs = root / 'case_study_briefs.json'
    measurements = root / 'case_study_measurements.json'
    if store.is_synthetic or not briefs.exists() or not measurements.exists():
        return {'available': False, 'reason': 'Reviewed case studies require the research dataset and its supplementary files.', 'cases': []}
    doc = json.loads(briefs.read_text())
    values = json.loads(measurements.read_text())['cases']
    output = []
    for brief in doc['cases']:
        sid, rid, obj = brief['site_id'], brief['ref_id'], brief['objective']
        if sid not in store.sites or rid not in store.references or not store.scoring:
            continue
        reference = store.references[rid]
        normal = {r.site_id: r for r in rank_sites(store, reference, obj)}
        stressed = {r.site_id: r for r in rank_sites(store, reference, obj, brief['stress_weights'])}
        objective = next(o for o in store.scoring.objectives if o.id == obj)
        benchmark_ids = [i for i, s in store.sites.items() if getattr(s, 'group', None) == 'baseline']
        ids = [sid, *[i for i in benchmark_ids if i != sid]]
        comparisons = []
        for i in ids:
            if i in normal:
                comparisons.append({'site_id': i, 'name': store.sites[i].name, 'candidate': i == sid,
                                    'result': normal[i].as_dict(), 'stress_result': stressed[i].as_dict()})
        strict = (store.sensitivity_summary.get('strict_evidence_variant') or {}).get('profiles', {}).get(obj)
        strict_view = None
        if strict:
            strict_view = {**strict, 'top5_base_names': [store.sites[i].name for i in strict['top5_base']],
                           'top5_strict_names': [store.sites[i].name for i in strict['top5_strict']],
                           'scope': "Published profile ranking: each site keeps its best score across the profile's published references. These are not fixed-reference scores or a live strict recalculation.",
                           'references': objective.published_references,
                           'method': (store.sensitivity_summary.get('strict_evidence_variant') or {}).get('method')}
        selected_score = normal[sid].score
        benchmark_scores = [normal[i].score for i in benchmark_ids if i in normal and normal[i].score is not None]
        output.append({**brief, 'site': store.sites[sid].model_dump(), 'reference': reference.model_dump(),
                       'objective_label': objective.label,
                       'exploratory_reference': bool(objective.published_references and rid not in objective.published_references),
                       'measurements': values[brief['id']], 'comparisons': comparisons,
                       'advantage_vs_best_benchmark': round(selected_score - max(benchmark_scores), 1) if selected_score is not None and benchmark_scores else None,
                       'strict_evidence': strict_view})
    return {**{k: v for k, v in doc.items() if k != 'cases'}, 'available': True,
            'scoring_note': 'Live scores use one fixed reference for all four sites. Ranks are among all catalog sites; scores are relative proxies, not probabilities or field-validation results.',
            'cases': output}
