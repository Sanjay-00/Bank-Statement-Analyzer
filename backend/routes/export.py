"""
routes/export.py - POST /api/analyze/excel.

Re-runs analyze() (no server-side result cache in v1 - see plan.md's "Server-
side result caching" open decision) and streams back the exact same .xlsx
generate_excel()/get_filename() already produce for the Streamlit app, so the
two frontends can never drift in report output.
"""

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from engine.excel_generator import generate_excel, get_filename
from engine.parser import LockedPDFError
from engine.statement import analyze

router = APIRouter(tags=["export"])

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/analyze/excel")
async def export_excel(
    file: UploadFile = File(...),
    password: Optional[str] = Form(default=None),
) -> Response:
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

    excel_bytes = generate_excel(result)
    filename = get_filename(result.bank_name, result.account_holder)

    return Response(
        content=excel_bytes,
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
