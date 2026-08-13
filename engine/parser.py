"""
parser.py - PDF I/O: opens a bank statement, unlocks it if needed, and hands
back per-page word boxes for the extraction stage.

Digital-text only for now (Phase 1-2). A page whose embedded text is too thin
to be a real digital layer is flagged as scanned rather than silently parsed
into garbage - OCR dispatch for those pages lands in Phase 3, reusing
CIBIL_EXCEL's word-box OCR approach.
"""

from dataclasses import dataclass

import fitz

from .ingest.layout import words_from_page
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

    pages = []
    any_scanned = False
    for i, page in enumerate(doc):
        words = words_from_page(page)
        char_count = sum(len(w[4]) for w in words)
        is_scanned = char_count < _SCAN_CHAR_THRESHOLD
        any_scanned = any_scanned or is_scanned
        pages.append(Page(
            index=i,
            width=page.rect.width,
            height=page.rect.height,
            words=words,
            is_scanned=is_scanned,
        ))

    return LoadedStatement(pages=pages, page_count=len(pages), any_scanned=any_scanned)


def page_text(page: Page) -> str:
    """Plain concatenated text for a page - used for bank/format detection."""
    return " ".join(w[4] for w in page.words)
