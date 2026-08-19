"""
parser.py - PDF I/O: opens a bank statement, unlocks it if needed, and hands
back per-page word boxes for the extraction stage.

A page whose embedded text is too thin to be a real digital layer is a scan
or photograph, not a digital export - it gets OCR'd on the spot (Tesseract,
via engine.ingest.ocr) rather than silently parsed into garbage. If OCR
recovers enough text the page is treated as digital from that point on
(same word-box shape, same downstream row engine); if Tesseract isn't
installed or the page still comes up thin, it stays flagged as scanned and
the rest of the pipeline skips it exactly as it did before OCR existed.
"""

from dataclasses import dataclass

import fitz

from .ingest import vlm
from .ingest.layout import words_from_page
from .ingest.ocr import ocr_image, render_page_image
from .ingest.password import unlock

# A page with fewer embedded characters than this (for a normal, non-blank
# statement page) almost certainly has no real text layer - it's a scan or a
# photograph, not a digital export.
_SCAN_CHAR_THRESHOLD = 40


class LockedPDFError(Exception):
    """Raised when a password-protected PDF couldn't be unlocked."""


@dataclass
class Page:
    index: int
    width: float
    height: float
    words: list          # (x0, y0, x1, y1, text)
    is_scanned: bool
    vision_rows: list = None   # transaction dicts from vlm fallback, or None


@dataclass
class LoadedStatement:
    pages: list           # list[Page]
    page_count: int
    any_scanned: bool


def load_statement(file_bytes: bytes, password: str = None,
                    pan: str = None, dob: str = None, name: str = None) -> LoadedStatement:
    """
    Open a bank statement PDF from bytes and extract per-page word boxes.

    Raises LockedPDFError if the document needs a password and none of the
    supplied/explicit/auto-tried candidates worked - the caller (app.py)
    should catch this and prompt the user for the password interactively.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    if doc.needs_pass:
        if not unlock(doc, explicit_password=password, pan=pan, dob=dob, name=name):
            raise LockedPDFError(
                "This statement is password-protected and none of the supplied "
                "credentials unlocked it."
            )

    page_words = [words_from_page(page) for page in doc]
    scanned_idx = [
        i for i, words in enumerate(page_words)
        if sum(len(w[4]) for w in words) < _SCAN_CHAR_THRESHOLD
    ]

    # OCR every scanned page's image up front, in parallel - each Tesseract
    # call is ~5s and a multi-page scan (a whole statement photographed page
    # by page) would otherwise OCR serially, one page at a time. Rendering
    # stays on this thread (MuPDF documents aren't thread-safe); only the
    # OCR call itself - a subprocess, GIL released while it runs - goes to
    # the worker pool, so results are identical to serial OCR, just faster.
    if scanned_idx:
        from concurrent.futures import ThreadPoolExecutor
        import os as _os

        images = [render_page_image(doc[i]) for i in scanned_idx]
        workers = min(len(images), max(1, _os.cpu_count() or 4))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            ocr_results = list(pool.map(ocr_image, images))
        for i, words in zip(scanned_idx, ocr_results):
            if sum(len(w[4]) for w in words) >= _SCAN_CHAR_THRESHOLD:
                page_words[i] = words

    pages = []
    any_scanned = False
    for i, page in enumerate(doc):
        words = page_words[i]
        is_scanned = sum(len(w[4]) for w in words) < _SCAN_CHAR_THRESHOLD
        vision_rows = None

        # Tesseract already had its shot at this page (the OCR pass above)
        # and still came up thin - a scan too poor for OCR (handwriting,
        # skew, low resolution). Escalate to Gemini Vision only for that
        # specific case, only if a key is configured; anything it can't
        # parse either just leaves the page flagged scanned, same as today.
        if is_scanned and vlm.is_configured():
            rows = vlm.extract_page_transactions(render_page_image(page))
            if rows:
                vision_rows, is_scanned = rows, False

        any_scanned = any_scanned or is_scanned
        pages.append(Page(
            index=i,
            width=page.rect.width,
            height=page.rect.height,
            words=words,
            is_scanned=is_scanned,
            vision_rows=vision_rows,
        ))

    return LoadedStatement(pages=pages, page_count=len(pages), any_scanned=any_scanned)


def page_text(page: Page) -> str:
    """Plain concatenated text for a page - used for bank/format detection."""
    return " ".join(w[4] for w in page.words)
