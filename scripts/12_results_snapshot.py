"""Step 12 - refresh the results snapshot block in README.md and HANDOFF_GROK_BOT_2.md from outputs (no hand-typed numbers)."""
import csv, json, re
from common import *

def snapshot():
    rows = list(csv.DictReader(open(OUTPUTS / "analog_rankings.csv", encoding="utf-8")))
    sens = load_json(OUTPUTS / "sensitivity_summary.json")
    val = load_json(OUTPUTS / "validation_results.json") if (OUTPUTS / "validation_results.json").exists() else None
    L = ["| Profile | #1 (score, completeness) | #2 | #3 | MC mean Spearman |", "|---|---|---|---|---|"]
    for p in scoring_config()["mission_profiles"]:
        top = sorted((r for r in rows if r["mission_profile"] == p), key=lambda r: int(r["fidelity_rank"]))[:3]
        cell = lambda r: f"{r['site_id']} {r['name'].split(',')[0].split(' (')[0][:34]} ({float(r['fidelity_score']):.1f}, {float(r['evidence_completeness']):.2f})"
        rho = (sens.get("profiles", sens).get(p) or {}).get("mc_spearman_mean")
        L.append(f"| {p} | " + " | ".join(cell(r) for r in top) + f" | {rho if rho is None else round(rho, 3)} |")
    if val:
        L += ["", f"Validation: **{sum(1 for c in val['checks'] if c.get('pass') or c.get('passed') or c.get('result') == 'PASS')}/{len(val['checks'])} checks passed** (see `outputs/validation_report.md`)."]
    L += ["", "Scores are relative, profile-specific fidelity (0-100), not planetary equivalence. Completeness = share of profile weight with data."]
    return "\n".join(L)

def main():
    block = snapshot()
    for fn in ("README.md", "HANDOFF_GROK_BOT_2.md"):
        p = ROOT / fn
        if p.exists():
            s = p.read_text(encoding="utf-8")
            s = re.sub(r"<!-- RESULTS:START -->.*?<!-- RESULTS:END -->", "<!-- RESULTS:START -->\n" + block + "\n<!-- RESULTS:END -->", s, flags=re.S)
            p.write_text(s, encoding="utf-8")
    print("results snapshot refreshed")

if __name__ == "__main__":
    main()
