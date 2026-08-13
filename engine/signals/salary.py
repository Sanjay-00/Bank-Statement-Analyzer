"""
salary.py - salary recurrence and consistency.

categorize.py tags a credit SALARY only on a strong narration match ("salary",
"payroll", "wages", ...) - this module doesn't re-guess which credits are
salary, it just asks: given the ones already tagged, how regularly and how
consistently do they show up? A single salary-looking credit with no repeat
pattern is a very different risk picture from six months of the same amount
landing in the same few days every month, and that distinction is what this
module turns into actual numbers instead of leaving it implicit.
"""

from statistics import mean, pstdev

from .categorize import SALARY
from .due_date import months_covered

DEFAULT_LOOKBACK_MONTHS = 6

# Below this fraction of the lookback window actually showing a salary
# credit, or above this coefficient of variation in the amount, salary income
# is flagged irregular rather than reliable.
_MIN_RECURRENCE_RATE = 4 / 6
_MAX_COEFFICIENT_OF_VARIATION = 0.15


def analyze_salary(transactions, lookback_months: int = DEFAULT_LOOKBACK_MONTHS) -> dict:
    """
    Returns:
      detected: whether any salary-tagged credit exists at all
      months_covered / months_with_salary: recurrence over the lookback window
      recurrence_rate: months_with_salary / months_covered
      average_amount / coefficient_of_variation: consistency of the amount
        (CV is None with fewer than 2 data points - nothing to vary against)
      day_spread: max-min day-of-month across occurrences (tight = same pay
        cycle every month, wide = inconsistent timing)
      irregular: recurrence or amount-consistency below threshold
      monthly: [(year, month, amount, date), ...] the underlying data, for
        a report to show the actual months rather than only the summary
    """
    all_months = months_covered(transactions)
    recent_months = set(all_months[-lookback_months:] if len(all_months) > lookback_months else all_months)

    by_month = {}
    for t in transactions:
        if t.category != SALARY or not t.credit or t.date is None:
            continue
        key = (t.date.year, t.date.month)
        # If more than one salary-tagged credit lands in the same month
        # (arrears, a correction), keep the larger one rather than summing -
        # summing would overstate a one-off correction as if it recurs.
        if key not in by_month or t.credit > by_month[key]["amount"]:
            by_month[key] = {"amount": t.credit, "date": t.date}

    months_with_salary = sorted(k for k in by_month if k in recent_months)
    recurrence_rate = (len(months_with_salary) / len(recent_months)) if recent_months else 0.0

    amounts = [by_month[k]["amount"] for k in months_with_salary]
    if len(amounts) >= 2:
        avg = mean(amounts)
        cv = (pstdev(amounts) / avg) if avg else None
    elif len(amounts) == 1:
        avg, cv = amounts[0], 0.0
    else:
        avg, cv = None, None

    days = [by_month[k]["date"].day for k in months_with_salary]
    day_spread = (max(days) - min(days)) if len(days) >= 2 else 0

    detected = len(by_month) > 0
    irregular = detected and (
        recurrence_rate < _MIN_RECURRENCE_RATE
        or (cv is not None and cv > _MAX_COEFFICIENT_OF_VARIATION)
    )

    return {
        "detected": detected,
        "months_covered": len(recent_months),
        "months_with_salary": len(months_with_salary),
        "recurrence_rate": recurrence_rate,
        "average_amount": avg,
        "coefficient_of_variation": cv,
        "day_spread": day_spread,
        "irregular": irregular,
        "monthly": [
            {"year": y, "month": m, "amount": by_month[(y, m)]["amount"], "date": by_month[(y, m)]["date"].isoformat()}
            for (y, m) in sorted(by_month.keys())
        ],
    }
