"""
pdf_forensics.py - cheap, deterministic PDF-tamper signals.

Mirrors what commercial FCU ("fraud control unit") checks are marketed as
doing (Perfios' "Document Tamper and Behavioural Check", ClearStaq's
"27+ fraud signals", Precisa's 4-tier detection) but restricted to the tier
that's genuinely rule-based - no ML model, no training data, just structural
facts about the PDF itself:

  - metadata: genuine bank statements come from core banking software
    (Finacle, FLEXCUBE, BaNCS) or a bank's own PDF export library, never
    from a consumer PDF editor - the Producer/Creator field says so; and a
    statement is generated once, so its CreationDate and ModDate should be
    the same instant, not hours or days apart.
  - structure: a PDF that's been edited and re-saved without a full
    rewrite leaves extra "%%EOF" markers from PDF's incremental-update
    format - counting them reveals edit history invisibly to any tool that
    only scrubs the Info dictionary.
  - fonts: a genuine statement's transaction table is set in one (or a
    small consistent handful of) embedded font(s) throughout; a row using
    a different font family or an unusual size delta from its neighbours
    usually means text was pasted in after the fact.

These are signals for an analyst to look at, not a verdict - each one is
individually explainable and can have an innocent cause (a bank that
genuinely re-issues a corrected statement, a bold subtotal row). Severity is
informational triage, not a fraud determination.
"""

import datetime
import re

import fitz

SUSPICIOUS_TOOLS = [
    "ADOBE ACROBAT PRO", "SMALLPDF", "ILOVEPDF", "PDF24", "CANVA",
    "PDFESCAPE", "SODAPDF", "PDFELEMENT", "PHANTOMPDF EDITOR", "PHOTOSHOP",
]

_PDF_DATE_RE = re.compile(r"D:(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?")

# Font-consistency check ignores the header/logo zone (top) and footer
# (bottom), which legitimately use different fonts from the transaction
# table without that meaning anything.
_HEADER_FRAC = 0.15
_FOOTER_FRAC = 0.95


def _parse_pdf_date(raw):
    if not raw:
        return None
    m = _PDF_DATE_RE.match(raw)
    if not m:
        return None
    y, mo, d, h, mi, s = m.groups()
    try:
        return datetime.datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), int(s or 0))
    except ValueError:
        return None


def _metadata_signals(doc) -> list:
    signals = []
    meta = doc.metadata or {}
    producer = (meta.get("producer") or "").upper()
    creator = (meta.get("creator") or "").upper()

    for tool in SUSPICIOUS_TOOLS:
        if tool in producer or tool in creator:
            signals.append({
                "code": "SUSPICIOUS_PDF_TOOL",
                "severity": "HIGH",
                "detail": (
                    f"PDF Producer/Creator field mentions '{tool.title()}'. "
                    "Genuine bank statements come from core banking software, "
                    "not a consumer PDF editor."
                ),
            })
            break

    created = _parse_pdf_date(meta.get("creationDate"))
    modified = _parse_pdf_date(meta.get("modDate"))
    if created and modified:
        gap_hours = abs((modified - created).total_seconds()) / 3600
        if gap_hours > 1:
            signals.append({
                "code": "CREATION_MOD_GAP",
                "severity": "MEDIUM",
                "detail": (
                    f"PDF creation and last-modified timestamps differ by "
                    f"{gap_hours:.1f} hours. A genuine statement is generated "
                    "once and not touched again after issuance."
                ),
            })

    return signals


def _structural_signals(file_bytes: bytes) -> list:
    signals = []
    eof_count = file_bytes.count(b"%%EOF")
    if eof_count > 1:
        signals.append({
            "code": "MULTIPLE_EOF_MARKERS",
            "severity": "HIGH",
            "detail": (
                f"PDF contains {eof_count} '%%EOF' markers, meaning "
                f"{eof_count - 1} incremental save(s) happened after the file "
                "was first written. A structural sign the PDF was edited "
                "post-issuance, invisible to a metadata-only check."
            ),
        })
    return signals


def _font_signals_for_page(page) -> list:
    d = page.get_text("dict")
    h = page.rect.height
    top_cut, bottom_cut = h * _HEADER_FRAC, h * _FOOTER_FRAC

    counts = {}
    total = 0
    for block in d.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                y = span["bbox"][1]
                if y < top_cut or y > bottom_cut:
                    continue
                text = span.get("text", "").strip()
                if not text:
                    continue
                key = (span.get("font", ""), round(span.get("size", 0) * 2) / 2)
                counts[key] = counts.get(key, 0) + 1
                total += 1

    if total < 20:
        return []

    outliers = {k: v for k, v in counts.items() if v >= 3 and v < total * 0.03}
    if not outliers:
        return []

    return [{
        "code": "FONT_INCONSISTENCY",
        "severity": "MEDIUM",
        "page": page.number + 1,
        "detail": (
            f"Page {page.number + 1} uses {len(counts)} distinct font/size "
            f"combinations in the transaction area; {len(outliers)} appear "
            "only a handful of times, which can indicate pasted-in or edited "
            "text, or just a bold subtotal/heading row worth a quick look."
        ),
    }]


def analyze(file_bytes: bytes, max_font_check_pages: int = 60) -> list:
    """
    Self-contained: opens its own fitz.Document from file_bytes rather than
    reusing engine.parser's, so this stays decoupled from the extraction
    pipeline. Font-consistency scanning is capped at `max_font_check_pages`
    (checked evenly across the document) - it's the one check here with
    real per-page cost, and a tampered page is just as likely to be caught
    by a sample as by scanning all 300 pages of a large statement.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return [{
            "code": "UNREADABLE_PDF",
            "severity": "HIGH",
            "detail": "The PDF could not be opened for forensic analysis.",
        }]

    signals = []
    signals.extend(_metadata_signals(doc))
    signals.extend(_structural_signals(file_bytes))

    page_count = doc.page_count
    if page_count <= max_font_check_pages:
        sample_indices = range(page_count)
    else:
        step = page_count / max_font_check_pages
        sample_indices = sorted({int(i * step) for i in range(max_font_check_pages)})

    for i in sample_indices:
        signals.extend(_font_signals_for_page(doc[i]))

    return signals
