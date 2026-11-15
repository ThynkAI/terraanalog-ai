# Drop-in folder for the research bot's (Bot 1) data

Copy these files here (any subset; missing ones degrade gracefully):

earth_analog_sites.geojson · planetary_reference_sites.geojson · analog_features.csv · analog_rankings.csv ·
dataset_catalog.csv · site_evidence.json · scoring_config.json · scientific_methodology.md · source_references.md

Then run the API with `TERRA_DATA_DIR=./data/real`, or validate first:

    .venv/bin/python scripts/validate_data.py data/real

See docs/DATA_INTEGRATION.md for the exact schema. Files in this folder are git-ignored.
