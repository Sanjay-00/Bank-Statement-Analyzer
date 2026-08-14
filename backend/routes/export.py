"""
routes/export.py - POST /api/analyze/excel.

Re-runs analyze() (no server-side result cache in v1 - see plan.md's "Server-
side result caching" open decision) and streams back the exact same .xlsx
generate_excel()/get_filename() already produce for the Streamlit app, so the
two frontends can never drift in report output.
"""

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import Response

from engine.excel_generator import generate_excel, get_filename

from ..upload import analyze_upload

router = APIRouter(tags=["export"])

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/analyze/excel")
async def export_excel(
    file: UploadFile = File(...),
    password: Optional[str] = Form(default=None),
) -> Response:
    result = await analyze_upload(file, password)

    excel_bytes = generate_excel(result)
    filename = get_filename(result.bank_name, result.account_holder)

    return Response(
        content=excel_bytes,
        media_type=_XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
