"""
balances.py - Average Bank Balance (ABB) over trailing 1/3/6/12-month windows.

ABB is the average of the account's *daily* closing balance across every day
in a window, not just the balance on days something happened - a bank
statement only prints a balance where a transaction occurred, so every other
day's balance is implicitly carried forward from the last one that did (the
same forward-fill principle due_date.py's anchor-day lookups use, applied
across an entire window's days instead of four days a month).

A window with too little reconciled history behind it contributes `None`
rather than a silently-low average computed from a partial period - the same
None-vs-0 discipline this project applies everywhere else: an ABB computed
from 12 of an intended 30 days is not the same number as one confidently
computed from all 30, and should never look like it on a report.
"""

import datetime

from .due_date import daily_closing_balances

WINDOWS = [1, 3, 6, 12]

# A window needs at least this fraction of its days carrying a known (or
# forward-filled) balance before its average is trusted - below this, the
# window contributes None rather than an average quietly biased toward
# whichever days happened to be covered.
_MIN_COVERAGE = 0.8

_DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _add_months(d: datetime.date, months: int) -> datetime.date:
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    max_day = _DAYS_IN_MONTH[month - 1]
    if month == 2 and _is_leap(year):
        max_day = 29
    return datetime.date(year, month, min(d.day, max_day))


def _window_average(sorted_dates: list, daily: dict, window_end: datetime.date, months: int) -> dict:
    window_start = _add_months(window_end, -months) + datetime.timedelta(days=1)
    total_days = (window_end - window_start).days + 1

    # Seed the forward-fill with whatever balance was already known at (or
    # before) the window's first day, then walk day by day.
    idx = 0
    last_balance = None
    for d in sorted_dates:
        if d <= window_start:
            last_balance = daily[d]
            idx += 1
        else:
            break

    covered = 0
    total_balance = 0.0
    cur = window_start
    while cur <= window_end:
        while idx < len(sorted_dates) and sorted_dates[idx] <= cur:
            last_balance = daily[sorted_dates[idx]]
            idx += 1
        if last_balance is not None:
            total_balance += last_balance
            covered += 1
        cur += datetime.timedelta(days=1)

    coverage_ratio = (covered / total_days) if total_days else 0
    average = (total_balance / covered) if covered and coverage_ratio >= _MIN_COVERAGE else None

    return {
        "average": average,
        "covered_days": covered,
        "total_days": total_days,
        "window_start": window_start,
        "window_end": window_end,
    }


def analyze_abb(transactions) -> dict:
    """
    Returns {"as_of": last_known_date, "windows": {1: {...}, 3: {...}, 6: {...}, 12: {...}}}
    Each window dict has "average" (float or None), "covered_days",
    "total_days", "window_start", "window_end" - the coverage numbers are
    there so a report can show *why* a window is None (e.g. "covered_days":
    45, "total_days": 365 for a statement that only spans 45 days) rather
    than a bare blank.
    """
    daily = daily_closing_balances(transactions)
    if not daily:
        empty = {"average": None, "covered_days": 0, "total_days": 0, "window_start": None, "window_end": None}
        return {"as_of": None, "windows": {w: dict(empty) for w in WINDOWS}}

    sorted_dates = sorted(daily.keys())
    window_end = sorted_dates[-1]

    windows = {w: _window_average(sorted_dates, daily, window_end, w) for w in WINDOWS}
    return {"as_of": window_end, "windows": windows}
