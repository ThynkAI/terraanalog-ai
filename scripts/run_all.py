"""Run the full TerraAnalog AI pipeline in order. Steps 01-03 hit the network (cached in data/raw/)."""
import subprocess, sys
from pathlib import Path
here = Path(__file__).parent
steps = ["01_retrieve_literature.py", "02_retrieve_earth_data.py", "03_retrieve_planetary_data.py", "04_build_features.py",
         "05_score.py", "06_analytics.py", "07_dataset_catalog.py", "08_build_geojson.py", "10_write_references.py", "11_data_contract.py", "09_validate.py", "12_results_snapshot.py"]
skip_net = "--offline" in sys.argv
for s in steps:
    if skip_net and s[:2] in ("01", "02", "03"):
        continue
    print(f"=== {s}", flush=True)
    subprocess.run([sys.executable, str(here / s)], check=True, cwd=here.parent)
