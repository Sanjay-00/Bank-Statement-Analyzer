"""
upload.py - shared request handling for the two file-upload routes
(analyze, export). Both routes need the exact same validate -> read ->
analyze() -> domain-exception-to-HTTPException sequence; this is the one
place that owns it so the two routes can't silently drift in what counts
as a valid upload or how a given failure is reported.
"""

from fastapi import HTTPException, UploadFile

from engine.parser import LockedPDFError
from engine.statement import AnalysisResult, QuickAnalysisResult, analyze, analyze_quick


async def analyze_upload(
    file: UploadFile, password: str | None, mode: str = "deep",
) -> AnalysisResult | QuickAnalysisResult:
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
        if mode == "quick":
            return analyze_quick(file_bytes, password=password)
        return analyze(file_bytes, password=password)
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
