"""
routes/analyze.py - POST /api/analyze.

Wraps engine.statement.analyze() behind an HTTP endpoint. All the real work
(PDF parsing, reconciliation, every signal) already happens inside engine/ -
this file's job is purely request-in/JSON-out plumbing, plus mapping the one
domain exception (LockedPDFError) and unreadable-file errors to responses
the frontend can render actionably instead of a bare 500.
"""

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from engine.parser import LockedPDFError
from engine.statement import analyze

from ..schemas import AnalysisResponse
from ..serialization import to_response

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_statement(
    file: UploadFile = File(...),
    password: Optional[str] = Form(default=None),
) -> AnalysisResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail={"error_code": "NOT_A_PDF", "message": "Only PDF files are supported."},
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "EMPTY_FILE", "message": "The uploaded file is empty."},
        )

    try:
        result = analyze(file_bytes, password=password)
    except LockedPDFError:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "LOCKED_PDF",
                "message": "This statement is password-protected and the "
                           "supplied password (if any) didn't unlock it.",
            },
        )
    except Exception as exc:  # noqa: BLE001 - genuinely unreadable/corrupt PDF, not a code bug
        raise HTTPException(
            status_code=400,
            detail={"error_code": "UNREADABLE_FILE", "message": f"Couldn't read this PDF: {exc}"},
        )

    return to_response(result)
