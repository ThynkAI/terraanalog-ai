"""Independently recompute every published ranking row with the app's scoring engine.

Usage: python scripts/verify_published.py [DATA_DIR] [--json OUT]
Reports abs score difference (vs the engine's unrounded score and its 1-dp display value), completeness difference and rank agreement.
Exit code 1 if max |diff| (unrounded) > 0.05 or any row cannot be scored.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
args = [a for a in sys.argv[1:] if not a.startswith("--")]
out_path = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
if out_path in args:
    args.remove(out_path)
os.environ["TERRA_DATA_DIR"] = str(Path(args[0]).resolve() if args else ROOT / "data" / "research")
sys.path.insert(0, str(ROOT / "backend"))

from app.loader import load_store  # noqa: E402
from app.scoring import effective_weights, rank_sites  # noqa: E402

st = load_store(Path(os.environ["TERRA_DATA_DIR"]))
cfg = st.scoring
smin, span = cfg.scale_min, cfg.scale_max - cfg.scale_min


def raw_score(site_id, ref, obj):
    w = effective_weights(cfg, ref, obj)
    feats = st.features.get(site_id, {})
    num = den = tot = 0.0
    for cid, wc in w.items():
        tot += wc
        fv = feats.get(cid)
        if fv is None or fv.value is None or wc <= 0:
            continue
        num += wc * (fv.value - smin) / span
        den += wc
    return (100 * num / den if den else None), (den / tot if tot else None)


rows, problems = [], []
ranks = {}
for key in {(p.ref_id, p.objective) for p in st.published_rankings}:
    ref = st.references.get(key[0])
    if ref is None:
        continue
    for r in rank_sites(st, ref, key[1], body_relevant_only=False):
        ranks[(key[0], key[1], r.site_id)] = (r.rank, r.score)

for p in st.published_rankings:
    ref = st.references.get(p.ref_id)
    if ref is None:
        problems.append(f"{p.ref_id}/{p.objective}/{p.site_id}: unknown reference")
        continue
    s, comp = raw_score(p.site_id, ref, p.objective)
    rank, disp = ranks.get((p.ref_id, p.objective, p.site_id), (None, None))
    if s is None or p.score is None:
        problems.append(f"{p.ref_id}/{p.objective}/{p.site_id}: published={p.score} engine={s}")
        continue
    rows.append({"ref_id": p.ref_id, "objective": p.objective, "site_id": p.site_id, "published": p.score, "engine_raw": round(s, 4),
                 "engine_display": disp, "abs_diff": abs(s - p.score), "abs_diff_display": abs(disp - p.score) if disp is not None else None,
                 "completeness_pub": p.completeness, "completeness_engine": round(comp, 4),
                 "rank_pub": p.rank, "rank_engine": rank})

d = [r["abs_diff"] for r in rows]
dd = [r["abs_diff_display"] for r in rows if r["abs_diff_display"] is not None]
cd = [abs(r["completeness_pub"] - r["completeness_engine"]) for r in rows if r["completeness_pub"] is not None]
rank_mismatch = [r for r in rows if r["rank_pub"] is not None and r["rank_engine"] != r["rank_pub"]]
worst = sorted(rows, key=lambda r: -r["abs_diff"])[:5]
summary = {
    "data_dir": os.environ["TERRA_DATA_DIR"].replace(str(ROOT) + "/", ""),
    "rows_published": len(st.published_rankings), "rows_compared": len(rows), "rows_unscorable": len(problems),
    "score_abs_diff_unrounded": {"max": round(max(d), 4), "mean": round(statistics.mean(d), 4), "median": round(statistics.median(d), 4),
                                 "within_0.05": sum(x <= 0.05 + 1e-9 for x in d), "within_0.01": sum(x <= 0.01 + 1e-9 for x in d)},
    "score_abs_diff_display_1dp": {"max": round(max(dd), 4), "mean": round(statistics.mean(dd), 4), "exact": sum(x < 1e-9 for x in dd)},
    "completeness_abs_diff": {"max": round(max(cd), 4) if cd else None, "mean": round(statistics.mean(cd), 4) if cd else None},
    "rank_agreement": {"compared": sum(1 for r in rows if r["rank_pub"] is not None), "mismatches": len(rank_mismatch),
                       "examples": [{k: r[k] for k in ("ref_id", "objective", "site_id", "published", "engine_raw", "rank_pub", "rank_engine")} for r in rank_mismatch[:10]]},
    "pairs": len({(r["ref_id"], r["objective"]) for r in rows}),
    "worst_rows": [{k: r[k] for k in ("ref_id", "objective", "site_id", "published", "engine_raw", "abs_diff")} for r in worst],
    "problems": problems,
}
print(json.dumps(summary, indent=2))
if out_path:
    Path(out_path).write_text(json.dumps(summary, indent=2) + "\n")
sys.exit(1 if problems or max(d) > 0.05 + 1e-9 else 0)
