#!/usr/bin/env python3
"""Validate a data directory against the TerraAnalog data contract and print an ID-consistency report.
Usage: python scripts/validate_data.py [DATA_DIR]   (exit code 1 if any errors)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.loader import load_store  # noqa: E402

d = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "fixtures"
st = load_store(d)
status = st.data_status()
print(json.dumps({k: status[k] for k in ("label", "files", "counts", "value_types", "error_count", "warning_count")}, indent=2))
for i in status["issues"]:
    print(f"[{i['level']}] {i['file']}: {i['message']}")
sys.exit(1 if status["error_count"] else 0)
