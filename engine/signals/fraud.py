"""
fraud.py - content-level fraud signals on the already-reconciled ledger.

Complements pdf_forensics.py's document-level checks with the transaction
patterns commercial platforms name as classic manipulation signatures:
balance-inflation round-tripping (money in, same money out days later, to
show a healthier balance than the account actually carries), duplicate rows
(a copy-pasted transaction to inflate turnover), and round-number clustering
(a real UPI/NEFT-heavy account is naturally noisy; a wall of suspiciously
exact amounts is not). Every check here already has the ledger it needs -
reconciliation.py's per-row verification - so there is no new extraction
cost, only new arithmetic over data already in hand.
"""

import datetime

_ROUND_TRIP_DAYS = 5
_ROUND_TRIP_TOLERANCE = 0.01          # 1% amount-match tolerance
_ROUND_TRIP_MIN_AMOUNT = 20000.0      # ignore small UPI in/out noise entirely
_ROUND_NUMBER_DIVISOR = 1000
_ROUND_NUMBER_MIN_COUNT = 15
_ROUND_NUMBER_FLAG_RATIO = 0.40


def _is_round(amount: float) -> bool:
    return amount is not None and amount > 0 and amount % _ROUND_NUMBER_DIVISOR == 0


def _round_number_clustering(transactions) -> list:
    amounts = [t.debit for t in transactions if t.debit] + \
              [t.credit for t in transactions if t.credit]
    if len(amounts) < _ROUND_NUMBER_MIN_COUNT:
        return []
    round_count = sum(1 for a in amounts if _is_round(a))
    ratio = round_count / len(amounts)
    if ratio < _ROUND_NUMBER_FLAG_RATIO:
        return []
    return [{
        "code": "ROUND_NUMBER_CLUSTERING",
        "severity": "LOW",
        "detail": (
            f"{round_count} of {len(amounts)} transaction amounts "
            f"({ratio:.0%}) are exact multiples of Rs.{_ROUND_NUMBER_DIVISOR}. "
            "Unusually clean for organic UPI/NEFT activity, worth a look "
            "though plenty of genuine accounts (fixed rent/EMI amounts) "
            "land here innocently."
        ),
    }]


def _round_tripping(transactions) -> list:
    """Large credit followed by a near-equal debit within a few days -
    the classic "show a healthy balance for the statement, then move the
    money back out" pattern. Restricted to materially large amounts (small
    UPI in/out - mandate registrations, split bills - would otherwise match
    combinatorially and bury the real signal in thousands of noise hits),
    and each debit is only ever claimed by its single closest-matching
    credit so one busy day of transactions can't multiply into dozens of
    "instances" of the same underlying pair."""
    credits = [t for t in transactions if t.credit and t.date and t.credit >= _ROUND_TRIP_MIN_AMOUNT]
    debits = [t for t in transactions if t.debit and t.date and t.debit >= _ROUND_TRIP_MIN_AMOUNT]

    used_debits = set()
    pairs = []
    for c in sorted(credits, key=lambda t: t.date):
        best = None
        best_diff = None
        for i, d in enumerate(debits):
            if i in used_debits or d.date < c.date:
                continue
            gap = (d.date - c.date).days
            if gap > _ROUND_TRIP_DAYS:
                continue
            diff = abs(d.debit - c.credit) / c.credit
            if diff <= _ROUND_TRIP_TOLERANCE and (best_diff is None or diff < best_diff):
                best, best_diff, best_gap = i, diff, gap
        if best is not None:
            used_debits.add(best)
            pairs.append((c, debits[best], best_gap))

    if not pairs:
        return []

    instances = [
        {
            "Credit date": c.date.isoformat(),
            "Credit amount (Rs.)": c.credit,
            "Debit date": d.date.isoformat(),
            "Debit amount (Rs.)": d.debit,
            "Gap (days)": gap,
        }
        for c, d, gap in pairs
    ]
    return [{
        "code": "ROUND_TRIPPING",
        "severity": "MEDIUM",
        "detail": (
            f"{len(pairs)} instance(s) of a large credit followed by a "
            f"near-equal debit within {_ROUND_TRIP_DAYS} days. Can indicate "
            "balance inflation for the statement rather than genuine cash flow."
        ),
        "instances": instances,
    }]


def _duplicate_transactions(transactions) -> list:
    seen = {}
    for t in transactions:
        if t.status == "OPENING" or t.date is None:
            continue
        key = (t.date, t.debit, t.credit, t.narration.strip().lower())
        seen[key] = seen.get(key, 0) + 1

    dupes = {k: v for k, v in seen.items() if v > 1}
    if not dupes:
        return []

    total_extra = sum(v - 1 for v in dupes.values())
    instances = [
        {
            "Date": date.isoformat(),
            "Amount (Rs.)": debit or credit,
            "Repeats": count,
            "Narration": narration[:80],
        }
        for (date, debit, credit, narration), count in dupes.items()
    ]
    return [{
        "code": "DUPLICATE_TRANSACTIONS",
        "severity": "MEDIUM",
        "detail": (
            f"{len(dupes)} distinct transaction(s) appear more than once with "
            f"identical date/amount/narration ({total_extra} extra row(s) total). "
            "Can be a genuine repeated payment, a copy-pasted row to inflate "
            "turnover, or a parsing artifact worth checking against the source PDF."
        ),
        "instances": instances,
    }]


def content_fraud_signals(transactions) -> list:
    signals = []
    signals.extend(_round_number_clustering(transactions))
    signals.extend(_round_tripping(transactions))
    signals.extend(_duplicate_transactions(transactions))
    return signals
