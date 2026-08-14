"""
routes/analyze.py - POST /api/analyze.

Wraps engine.statement.analyze() behind an HTTP endpoint. All the real work
(PDF parsing, reconciliation, every signal) already happens inside engine/ -
this file's job is purely request-in/JSON-out plumbing, plus mapping the one
domain exception (LockedPDFError) and unreadable-file errors to responses
the frontend can render actionably instead of a bare 500.
"""

from typing import Optional, Union

from fastapi import APIRouter, File, Form, UploadFile

from ..schemas import AnalysisResponse, QuickAnalysisResponse
from ..serialization import to_quick_response, to_response
from ..upload import analyze_upload

router = APIRouter(tags=["analyze"])


@router.post("/analyze")
async def analyze_statement(
    file: UploadFile = File(...),
    password: Optional[str] = Form(default=None),
    mode: str = Form(default="deep"),
) -> Union[AnalysisResponse, QuickAnalysisResponse]:
    # No response_model: the two modes return genuinely different shapes,
    # and FastAPI serializes a returned Pydantic model correctly without
    # one - a Union response_model here would just add ambiguous-match risk
    # for no benefit.
    result = await analyze_upload(file, password, mode)
    if mode == "quick":
        return to_quick_response(result)
    return to_response(result)
