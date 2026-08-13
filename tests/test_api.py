"""
test_api.py - hits the FastAPI backend through TestClient with the same real
sample set used to validate engine/ directly (see test_reconciliation_units.py
and this project's regression sweeps). This is a serialization-correctness
check, not a re-test of extraction logic - it confirms the HTTP layer doesn't
lose or corrupt anything engine.statement.analyze() already got right.

Skips cleanly if BANK_STMT_TEST_DIR isn't set, same pattern as the rest of
this project's regression tests.
"""

import glob
import os

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

_SAMPLE_DIR = os.environ.get("BANK_STMT_TEST_DIR", "Sample Data")
_SAMPLES = glob.glob(os.path.join(_SAMPLE_DIR, "**", "*.pdf"), recursive=True) if os.path.isdir(_SAMPLE_DIR) else []


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_analyze_rejects_non_pdf():
    resp = client.post("/api/analyze", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_code"] == "NOT_A_PDF"


@pytest.mark.skipif(not _SAMPLES, reason="No sample statements found (set BANK_STMT_TEST_DIR)")
@pytest.mark.parametrize("path", _SAMPLES, ids=[os.path.basename(p) for p in _SAMPLES])
def test_analyze_matches_direct_call(path):
    from engine.statement import analyze as direct_analyze

    with open(path, "rb") as fh:
        file_bytes = fh.read()

    direct = direct_analyze(file_bytes)

    with open(path, "rb") as fh:
        resp = client.post("/api/analyze", files={"file": (os.path.basename(path), fh, "application/pdf")})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["bank_name"] == direct.bank_name
    assert body["summary"]["transaction_count"] == direct.summary["transaction_count"]
    assert body["summary"]["counts"] == direct.summary["counts"]
    assert len(body["transactions"]) == len(direct.transactions)
    assert body["score"]["score"] == pytest.approx(direct.score["score"])


@pytest.mark.skipif(not _SAMPLES, reason="No sample statements found (set BANK_STMT_TEST_DIR)")
def test_export_excel_returns_xlsx():
    path = _SAMPLES[0]
    with open(path, "rb") as fh:
        resp = client.post("/api/analyze/excel", files={"file": (os.path.basename(path), fh, "application/pdf")})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment; filename=" in resp.headers["content-disposition"]
    assert len(resp.content) > 1000
