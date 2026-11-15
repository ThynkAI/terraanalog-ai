"""Export only existing regional measurements for the reviewed cases; never retrieve or invent data.
Run from any directory: python app/scripts/build_case_measurements.py
The scoring contract remains unchanged. Source CSV cells stay null when absent.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'app/data/research/supplementary'

def rows(name, key):
    with (ROOT / 'outputs' / name).open() as f:
        return {r[key]: r for r in csv.DictReader(f)}

def number(value):
    return float(value) if value not in ('', None) else None

def build():
    earth = rows('analog_features.csv', 'site_id')
    planet = rows('planetary_features.csv', 'ref_id')
    cases = json.loads((OUT / 'case_study_briefs.json').read_text())['cases']
    result = {}
    for case in cases:
        e, p = earth[case['site_id']], planet[case['ref_id']]
        lunar = p['body'] == 'Moon'
        prefix = 't90m_r5km' if lunar else 't450m_r15km'
        result[case['id']] = {
            'source_files': ['outputs/analog_features.csv', 'outputs/planetary_features.csv'],
            'sampling_note': 'Regional sampling windows around catalog reference points; not a cave survey, traverse map or legal site boundary.',
            'earth_native_dem_m': 30,
            'planet_dem_product': p['dem_product'],
            'comparison_grid_m': 90 if lunar else 450,
            'radius_m': 5000 if lunar else 15000,
            'earth_valid_fraction': number(e.get(prefix + '_valid_fraction')),
            'metrics': [
                {'label': 'Regional median slope', 'unit': 'degrees', 'earth': number(e[prefix + '_slope_median_deg']), 'planet': number(p['ref_slope_median_deg']), 'provenance': 'Derived from Copernicus DEM and LOLA/MOLA at the stated comparison scale.'},
                {'label': 'Regional 90th-percentile slope', 'unit': 'degrees', 'earth': number(e[prefix + '_slope_p90_deg']), 'planet': number(p['ref_slope_p90_deg']), 'provenance': 'Derived; does not resolve wheel-scale hazards.'},
                {'label': 'Median terrain ruggedness (TRI)', 'unit': 'm', 'earth': number(e[prefix + '_tri_median_m']), 'planet': number(p['ref_tri_median_m']), 'provenance': 'Derived; depends on DEM resolution and resampling.'},
                {'label': 'Thermal scoring proxy', 'unit': 'K', 'earth': number(e['temperature_K']), 'planet': number(p['temperature_K']), 'provenance': 'Earth: modeled annual air temperature. Planet: ' + p['temperature_provenance'] + '; different physical/temporal support. Not a direct temperature equivalence.'},
                {'label': 'Fine sediment fraction', 'unit': '0–1', 'earth': number(e['fine_fraction']), 'planet': number(p['fine_fraction']), 'provenance': 'Earth: SoilGrids modeled surface texture; planetary literature proxy if available. Not a cave-floor measurement.'}
            ],
            'earth_precipitation_mm_yr': number(e['era5_precip_mm_yr']),
            'earth_permafrost_probability': number(e['permafrost_prob']),
            'earth_permafrost_source': e['permafrost_source']
        }
    return {'method': 'Deterministic subset of committed research CSVs. No new measurements; no missing-value imputation.', 'cases': result}

if __name__ == '__main__':
    (OUT / 'case_study_measurements.json').write_text(json.dumps(build(), indent=2, ensure_ascii=False) + '\n')
