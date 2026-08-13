"""
bounces.py - cheque/ECS/NACH/UPI bounce (return) frequency.

categorize.py tags BOUNCE on narrations matching RETURN/INSUFFICIENT FUND/
CHQ RET/ECS RET/etc. This module counts and rates them - it deliberately
does not try to split inward (a cheque paid to the customer bounced) from
outward (the customer's own payment bounced), since Indian bank narrations
for this are inconsistent enough that a wrong guess here would be worse than
an honest "can't tell" - the count and the instances are what a red-flag
rule and an analyst both actually need.
"""

from .categorize import BOUNCE


def analyze_bounces(transactions) -> dict:
    bounce_txns = [t for t in transactions if t.category == BOUNCE and t.date is not None]

    months = {(t.date.year, t.date.month) for t in transactions if t.date is not None}
    rate_per_month = (len(bounce_txns) / len(months)) if months else None

    return {
        "count": len(bounce_txns),
        "rate_per_month": rate_per_month,
        "instances": [
            {
                "date": t.date.isoformat(),
                "amount": t.debit or t.credit,
                "narration": t.narration[:120],
            }
            for t in bounce_txns
        ],
    }
