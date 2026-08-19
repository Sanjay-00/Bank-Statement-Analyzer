"""
statement_table.py - generic transaction-row extraction.

Deliberately does NOT map columns by x-position against a per-bank header
config. Real statement headers merge unpredictably when adjacent columns sit
close together (e.g. "Value Dt" + "Withdrawal Amt." routinely fuse into one
header cell, or a debit amount and the running balance glue into one cell on
some Axis rows), which makes x-anchor matching fragile across dozens of bank
layouts. Instead this reads the *structure* every Indian bank statement
shares regardless of header wording, working on whitespace-split tokens
rather than raw cells so a merged cell doesn't hide the tokens inside it:

  - a transaction row starts wherever one of its first few tokens is a
    parseable date (allowing for a leading serial-number column some banks
    print before the date); everything on later physical lines before the
    next such row is a narration wrap, not a new row (rows_with_cells
    already reconstructs each physical line's cells - this stage decides
    which lines belong to the same logical transaction);
  - amount-shaped tokens (comma-grouped, two decimal places) are always
    right of the narration, in a fixed left-to-right convention every
    sample bank follows: [debit] [credit] balance, with debit/credit
    optional per row and balance always last;
  - when a row prints only one amount column (no separate debit/credit),
    its direction comes from an explicit DR/CR token if present, otherwise
    from the sign of the running-balance delta versus the previous row -
    which reconciliation.py then re-derives independently, so a
    mis-resolved direction fails the balance check rather than silently
    entering the ledger wrong.

This is what lets a bank statement_table.py has never seen work without a
new per-bank column map: bank_config.py only has to carry a display name and
identification tokens, not a layout.

A handful of Axis Bank layouts split one logical transaction across physical
lines out of order (amount+balance printing on the line *before* its own
serial-number/date line) - `_extract_page`'s one-row lookahead handles that
specifically; see its docstring.
"""

import datetime
import re
from dataclasses import dataclass

from ..ingest.layout import rows_with_cells

_MONTHS = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
           "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}

_DATE_RE = re.compile(
    r"^(\d{1,2})[/\-.](\d{1,2}|[A-Za-z]{3})[/\-.](\d{2,4})$"
)

_AMOUNT_RE = re.compile(
    # A few banks print exact-tenth amounts with a single decimal digit
    # ("10000.0" instead of "10000.00") - \d{1,2} instead of a flat \d{2}
    # so those aren't silently invisible to extraction (a rejected amount
    # token isn't a parse failure, it just vanishes into narration text).
    # A zero balance sometimes prints with no leading digit at all (".00"
    # instead of "0.00", seen on Axis statements) - \d* rather than \d+ so
    # that isn't silently dropped either (dropping it doesn't just vanish
    # the token, it desyncs which amount is debit/credit/balance for the
    # row and cascades a wrong running balance into the next transaction).
    r"^-?(?:\d{1,3}(?:,\d{2,3})*|\d*)\.\d{1,2}(CR|DR)?$", re.IGNORECASE
)

_REF_RE = re.compile(r"^\d{6,}$")

# A few banks (Axis) prefix a running balance with a decorative "-," glyph
# that is not a minus sign - a genuine negative always has the "-" directly
# against a digit (e.g. "-2,915.20" on an overdrawn HDFC account).
_DECORATIVE_DASH_RE = re.compile(r"^-,")

# Page-footer boilerplate that sometimes has no date row after it to stop the
# continuation-line accumulation, so it would otherwise glue onto the last
# real transaction's narration on that page - and worse, a summary table's
# own Debit/Credit/Closing-Balance figures are amount-shaped, so without this
# they'd silently corrupt that transaction's amount list (see
# _extract_page's early-break on this pattern). Every bank phrases its
# closing summary differently, so this is a broad net of the phrasings seen
# across the sample set rather than one bank's exact wording.
_FOOTER_RE = re.compile(
    # No trailing \b: several of these phrases end in ":" immediately
    # followed by whitespace, and \b can't match between two non-word
    # characters - a trailing boundary there silently never matches at all.
    r"\b(STATEMENT SUMMARY|B\.\s*Summary|Summary for Account|Transaction Summary|"
    r"This is a computer generated statement|This is a System Generated Statement|"
    r"This is a system-generated statement|"
    r"Registered Office Address|Generated On:|"
    r"Total Transaction Count|Total Debit Amount|Total Credit Amount|"
    r"Balance as on|Total Balance\s*:|Number of Credits?\s*:|Number of Debits?\s*:|"
    r"Page Total\s*:|TOTAL\s*:-|\bTotals\s*/\s*Balance\b|"
    r"TRANSACTION TOTAL\b|"
    r"END OF STATEMENT)", re.IGNORECASE
)

_OPENING_RE = re.compile(r"^\s*(B/?F\b|OPENING\s*BAL(?:ANCE)?\b)", re.IGNORECASE)

# How many leading tokens on a row we'll scan for the date, to tolerate a
# serial-number column before it (Axis: "63  03/10/2025  03/10/2025  ...").
_DATE_SEARCH_WINDOW = 3


def _clean_amount_token(tok: str) -> str:
    return _DECORATIVE_DASH_RE.sub("", tok)


def _parse_date(token: str):
    m = _DATE_RE.match(token.strip())
    if not m:
        return None
    day, month, year = m.groups()
    if len(year) == 2:
        year = "20" + year
    try:
        month_num = _MONTHS.get(month[:3].upper()) if month.isalpha() else int(month)
        if not month_num:
            return None
        return datetime.date(int(year), month_num, int(day))
    except ValueError:
        return None


def _is_amount(token: str) -> bool:
    return bool(_AMOUNT_RE.match(_clean_amount_token(token.strip())))


def _parse_amount(token: str):
    t = _clean_amount_token(token.strip())
    m = _AMOUNT_RE.match(t)
    if not m:
        return None, None
    suffix = (m.group(1) or "").upper() or None
    numeric = re.sub(r"[A-Za-z]", "", t)
    try:
        return float(numeric.replace(",", "")), suffix
    except ValueError:
        return None, suffix


@dataclass
class RawTransaction:
    date: object                 # datetime.date
    narration: str
    chq_ref: str
    debit: float
    credit: float
    balance: float
    is_opening: bool
    ambiguous: bool = False      # single amount column, direction inferred


def _from_vision_rows(rows: list) -> list:
    """A page the vlm fallback recovered already comes back as structured
    rows (see engine.ingest.vlm), not word boxes - no row/column
    reconstruction needed, just conversion to RawTransaction. Skips a row
    outright if its date doesn't parse rather than guessing - same "an
    honest miss beats a wrong guess" rule the rest of this module follows."""
    out = []
    for row in rows:
        date = _parse_date(str(row.get("date", "")).strip())
        if date is None:
            continue
        debit = row.get("debit")
        credit = row.get("credit")
        balance = row.get("balance")
        out.append(RawTransaction(
            date=date,
            narration=str(row.get("narration", "")).strip(),
            chq_ref=None,
            debit=float(debit) if debit not in (None, "") else None,
            credit=float(credit) if credit not in (None, "") else None,
            balance=float(balance) if balance not in (None, "") else None,
            is_opening=False,
        ))
    return out


def extract_transactions(pages) -> list:
    """
    `pages` is a list of engine.parser.Page (digital, non-scanned pages only
    for v1). Returns a flat, page-order list of RawTransaction.
    """
    out = []
    for page in pages:
        if page.is_scanned:
            continue
        if page.vision_rows is not None:
            out.extend(_from_vision_rows(page.vision_rows))
            continue
        rows = rows_with_cells(page.words, page.width)
        out.extend(_extract_page(rows))
    return out


def header_boundary_y(page) -> float:
    """
    Y-coordinate where the transaction table actually starts on a page (the
    first row whose tokens read as a real transaction, per the same
    date+amount test _extract_page uses). Returns None if no transaction row
    is found on the page. Used by bank_detect.py to identify the bank from
    header text only, without counterparty bank names that show up all over
    the narration column (e.g. "ACH-DR-HDFC BANK LIMITED...") getting
    mistaken for the statement's own issuing bank.
    """
    rows = rows_with_cells(page.words, page.width)
    for y, cells in rows:
        tokens = _row_tokens(cells)
        if not tokens:
            continue
        for i in range(min(_DATE_SEARCH_WINDOW, len(tokens))):
            if _parse_date(tokens[i]) and any(_is_amount(t) for t in tokens[i + 1:]):
                return y
    return None


def _row_tokens(cells) -> list:
    toks = []
    for _x0, _x1, text in cells:
        toks.extend(text.split())
    return toks


def _find_date(tokens: list):
    """(date, index) for the first parseable date within the first few
    tokens, or (None, None)."""
    for i in range(min(_DATE_SEARCH_WINDOW, len(tokens))):
        d = _parse_date(tokens[i])
        if d:
            return d, i
    return None, None


def _extract_page(rows) -> list:
    """
    Almost every row is [date ...] [narration] [amount(s)] [balance] on one
    physical line, handled by the straightforward date-then-amount path
    below. A few Axis Bank layouts break that: a transaction's amount and
    balance print on the physical line *before* its own serial-number/date
    line instead of on it, e.g.

        NEFT/DH/AXODH03395335930/GOVINDA          5,000.00   12,89,24,810.45
        30  02/02/2026  02/02/2026  RAMBHAU LONDE/ABHYUDAYA COOPERATIV...

    where line 1 has amounts but no date, and line 2 (the transaction's own
    S.No/date row) has narration but no amount - if line 1 were treated as
    a continuation of whatever came before it (the general rule for a
    date-less row), its amount/balance would corrupt the *previous*
    transaction, and the real transaction on line 2 would be extracted with
    no amounts at all. A single-token lookahead resolves it: a date-less
    row carrying an amount, immediately followed by a date-only row with no
    amount, has its amounts and narration text buffered as the seed of that
    *next* transaction rather than folded into the current one.
    """
    transactions = []
    current = None      # dict accumulator for the transaction being built
    pending = None       # dict buffered from an orphan amount-row, seeding
                          # the next date-only row's transaction

    def flush():
        if current is not None:
            _finalize(current, transactions)

    rows = [(y, cells) for y, cells in rows if _row_tokens(cells)]
    n = len(rows)

    for i, (_y, cells) in enumerate(rows):
        tokens = _row_tokens(cells)

        # Summary/boilerplate text (the "STATEMENT SUMMARY" totals table,
        # legal boilerplate, ...) has no date of its own, so without this
        # check it would be treated as a continuation line of whatever
        # transaction came last - and a summary table's own Debits/Credits/
        # Closing-Bal figures are amount-shaped, so they'd silently corrupt
        # that transaction's amount list. Only flush-and-detach when there's
        # an in-progress transaction actually at risk of contamination - a
        # few banks (seen in the sample set) print this same summary block
        # at the *top* of page 1, before any transaction exists yet, and a
        # blanket break() there would discard the entire page's real rows.
        if _FOOTER_RE.search(" ".join(tokens)):
            if current is not None:
                flush()
                current = None
            pending = None
            continue

        date, date_idx = _find_date(tokens)
        row_has_amount = (
            any(_is_amount(t) for t in tokens[date_idx + 1:]) if date
            else any(_is_amount(t) for t in tokens)
        )

        if date and row_has_amount:
            flush()
            current = {"date": date, "narration_parts": [], "chq_ref": None, "amounts": []}
            _consume_tokens(current, tokens[date_idx + 1:])
            pending = None

        elif date and not row_has_amount and pending is not None:
            # Date/narration with no amount on this line, but `pending` has
            # amounts buffered from the orphan row just before it (the Axis
            # quirk above) - this is that transaction's date/narration half.
            # Deliberately narrow: only start a transaction here when there
            # really is a buffered orphan to attach. A bare date-shaped
            # token turns up plenty of places that aren't transaction rows
            # at all (a statement's own "From Date 30-09-2025 To Date
            # ..." period-range header, for one) - treating every such row
            # as a transaction start regardless of pending swallowed a real
            # statement's header block whole in testing (its "Available
            # Balance"/"Accrued Interest" figures got absorbed as a bogus
            # first transaction's amounts). Anywhere there's no pending
            # orphan, this row falls through to the plain narration-append
            # case below instead, exactly like a row with no date at all.
            flush()
            current = pending
            current["date"] = date
            _consume_tokens(current, tokens[date_idx + 1:])
            pending = None

        elif date and not row_has_amount and current is not None:
            # Same row shape, but nothing pending to attach it to - treat
            # it as more narration for whatever transaction is already
            # in progress rather than manufacturing an empty one.
            _consume_tokens(current, tokens[date_idx + 1:])

        else:
            # No date on this row at all.
            next_date, next_date_idx, next_tokens = None, None, None
            if i + 1 < n:
                next_tokens = _row_tokens(rows[i + 1][1])
                next_date, next_date_idx = _find_date(next_tokens)
            next_is_date_only = bool(next_date) and not any(
                _is_amount(t) for t in next_tokens[next_date_idx + 1:]
            )

            if any(_is_amount(t) for t in tokens) and next_is_date_only:
                # This row's narration + amounts belong to the *next*
                # transaction (the date-only row right after it), not to
                # `current` - whatever `current` was is already complete.
                flush()
                current = None
                pending = {"date": None, "narration_parts": [], "chq_ref": None, "amounts": []}
                _consume_tokens(pending, tokens)
            elif current is not None:
                _consume_tokens(current, tokens)
            elif pending is not None:
                _consume_tokens(pending, tokens)

    flush()
    return transactions


# A transaction row structurally never carries more than 3 amount-shaped
# tokens - debit, credit, balance (or fewer: a single Amount column plus
# balance, or just a balance on an OPENING row). This is a hard invariant of
# the ledger format itself, true for every bank regardless of how a given
# statement phrases its page footer - so it's a far more durable defense
# against footer/summary noise (page totals, "Number of Credits/Debits",
# disclaimer text with stray figures, ...) than matching each phrasing by
# name in _FOOTER_RE ever can be: _FOOTER_RE only catches wording we've
# already seen, this catches the shape of the corruption regardless of
# wording. A 4th+ amount-looking token reaching an accumulator that already
# has 3 is never a real column - drop it into narration instead of letting
# it desync which figure is debit/credit/balance for the row.
_MAX_AMOUNTS_PER_ROW = 3


def _consume_tokens(acc: dict, tokens: list) -> None:
    for tok in tokens:
        if _is_amount(tok) and len(acc["amounts"]) < _MAX_AMOUNTS_PER_ROW:
            acc["amounts"].append(tok)
        elif _REF_RE.match(tok) and acc["chq_ref"] is None:
            acc["chq_ref"] = tok
        elif acc["date"] is not None and _parse_date(tok) is not None:
            # A bare date-shaped token showing up after this transaction's
            # own date is already known is essentially always a "Value
            # Date" column duplicating the transaction date, not real
            # narration text - many statements print both, and a tight
            # column gap between the reference-number/narration column and
            # the Value Date column can fuse them into one cell (the same
            # risk this module's own docstring flags for "Value Dt" +
            # "Withdrawal Amt." - a structural layout-detection limit, not
            # a per-bank quirk, so this drops it regardless of which bank
            # or extraction path - digital or OCR - produced the token).
            continue
        elif tok:
            acc["narration_parts"].append(tok)


def _finalize(acc: dict, out: list) -> None:
    narration = " ".join(acc["narration_parts"]).strip()
    m = _FOOTER_RE.search(narration)
    if m:
        narration = narration[:m.start()].strip()

    if not acc["amounts"]:
        return  # shouldn't happen given the amount_after gate, but be defensive

    balance_val, _bal_suffix = _parse_amount(acc["amounts"][-1])
    leading = acc["amounts"][:-1]

    is_opening = bool(_OPENING_RE.search(narration))

    if is_opening or not leading:
        out.append(RawTransaction(
            date=acc["date"], narration=narration or "OPENING BALANCE",
            chq_ref=acc["chq_ref"], debit=None, credit=None,
            balance=balance_val, is_opening=True,
        ))
        return

    if len(leading) >= 2:
        debit, _ = _parse_amount(leading[0])
        credit, _ = _parse_amount(leading[1])
        ambiguous = False
    else:
        amt, suffix = _parse_amount(leading[0])
        if suffix == "DR":
            debit, credit, ambiguous = amt, None, False
        elif suffix == "CR":
            debit, credit, ambiguous = None, amt, False
        elif amt is not None and amt < 0:
            # A handful of formats sign the single Amount column directly
            # instead of a CR/DR suffix - the minus sign IS the debit
            # indicator, not part of the magnitude, so it resolves the
            # direction just as unambiguously as an explicit DR token.
            debit, credit, ambiguous = -amt, None, False
        else:
            # Direction not stated on the row itself - resolved against the
            # previous transaction's balance in reconciliation.py, which is
            # also where a wrong guess here gets caught.
            debit, credit, ambiguous = amt, None, True

    out.append(RawTransaction(
        date=acc["date"], narration=narration, chq_ref=acc["chq_ref"],
        debit=debit, credit=credit, balance=balance_val,
        is_opening=False, ambiguous=ambiguous,
    ))
