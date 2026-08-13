"""bank_detect.py - resolve a loaded statement to a bank identity."""

import re

from ..parser import LoadedStatement
from ..extract.statement_table import header_boundary_y
from .bank_config import identify_bank


def _header_text(page) -> str:
    """
    Text above the transaction table only. Full-page text would pick up
    counterparty bank names that appear constantly in narrations (e.g.
    "ACH-DR-HDFC BANK LIMITED...") and misidentify the statement's own
    issuing bank - the header block (account holder / IFSC / branch details)
    printed before the table is what's actually unambiguous.
    """
    boundary = header_boundary_y(page)
    words = page.words if boundary is None else [w for w in page.words if w[1] < boundary]
    return " ".join(w[4] for w in words)


def detect(stmt: LoadedStatement) -> tuple:
    """
    Scan the first couple of pages' header text (bank identity usually sits
    in a header block on page 1, occasionally spills to page 2) and return
    (bank_key, display_name). Falls back to (None, "Unknown Bank") - never
    guesses.
    """
    text = " ".join(_header_text(p) for p in stmt.pages[:2] if not p.is_scanned)
    return identify_bank(text)


# Word-boxes get joined with plain spaces (no line breaks survive), so the
# name is captured up to the next known header label rather than a newline.
_NAME_LABEL_RE = re.compile(
    r"(?:Account\s*Name|Customer\s*Name|A/?c\.?\s*Holder(?:\s*Name)?|"
    r"Name\s*of\s*(?:the\s*)?(?:Account\s*Holder|Customer))\s*[:\-]?\s*"
    r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){1,4})",
    re.IGNORECASE,
)
_NAME_STOP_WORDS = {
    "ADDRESS", "ACCOUNT", "A/C", "AC", "IFSC", "BRANCH", "EMAIL", "MOBILE",
    "PHONE", "CUSTOMER", "CIF", "MICR", "STATEMENT", "PERIOD", "FROM", "TO",
    "DATE", "NO", "NUMBER", "ID", "TYPE", "CURRENCY", "NOMINEE", "AVAILABLE",
    "BALANCE", "OPENING", "CLOSING", "AS", "ON", "DATED", "JOINT", "HOLDER",
    "PAN", "KYC", "SCHEME", "PRODUCT",
}


def extract_account_holder(stmt: LoadedStatement) -> str:
    """
    Best-effort account holder name from the header block, for naming the
    Excel report after the customer rather than the bank. Regex against a
    labelled field only ("Account Name:", "Customer Name:", ...) - never
    guesses from an unlabelled capitalised run, so a miss returns None
    rather than a wrong name.
    """
    text = " ".join(_header_text(p) for p in stmt.pages[:2] if not p.is_scanned)
    match = _NAME_LABEL_RE.search(text)
    if not match:
        return None
    words = match.group(1).split()
    while words and words[-1].upper().rstrip(".") in _NAME_STOP_WORDS:
        words.pop()
    if len(words) < 2:
        return None
    return " ".join(words).title()
