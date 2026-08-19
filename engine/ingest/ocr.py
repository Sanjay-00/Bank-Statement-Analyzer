"""
ocr.py - Tesseract front-end for scanned statement pages.

Ported from CIBIL_EXCEL's ocr_extractor.py, trimmed down: that project builds
its own text-row reconstruction inside the OCR module because its downstream
parsers work on raw text. This one doesn't need to - engine.ingest.layout's
rows_with_cells() already reconstructs rows generically from (x0,y0,x1,y1,
text) word boxes for the digital-PDF path, so OCR only has to get a scanned
page into that same shape (via words_from_tesseract, already in layout.py)
and every downstream stage (statement_table.py, categorize.py, reconciliation,
...) runs unchanged - a scanned statement is just another word-box source to
the row engine, not a second extraction pipeline.
"""

import os
import shutil

import fitz

# Render scale for OCR (higher = sharper text, slower). 3x ~= 216 DPI on A4 -
# same figure CIBIL_EXCEL settled on after testing; low enough to OCR a
# multi-page scan in reasonable time, high enough for Tesseract to resolve a
# statement's small transaction-table font.
_OCR_MATRIX = fitz.Matrix(3, 3)

# Force the LSTM engine explicitly (--oem 1) rather than each Tesseract
# build's own default (--oem 3) - different installs (Windows vs a Linux
# server) can default to different bundled engines, so being explicit closes
# one more axis two environments could silently disagree on.
_TESS_CONFIG = "--oem 1"

_WIN_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]


def _configure_tesseract():
    """Locate the Tesseract binary and return a ready-to-use pytesseract
    module, or None if it isn't installed. An env override (TESSERACT_CMD)
    covers custom install locations; otherwise the standard Windows install
    path is checked, then PATH via shutil.which.

    Deliberately never falls back to just handing pytesseract the bare
    "tesseract" command name and hoping subprocess sorts it out - on
    Windows, invoking an unresolvable command name can hang on the App
    Execution Alias redirect (a hidden "open Microsoft Store?" prompt)
    instead of failing fast with FileNotFoundError like it does everywhere
    else. Resolving the path ourselves first means every unavailable case
    returns None immediately, and a page falls back to the pre-OCR
    "flagged as scanned, skipped" behavior instead of hanging the request.
    """
    try:
        import pytesseract
    except ImportError:
        return None

    override = os.getenv("TESSERACT_CMD")
    if override and os.path.exists(override):
        pytesseract.pytesseract.tesseract_cmd = override
        return pytesseract
    for cand in _WIN_CANDIDATES:
        if os.path.exists(cand):
            pytesseract.pytesseract.tesseract_cmd = cand
            return pytesseract
    on_path = shutil.which("tesseract")
    if on_path:
        pytesseract.pytesseract.tesseract_cmd = on_path
        return pytesseract
    return None


def is_available() -> bool:
    """Whether OCR can actually run right now - checked once up front so a
    document with scanned pages can fall back to today's "flagged as
    scanned, skipped" behavior in one place rather than failing page by page
    partway through."""
    pytesseract = _configure_tesseract()
    if pytesseract is None:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def render_page_image(page):
    """Render one PyMuPDF page to a PIL image for OCR. Must run on the
    thread that owns the fitz.Document (MuPDF documents aren't thread-safe)
    - callers OCR-ing many pages should render each on the main thread and
    hand the resulting images off to a worker pool for the actual OCR call,
    not call this from inside worker threads."""
    from PIL import Image
    pix = page.get_pixmap(matrix=_OCR_MATRIX)
    mode = {1: "L", 3: "RGB", 4: "RGBA"}.get(pix.n, "RGB")
    return Image.frombytes(mode, (pix.width, pix.height), pix.samples)


def ocr_image(img) -> list:
    """OCR an already-rendered page image (see render_page_image). Returns
    (x0, y0, x1, y1, text) word boxes in the same shape words_from_page()
    produces for a digital page, via layout.words_from_tesseract - so the
    caller can drop this straight into Page.words and every downstream
    stage treats it identically to a digital page's own word boxes.
    Returns [] if Tesseract isn't available or OCR fails outright (page
    stays flagged as scanned, same as before OCR existed - a failed OCR
    attempt is not worse than the old behavior). Safe to call from a worker
    thread: it only runs a Tesseract subprocess, no MuPDF calls."""
    from .layout import words_from_tesseract

    pytesseract = _configure_tesseract()
    if pytesseract is None:
        return []
    try:
        from pytesseract import Output
        data = pytesseract.image_to_data(img, output_type=Output.DICT, config=_TESS_CONFIG)
    except Exception:
        return []

    words = words_from_tesseract(data)
    # image_to_data's coordinates are in the rendered image's pixel space
    # (scaled by _OCR_MATRIX), not the PDF's own point space - scale back
    # down so these boxes line up with page.rect / page_width the same way
    # a digital page's PyMuPDF word boxes already do.
    sx, sy = 1 / _OCR_MATRIX.a, 1 / _OCR_MATRIX.d
    return [(x0 * sx, y0 * sy, x1 * sx, y1 * sy, text) for x0, y0, x1, y1, text in words]


def ocr_words(page) -> list:
    """Convenience wrapper: render + OCR a single page in one call. Not for
    batch use (see render_page_image/ocr_image + engine.parser's parallel
    dispatch for a multi-page document) - this exists for the single-page
    case where the threading split would just be overhead."""
    return ocr_image(render_page_image(page))
