"""
due_date.py - EMI/loan due-date recommendation.

Lenders set a due date; the borrower needs enough closing balance the day
before it clears (auto-debit mandates run early morning against the
previous day's closing balance, not the due date's own). This checks the
customer's closing balance on the 4th/9th/14th/19th of every month (the day
before the four due dates lenders commonly offer - 5th/10th/15th/20th),
averages each anchor day's balance over the last 6 months of the statement,
and recommends the due date whose anchor day carries the highest average
balance - i.e. the date the customer is statistically most likely to be able
to pay on.

"Closing balance on day X" means the last transaction's running balance on
day X, or the closing balance of the most recent earlier day with any
transaction at all if day X itself had none - a bank statement only prints a
balance where something happened, so every other day's balance is implicitly
carried forward from the last one that did.
"""

import datetime
from collections import OrderedDict

ANCHOR_DAYS = [4, 9, 14, 19]
DUE_DATE_LABEL = {4: "5th", 9: "10th", 14: "15th", 19: "20th"}
DEFAULT_LOOKBACK_MONTHS = 6


def daily_closing_balances(transactions) -> dict:
    """date -> balance, last transaction of each day wins (assumes the
    statement's own row order is chronological, same assumption
    reconciliation.py makes)."""
    daily = {}
    for t in transactions:
        if t.date is not None and t.balance is not None:
            daily[t.date] = t.balance
    return daily


def months_covered(transactions) -> list:
    dates = [t.date for t in transactions if t.date is not None]
    if not dates:
        return []
    start, end = min(dates), max(dates)
    months, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return months


def _balance_on_or_before(target: datetime.date, sorted_dates: list, daily: dict):
    candidate = None
    for d in sorted_dates:
        if d > target:
            break
        candidate = d
    return daily.get(candidate) if candidate is not None else None


def analyze_due_dates(transactions, lookback_months: int = DEFAULT_LOOKBACK_MONTHS) -> dict:
    """
    Returns:
      monthly: [{"year", "month", 4: bal, 9: bal, 14: bal, 19: bal}, ...]
                one row per calendar month the statement covers, ascending.
      averages: {4: avg_or_None, 9: ..., 14: ..., 19: ...} over the last
                `lookback_months` rows of `monthly`.
      recommendations: [{"priority", "anchor_day", "due_date", "avg_balance"}, ...]
                ranked highest average balance first.
      months_used: how many months actually fed the averages (<= lookback_months
                   when the statement covers fewer).
    """
    daily = daily_closing_balances(transactions)
    sorted_dates = sorted(daily.keys())
    months = months_covered(transactions)

    monthly = []
    for (y, m) in months:
        row = {"year": y, "month": m}
        for anchor in ANCHOR_DAYS:
            try:
                target = datetime.date(y, m, anchor)
            except ValueError:
                target = None
            row[anchor] = (_balance_on_or_before(target, sorted_dates, daily)
                            if target is not None else None)
        monthly.append(row)

    recent = monthly[-lookback_months:] if len(monthly) > lookback_months else monthly

    averages = {}
    for anchor in ANCHOR_DAYS:
        vals = [row[anchor] for row in recent if row[anchor] is not None]
        averages[anchor] = (sum(vals) / len(vals)) if vals else None

    ranked = sorted(
        (a for a in ANCHOR_DAYS if averages[a] is not None),
        key=lambda a: averages[a], reverse=True,
    )
    recommendations = [
        {
            "priority": i + 1,
            "anchor_day": a,
            "due_date": DUE_DATE_LABEL[a],
            "avg_balance": averages[a],
        }
        for i, a in enumerate(ranked)
    ]

    return {
        "monthly": monthly,
        "averages": averages,
        "recommendations": recommendations,
        "months_used": len(recent),
    }


def monthly_summary(transactions) -> "OrderedDict":
    """(year, month) -> {debit, credit, debit_count, credit_count, txn_count,
    net}, ascending by month. Opening-balance rows are excluded - they carry
    no debit/credit of their own."""
    buckets = OrderedDict()
    for t in transactions:
        if t.date is None or t.status == "OPENING":
            continue
        key = (t.date.year, t.date.month)
        b = buckets.setdefault(key, {
            "debit": 0.0, "credit": 0.0,
            "debit_count": 0, "credit_count": 0, "txn_count": 0,
        })
        if t.debit:
            b["debit"] += t.debit
            b["debit_count"] += 1
        if t.credit:
            b["credit"] += t.credit
            b["credit_count"] += 1
        b["txn_count"] += 1
    for b in buckets.values():
        b["net"] = b["credit"] - b["debit"]
    return buckets
