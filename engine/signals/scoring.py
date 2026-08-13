"""
scoring.py - FOIR, DSCR, and a transparent cash-flow score.

FOIR and DSCR are the two ratios the credit-decisioning research actually
found published thresholds for (FOIR <=50%, DSCR >=1.25 - see plan.md's
"Expanded feature scope" for sources). Everything past that - loan-amount
multipliers, the exact weights a scoring model uses - is proprietary to
every vendor that publishes one; nobody discloses it. Rather than pretend to
reverse-engineer someone else's black box, the composite score below is
built entirely from signals this project already computes, every weight
shown in the output, explicitly a starting policy to tune against real
outcomes - not a validated model, and it never claims to be one. An analyst
should never have to trust a number they can't see the arithmetic behind.
"""

from statistics import mean, pstdev

from .categorize import EMI, RENT

DEFAULT_LOOKBACK_MONTHS = 6

FOIR_CAP_STANDARD = 50.0
FOIR_CAP_STRONG = 60.0
DSCR_FLOOR = 1.25

# Score component weights (fractions of 1000 total) - a policy default, not
# a fitted model. Change these before relying on the score for anything real.
_WEIGHTS = {
    "abb": 0.25,
    "foir": 0.25,
    "bounces": 0.20,
    "income_stability": 0.20,
    "cash_dependency": 0.10,
}
_RED_FLAG_PENALTY = {"HIGH": 60, "MEDIUM": 25, "LOW": 8}


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def _recent_month_keys(monthly: dict, lookback_months: int) -> list:
    return list(monthly.keys())[-lookback_months:]


def _avg_monthly_debit(transactions, month_keys: list, categories: set) -> float:
    if not month_keys:
        return 0.0
    totals = {k: 0.0 for k in month_keys}
    for t in transactions:
        if t.category not in categories or not t.debit or t.date is None:
            continue
        key = (t.date.year, t.date.month)
        if key in totals:
            totals[key] += t.debit
    return sum(totals.values()) / len(month_keys)


def _estimate_monthly_income(monthly: dict, salary: dict, month_keys: list) -> tuple:
    """(income, source) - the salary average if salary is detected and
    regular, otherwise the average of total monthly credits over the
    lookback window. Averaging several months rather than taking the best
    one is the one piece of concrete guidance the research found for
    estimating self-employed/business income from a bank statement."""
    if salary.get("detected") and not salary.get("irregular") and salary.get("average_amount"):
        return salary["average_amount"], "salary"
    if not month_keys:
        return None, None
    avg_credit = mean(monthly[k]["credit"] for k in month_keys)
    return (avg_credit if avg_credit > 0 else None), "average_monthly_credits"


def analyze_foir_dscr(transactions, monthly: dict, salary: dict,
                       lookback_months: int = DEFAULT_LOOKBACK_MONTHS) -> dict:
    """
    FOIR = fixed obligations (EMI + rent) / income, capped at 50% standard /
    60% for strong profiles per the published guidance.
    DSCR = net operating income / debt service (EMI only - rent isn't debt),
    floor 1.25 per the published guidance. Net operating income is income
    minus every expense that isn't the debt service itself.
    """
    month_keys = _recent_month_keys(monthly, lookback_months)
    income, income_source = _estimate_monthly_income(monthly, salary, month_keys)

    debt_service = _avg_monthly_debit(transactions, month_keys, {EMI})
    fixed_obligations = _avg_monthly_debit(transactions, month_keys, {EMI, RENT})
    avg_total_debit = mean(monthly[k]["debit"] for k in month_keys) if month_keys else None

    foir = (fixed_obligations / income * 100) if income else None
    if foir is None:
        foir_band = None
    elif foir <= FOIR_CAP_STANDARD:
        foir_band = "within standard cap (<=50%)"
    elif foir <= FOIR_CAP_STRONG:
        foir_band = "elevated - within cap for strong profiles only (<=60%)"
    else:
        foir_band = "above typical lending cap (>60%)"

    # Floor rather than `> 0`: a stray sub-Rs.500 debit miscategorized as EMI
    # would otherwise sit in the denominator and blow DSCR up to nonsense.
    dscr = None
    if income is not None and avg_total_debit is not None and debt_service > 500.0:
        non_debt_expenses = avg_total_debit - debt_service
        net_operating_income = income - non_debt_expenses
        dscr = net_operating_income / debt_service
    dscr_band = None
    if dscr is not None:
        dscr_band = "meets standard floor (>=1.25)" if dscr >= DSCR_FLOOR else "below standard floor (<1.25)"

    return {
        "monthly_income": income,
        "income_source": income_source,
        "monthly_debt_service": debt_service,
        "monthly_fixed_obligations": fixed_obligations,
        "foir": foir,
        "foir_band": foir_band,
        "dscr": dscr,
        "dscr_band": dscr_band,
        "months_used": len(month_keys),
    }


def _abb_component(abb: dict) -> float:
    win = abb["windows"].get(3) or abb["windows"].get(1) or {}
    avg = win.get("average")
    if avg is None:
        return 50.0  # not enough history - neutral, not punished
    return _clamp((avg / 50000) * 100)


def _foir_component(foir) -> float:
    if foir is None:
        return 50.0
    if foir <= 40:
        return 100.0
    if foir >= 80:
        return 0.0
    return _clamp(100 - (foir - 40) * 2.5)


def _bounce_component(bounces: dict) -> float:
    rate = bounces.get("rate_per_month") or 0.0
    return _clamp(100 - rate * 30)


def _income_stability_component(monthly: dict, month_keys: list) -> float:
    credits = [monthly[k]["credit"] for k in month_keys if monthly[k]["credit"] > 0]
    if len(credits) < 2:
        return 50.0
    avg = mean(credits)
    cv = (pstdev(credits) / avg) if avg else 1.0
    return _clamp(100 - cv * 150)


def _cash_dependency_component(cashflow: dict) -> float:
    ratio = cashflow.get("cash_dependency_ratio")
    if ratio is None:
        return 50.0
    return _clamp(100 - ratio * 200)


def analyze_cashflow_score(transactions, monthly: dict, salary: dict, bounces: dict,
                            abb: dict, cashflow: dict, red_flags: list,
                            lookback_months: int = DEFAULT_LOOKBACK_MONTHS) -> dict:
    """
    0-1000 composite (higher = lower risk) plus a 0-1 volatility score
    (lower = more stable), same shape as the cash-flow scores commercial
    platforms publish - built from this project's own signals with every
    weight visible in `components`, not copied from anyone's proprietary
    formula. `foir` is computed independently here (not passed in) so this
    function has everything it needs from the signals already on
    AnalysisResult.
    """
    month_keys = _recent_month_keys(monthly, lookback_months)
    foir_dscr = analyze_foir_dscr(transactions, monthly, salary, lookback_months)

    components = {
        "abb": _abb_component(abb),
        "foir": _foir_component(foir_dscr["foir"]),
        "bounces": _bounce_component(bounces),
        "income_stability": _income_stability_component(monthly, month_keys),
        "cash_dependency": _cash_dependency_component(cashflow),
    }
    weighted = sum(components[k] * _WEIGHTS[k] for k in _WEIGHTS) * 10  # 0-100 -> 0-1000
    penalty = sum(_RED_FLAG_PENALTY.get(f.get("severity"), 0) for f in red_flags)
    score = _clamp(weighted - penalty, 0, 1000)
    volatility = _clamp(1 - components["income_stability"] / 100, 0, 1)

    return {
        "score": round(score, 1),
        "components": {k: round(v, 1) for k, v in components.items()},
        "weights": dict(_WEIGHTS),
        "red_flag_penalty": penalty,
        "volatility": round(volatility, 3),
        "foir_dscr": foir_dscr,
    }
