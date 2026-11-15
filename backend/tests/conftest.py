import shutil
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
FIXTURES = BACKEND.parent / "data" / "fixtures"


@pytest.fixture()
def fixture_dir() -> Path:
    return FIXTURES


@pytest.fixture()
def tmp_data(tmp_path, monkeypatch) -> Path:
    """A writable copy of the fixtures, wired into the API via TERRA_DATA_DIR."""
    d = tmp_path / "data"
    shutil.copytree(FIXTURES, d)
    monkeypatch.setenv("TERRA_DATA_DIR", str(d))
    return d


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("TERRA_DATA_DIR", str(FIXTURES))
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture()
def store():
    from app.loader import load_store
    return load_store(FIXTURES)
