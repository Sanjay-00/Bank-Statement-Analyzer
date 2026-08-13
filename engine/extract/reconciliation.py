"""
reconciliation.py - the bank-statement analogue of CIBIL_EXCEL's "validate
against the report's own printed totals" and ITR Extractor's arithmetic
verification. Every bank statement carries this check implicitly: each row's
running balance is fully determined by the row before it.

Checked per row, not just per document - stronger than either sibling's
whole-block checks, and it pinpoints exactly which row misread rather than
invalidating a whole page. `None` in debit/credit/balance short-circuits to
UNVERIFIED rather than being coerced to 0 - an unreadable amount and a
confident zero must never be treated the same, the same discipline both
sibling projects apply to their own extractions.
"""

from dataclasses import dataclass

_TOLERANCE = 0.02  # paise-level float rounding slack


@dataclass
class VerifiedTransaction:
    date: object
    narration: str
    chq_ref: str
    debit: float
    credit: float
    balance: float
    status: str          # VERIFIED / FAILED / UNVERIFIED / OPENING
    expected_balance: float = None
    category: str = None             # set by engine.signals.categorize, after verify()
    category_confidence: str = None  # "high" / "medium" / "low" / None


def verify(transactions: list) -> list:
    """
    `transactions` is a page-order list of statement_table.RawTransaction.
    Returns a list of VerifiedTransaction with reconciliation status set.
    """
    out = []
    prev_balance = None

    for t in transactions:
        if t.is_opening:
            out.append(VerifiedTransaction(
                date=t.date, narration=t.narration, chq_ref=t.chq_ref,
                debit=None, credit=None, balance=t.balance, status="OPENING",
            ))
            prev_balance = t.balance
            continue

        if prev_balance is None:
            # No opening-balance row was found (some banks omit "B/F" and
            # just start with the first real transaction) - seed from this
            # row's own arithmetic instead of failing every row that follows.
            prev_balance = _infer_opening(t)

        debit, credit = t.debit, t.credit

        # Single ambiguous amount column: resolve direction from which way
        # the balance actually moved, then let the check below catch it if
        # that still doesn't reconcile (e.g. the amount cell was misread).
        if t.ambiguous and prev_balance is not None and t.balance is not None:
            delta = t.balance - prev_balance
            if delta >= 0:
                debit, credit = None, t.debit
            else:
                debit, credit = t.debit, None

        if debit is None and credit is None:
            status = "UNVERIFIED"
            expected = None
        elif prev_balance is None or t.balance is None:
            status = "UNVERIFIED"
            expected = None
        else:
            expected = prev_balance - (debit or 0) + (credit or 0)
            status = "VERIFIED" if abs(expected - t.balance) <= _TOLERANCE else "FAILED"

        out.append(VerifiedTransaction(
            date=t.date, narration=t.narration, chq_ref=t.chq_ref,
            debit=debit, credit=credit, balance=t.balance,
            status=status, expected_balance=expected,
        ))

        if t.balance is not None:
            prev_balance = t.balance

    return out


def _infer_opening(t) -> float:
    """Back out an opening balance from the first real transaction's own
    debit/credit + balance, when the statement prints no explicit B/F row."""
    if t.balance is None:
        return None
    return t.balance + (t.debit or 0) - (t.credit or 0)


def summary(verified: list) -> dict:
    """Counts by status, plus total debit/credit - feeds the Summary sheet
    and is the statement-level cross-check analogue of CIBIL_EXCEL's
    "validate against printed totals": if the statement itself prints an
    opening/closing balance, compare it against opening_balance/
    closing_balance here as an independent second check."""
    total_debit = sum(v.debit or 0 for v in verified if v.status not in ("OPENING",))
    total_credit = sum(v.credit or 0 for v in verified if v.status not in ("OPENING",))
    counts = {"VERIFIED": 0, "FAILED": 0, "UNVERIFIED": 0, "OPENING": 0}
    for v in verified:
        counts[v.status] = counts.get(v.status, 0) + 1

    opening_balance = next((v.balance for v in verified if v.status == "OPENING"), None)
    closing_balance = verified[-1].balance if verified else None

    return {
        "counts": counts,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "transaction_count": len([v for v in verified if v.status != "OPENING"]),
    }
