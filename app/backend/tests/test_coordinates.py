"""Geospatial coordinate correctness (Earth WGS84 vs planetary IAU conventions)."""
import json
import math

import pytest

from app.models import PlanetaryReference

GAZETTEER = {  # values verified against planetarynames.wr.usgs.gov on 2026-11-15
    "moon-shackleton": (-89.67, 129.78), "moon-malapert": (-85.0, 11.4), "moon-mare-tranquillitatis": (8.35, 30.83),
    "mars-jezero": (18.41, 77.69), "mars-gale": (-5.37, 137.81), "mars-elysium-planitia": (2.98, 154.74),
    "mars-arsia-mons": (-8.26, -120.09),
}


def test_earth_sites_in_wgs84_range_and_lon_lat_order(fixture_dir, store):
    gj = json.loads((fixture_dir / "earth_analog_sites.geojson").read_text())
    for f in gj["features"]:
        lon, lat = f["geometry"]["coordinates"]
        assert -180 <= lon <= 180 and -90 <= lat <= 90
    assert store.sites["CA-HAU"].lat > 70 and store.sites["CA-HAU"].lon < -80  # Devon Island: high N, west
    assert store.sites["AQ-MDV"].lat < -70  # Antarctica
    assert store.sites["CL-ATA"].lon < -60  # South America west


def test_planetary_reference_ranges(store):
    for r in store.references.values():
        assert -90 <= r.lat <= 90
        assert -180 <= r.lon_east <= 180
        assert r.lon_east_360 is not None and 0 <= r.lon_east_360 < 360


@pytest.mark.parametrize("ref_id,expected", list(GAZETTEER.items()))
def test_gazetteer_values(store, ref_id, expected):
    r = store.references[ref_id]
    assert (r.lat, r.lon_east) == pytest.approx(expected, abs=1e-6)


def test_body_radii_iau_not_earth(store):
    for r in store.references.values():
        assert r.body_radius_km == {"moon": 1737.4, "mars": 3389.5}[r.body]
        assert abs(r.body_radius_km - 6378.137) > 1000  # never the WGS84 semi-major axis


def test_east_positive_0_360_conversion(store):
    assert store.references["mars-arsia-mons"].lon_east_360 == pytest.approx(239.91)
    assert store.references["mars-meridiani-planum"].lon_east_360 == pytest.approx(356.86)


def test_inconsistent_longitudes_rejected():
    with pytest.raises(Exception):
        PlanetaryReference(ref_id="x", body="mars", name="x", lat=0, lon_east=10, lon_east_360=20, body_radius_km=3389.5)


def test_south_polar_refs_are_south_polar(store):
    for rid in ["moon-shackleton", "moon-malapert", "moon-de-gerlache", "moon-south-pole-region"]:
        assert store.references[rid].lat <= -84.9


def test_api_haversine_earth_only(client):
    # near-search around Flagstaff should find SF Volcanic Field and Meteor Crater but not Iceland
    r = client.get("/api/sites", params={"near": "35.2,-111.6", "radius_km": 100, "sort": "distance", "order": "asc"}).json()
    ids = [s["site_id"] for s in r["sites"]]
    assert ids[0] == "US-SFV" and "US-MET" in ids and "IS-ASK" not in ids
    d = r["sites"][0]["distance_km"]
    assert 0 < d < 30
    assert math.isfinite(d)
