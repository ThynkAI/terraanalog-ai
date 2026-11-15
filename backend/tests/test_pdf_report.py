"""Generated PDF Site Comparison Report."""
import io
import re

from pypdf import PdfReader


def _text(pdf: bytes) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)


def test_pdf_report_is_valid_pdf(client):
    r = client.get("/api/export/compare.pdf", params={"ids": "CA-HAU,AQ-MDV", "ref_id": "moon-shackleton", "objective": "general"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"] and r.headers["content-disposition"].endswith('.pdf"')
    assert r.content.startswith(b"%PDF-") and r.content.rstrip().endswith(b"%%EOF")
    assert len(r.content) > 3000
    assert len(re.findall(rb"/Type\s*/Page[^s]", r.content)) >= 2


def test_pdf_report_contents_match_compare(client):
    params = {"ids": "CA-HAU,AQ-MDV", "ref_id": "moon-shackleton", "objective": "general"}
    txt = _text(client.get("/api/export/compare.pdf", params=params).content)
    cmp = client.get("/api/compare", params=params).json()
    assert "Site Comparison Report" in txt
    assert "SYNTHETIC FIXTURE DATA" in txt
    for s in cmp["sites"]:
        assert s["site_id"] in txt
        if s["result"]["score"] is not None:
            assert f'{s["result"]["score"]:.1f}' in txt


def test_pdf_report_shows_missing_not_imputed(client):
    txt = _text(client.get("/api/export/compare.pdf", params={"ids": "ES-RIO,CA-HAU", "ref_id": "mars-jezero"}).content)
    assert "missing" in txt


def test_pdf_report_validation(client):
    assert client.get("/api/export/compare.pdf", params={"ids": "NOPE"}).status_code == 404
    assert client.get("/api/export/compare.pdf", params={"ids": "CA-HAU", "ref_id": "bad id!"}).status_code == 422
    assert client.get("/api/export/compare.pdf").status_code == 422
    assert client.get("/api/export/compare.pdf", params={"ids": "CA-HAU", "weights": "terrain:99"}).status_code == 422
