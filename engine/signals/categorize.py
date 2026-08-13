"""
categorize.py - transaction categorization.

Rule-based, same "deterministic first" philosophy as the rest of this suite -
regex/keyword matching over the narration field, each category returning a
confidence tier. Unmatched narrations stay "uncategorized" rather than being
forced into the nearest-looking bucket - a guessed category is worse than an
honest "don't know" when the downstream signals (salary consistency, ABB,
red flags) depend on these being right, not just populated.

Order matters: categories are checked in the sequence below, first match
wins, going from most-specific/least-ambiguous to most-generic. A narration
matching both "salary" and "UPI" patterns (most salary credits arrive via
UPI/NEFT, and the payment-mode token is often present alongside the
employer-style token) should land in SALARY, not the generic UPI bucket -
that's why UPI/cash/charges checks run last.
"""

import re

# ── Category constants ──────────────────────────────────────────────

SALARY = "salary"
EMI = "emi"
RENT = "rent"
BOUNCE = "bounce"
UPI = "upi"
CASH = "cash"
CHARGES = "charges"
INTEREST = "interest"
UNCATEGORIZED = "uncategorized"

# ── Pattern tables ───────────────────────────────────────────────────
# Each entry: (category, compiled regex, confidence). Checked in order;
# first match wins. "high" confidence means the narration token is
# unambiguous on its own (e.g. "SALARY", "EMI"); "medium" means the token is
# suggestive but shared with adjacent concepts (e.g. a NACH mandate could be
# an EMI or a SIP/insurance premium - still bucketed as EMI/loan-obligation
# since that's the common case, but flagged medium not high).

_BOUNCE_RE = re.compile(
    r"\b(RETURN(?:ED)?|INSUFFICIENT\s*FUND|CHQ\s*RET|CHEQUE\s*RET|"
    r"ECS\s*RET|NACH\s*RET|UPI\s*RET|ACH\s*RET|BOUNCE|"
    r"FUNDS?\s*INSUFFICIENT|REFER\s*TO\s*DRAWER|EXCEEDS\s*ARRANGEMENT|"
    r"UNPAID)\b", re.IGNORECASE
)

_EMI_RE = re.compile(
    r"\b(EMI|LOAN\s*(?:REPAY|INSTAL|EMI)|NACH[\s-]|ACH[\s-]?(?:DR|DEBIT)|"
    r"MANDATE|LOAN\s*A/?C|INSTALLMENT|INSTALMENT)\b", re.IGNORECASE
)

_RENT_RE = re.compile(r"\bRENT\b", re.IGNORECASE)

_SALARY_RE = re.compile(
    r"\b(SALARY|SAL\s*CREDIT|SAL[\s-]|PAYROLL|WAGES?)\b", re.IGNORECASE
)

_INTEREST_CHARGE_RE = re.compile(
    r"\b(INT\.?\s*(?:PAID|CREDIT|CR)|INTEREST\s*(?:PAID|CREDIT|CR)|"
    r"SMS\s*CHRG|SMS\s*ALERT|AMB\s*CHRG|MAB\s*CHRG|"
    r"MIN(?:IMUM)?\s*BAL(?:ANCE)?\s*CHRG|ANNUAL\s*FEE|AMC|"
    r"GST\s*(?:ON|CHRG)|CARD\s*(?:ANN|ANNUAL)|"
    r"INCIDENTAL\s*CHARGE|LEDGER\s*(?:FOLIO)?\s*CHRG|"
    r"CHEQUE\s*BOOK\s*CHRG|ATM\s*(?:ANN\.?|ANNUAL)\s*CHRG)\b", re.IGNORECASE
)

_CASH_RE = re.compile(
    r"\b(ATM\s*(?:WDL|WITHDRAW|CASH)?|CASH\s*WDL|CASH\s*DEPOSIT|"
    r"CDM|SELF\s*(?:CHQ|CHEQUE)?|CSH\s*WDL)\b", re.IGNORECASE
)

_UPI_RE = re.compile(r"\bUPI\b", re.IGNORECASE)


def categorize(narration: str) -> tuple:
    """
    Returns (category, confidence) for a single transaction's narration.
    confidence is "high"/"medium"/"low"; UNCATEGORIZED always pairs with
    confidence None since there's nothing to be confident about.
    """
    if not narration:
        return UNCATEGORIZED, None

    if _BOUNCE_RE.search(narration):
        return BOUNCE, "high"
    if _SALARY_RE.search(narration):
        return SALARY, "high"
    if _RENT_RE.search(narration):
        return RENT, "high"
    if _EMI_RE.search(narration):
        return EMI, "medium"
    if _INTEREST_CHARGE_RE.search(narration):
        return CHARGES, "high"
    if _CASH_RE.search(narration):
        return CASH, "medium"
    if _UPI_RE.search(narration):
        return UPI, "low"

    return UNCATEGORIZED, None


def categorize_transactions(transactions) -> list:
    """
    `transactions` is a list of engine.extract.reconciliation.VerifiedTransaction.
    Returns a parallel list of (category, confidence) tuples, same order,
    including one entry for OPENING rows (categorized UNCATEGORIZED - an
    opening-balance row isn't a transaction to bucket).
    """
    out = []
    for t in transactions:
        if t.status == "OPENING":
            out.append((UNCATEGORIZED, None))
            continue
        out.append(categorize(t.narration))
    return out


def category_summary(transactions, categories) -> dict:
    """
    `categories` is the parallel list from categorize_transactions().
    Returns {category: {"count": n, "total_debit": x, "total_credit": y}},
    ordered by total absolute amount descending - the categories moving the
    most money surface first, not just the most frequent ones.
    """
    buckets = {}
    for t, (cat, _conf) in zip(transactions, categories):
        if t.status == "OPENING":
            continue
        b = buckets.setdefault(cat, {"count": 0, "total_debit": 0.0, "total_credit": 0.0})
        b["count"] += 1
        b["total_debit"] += t.debit or 0
        b["total_credit"] += t.credit or 0

    return dict(sorted(
        buckets.items(),
        key=lambda kv: kv[1]["total_debit"] + kv[1]["total_credit"],
        reverse=True,
    ))


def cashflow_ratios(cat_summary: dict) -> dict:
    """
    Two cheap derived ratios on top of an already-computed category_summary -
    no new extraction, just arithmetic over numbers already in hand:

      cash_dependency_ratio: what fraction of total money movement (debit +
        credit across every category) is cash (ATM/CDM) rather than digital -
        a heavily cash-dependent account is harder to verify and a genuine
        underwriting-relevant signal on its own.
      expense_concentration: the single largest spending category's share of
        total debit - a concentrated, explainable expense picture (e.g.
        "60% EMI") reads very differently from a diffuse one.
    """
    total_debit = sum(b["total_debit"] for b in cat_summary.values())
    total_credit = sum(b["total_credit"] for b in cat_summary.values())
    total_flow = total_debit + total_credit

    cash = cat_summary.get(CASH, {"total_debit": 0.0, "total_credit": 0.0})
    cash_amount = cash["total_debit"] + cash["total_credit"]
    cash_dependency_ratio = (cash_amount / total_flow) if total_flow else None

    debit_by_cat = {cat: b["total_debit"] for cat, b in cat_summary.items() if b["total_debit"] > 0}
    if debit_by_cat and total_debit:
        top_cat = max(debit_by_cat, key=debit_by_cat.get)
        expense_concentration = {
            "category": top_cat,
            "ratio": debit_by_cat[top_cat] / total_debit,
        }
    else:
        expense_concentration = None

    return {
        "cash_dependency_ratio": cash_dependency_ratio,
        "expense_concentration": expense_concentration,
    }
