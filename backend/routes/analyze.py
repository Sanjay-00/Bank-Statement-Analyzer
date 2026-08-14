"""
routes/analyze.py - POST /api/analyze.

Wraps engine.statement.analyze() behind an HTTP endpoint. All the real work
(PDF parsing, reconciliation, every signal) already happens inside engine/ -
this file's job is purely request-in/JSON-out plumbing, plus mapping the one
domain exception (LockedPDFError) and unreadable-file errors to responses
the frontend can render actionably instead of a bare 500.
"""

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from ..schemas import AnalysisResponse
from ..serialization import to_response
from ..upload import analyze_upload

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_statement(
    file: UploadFile = File(...),
    password: Optional[str] = Form(default=None),
) -> AnalysisResponse:
    result = await analyze_upload(file, password)
    return to_response(result)
