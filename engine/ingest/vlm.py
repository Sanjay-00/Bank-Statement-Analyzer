"""
vlm.py - Gemini Vision fallback for pages Tesseract can't read.

Deliberately narrow: this is not a second extraction pipeline sitting
alongside the digital/OCR one, it's a per-page escalation for the specific
case where OCR itself already failed - a scanned page still has too little
recovered text after engine.ingest.ocr's Tesseract pass (handwriting, a
skewed photo, low-resolution scan). That's an existing, already-computed
signal (the same _SCAN_CHAR_THRESHOLD check parser.py runs after OCR), not a
new quality heuristic to invent and tune.

Mirrors CIBIL_EXCEL's ocr_extractor.py pattern (free/local path first,
Vision only as the accuracy safety net for the pages that path couldn't
handle) but returns structured transaction rows directly instead of raw
text, since a bank statement table is far more regular than a CRIF report's
layout - asking the model for the row shape itself avoids a second,
unnecessary text-parsing pass on its output.
"""

import json
import os
import re
import time

_LLM_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

_PROMPT = (
    "This image is one page of an Indian bank statement that could not be read "
    "by OCR (handwritten, skewed, or low-quality scan). Extract every transaction "
    "row from the visible table.\n\n"
    "Return ONLY a valid JSON array, one object per row, oldest-to-newest as "
    "printed, with keys:\n"
    '  date (DD-MM-YYYY), narration (string), debit (number or null), '
    "credit (number or null), balance (number or null)\n"
    "Rules:\n"
    "- Exactly one of debit/credit should be non-null per row (the row's single "
    "amount), never both, unless the statement genuinely prints separate debit "
    "and credit columns with both filled for one row.\n"
    "- balance is the running balance printed on that row. Use null only if the "
    "statement truly does not print one for that row.\n"
    "- Skip header rows, page totals, and any 'Opening Balance' banner row.\n"
    "- Do not invent, merge, or skip transaction rows. Numbers as plain digits "
    "(no commas, no currency symbols).\n"
    "No text outside the JSON array."
)


def is_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def _is_transient(err: Exception) -> bool:
    s = str(err)
    return any(tok in s for tok in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE",
                                     "DeadlineExceeded", "Timeout"))


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [p.get("text", "") for p in content if isinstance(p, dict)]
        return "".join(parts)
    return str(content)


def _invoke(api_key: str, content) -> str:
    """Model cascade with a short backoff-retry on transient errors, same
    shape as CIBIL_EXCEL's _llm_invoke - kept local rather than shared
    because that module also carries CRIF-report-specific prompt/parsing
    code this project has no use for."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage

    last_err = None
    for model in _LLM_MODELS:
        llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key,
                                      temperature=0.1, max_tokens=8192)
        for delay in (0, 1.5, 3):
            if delay:
                time.sleep(delay)
            try:
                return _content_to_text(llm.invoke([HumanMessage(content=content)]).content)
            except Exception as e:
                last_err = e
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    break
                if not _is_transient(e):
                    raise
    raise RuntimeError(f"No Gemini model responded. Tried: {_LLM_MODELS}") from last_err


def _strip_md(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    return re.sub(r"\s*```$", "", text).strip()


def _img_data_uri(img) -> str:
    import base64
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"


def extract_page_transactions(img, api_key: str = None) -> list:
    """Ask Gemini Vision to read one page image as a list of transaction
    dicts (see _PROMPT for shape). Returns [] on any failure - a page Vision
    can't parse either just stays absent from the ledger rather than
    crashing the whole statement, same fail-open posture as the OCR step
    before it."""
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return []
    content = [
        {"type": "text", "text": _PROMPT},
        {"type": "image_url", "image_url": _img_data_uri(img)},
    ]
    try:
        raw = _invoke(api_key, content)
        rows = json.loads(_strip_md(raw))
        return rows if isinstance(rows, list) else []
    except Exception:
        return []
