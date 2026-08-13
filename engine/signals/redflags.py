"""
redflags.py - the DPD/status-colour analogue for bank statements.

Every rule here reads a number already computed elsewhere in this package
(reconciliation, categorize, balances, salary, bounces) and checks it
against a threshold - this module never re-derives anything itself, it's a
thin decision layer on top of signals that already exist. Each flag names
the specific number that triggered it so an analyst can see exactly why
without re-deriving it themselves, the same "explainable, not a black-box
verdict" stance the fraud signals already take.

Severity mirrors CIBIL_EXCEL's RBI-SMA-stage colour gradient conceptually
(a graded scale of concern, not a single risky/not-risky bit) but this is a
bank-statement-native rule set, not a borrowed bureau taxonomy - it's new
territory for this suite, not a reuse of an existing one.
"""

_MIN_RECURRENCE_RATE = 4 / 6
_BOUNCE_COUNT_THRESHOLD = 2
_CASH_DEPENDENCY_THRESHOLD = 0.30
_NEAR_ZERO_BALANCE = 1000.0
_ABB_DECLINE_RATIO = 0.70          # ABB1 below this fraction of ABB3 = declining
_EMI_SERIES_MIN_OCCURRENCES = 2    # a recurring debit needs this many hits to count as a "series"
_MULTIPLE_EMI_SERIES_THRESHOLD = 2  # this many distinct series = possible undisclosed loans


def _flag(code, severity, detail):
    return {"code": code, "severity": severity, "detail": detail}


def _bounce_flag(bounces: dict):
    count = bounces.get("count", 0)
    if count <= _BOUNCE_COUNT_THRESHOLD:
        return None
    rate = bounces.get("rate_per_month")
    rate_txt = f" ({rate:.1f}/month)" if rate is not None else ""
    return _flag(
        "FREQUENT_BOUNCES", "HIGH",
        f"{count} bounced/returned payment(s) detected{rate_txt} - a direct "
        "repayment-stress signal, not just a data quality note.",
    )


def _salary_irregularity_flag(salary: dict):
    if not salary.get("detected"):
        return _flag(
            "NO_SALARY_DETECTED", "MEDIUM",
            "No salary-pattern credit found in this statement - either "
            "genuinely no fixed salary (self-employed/business income) or "
            "income arrives through a channel this doesn't recognise as salary.",
        )
    if salary.get("irregular"):
        rate = salary.get("recurrence_rate", 0)
        cv = salary.get("coefficient_of_variation")
        cv_txt = f", amount varies {cv:.0%} month to month" if cv else ""
        return _flag(
            "SALARY_IRREGULARITY", "MEDIUM",
            f"Salary credit found in only {salary['months_with_salary']} of "
            f"{salary['months_covered']} recent month(s) ({rate:.0%} recurrence){cv_txt}.",
        )
    return None


def _abb_decline_flag(abb: dict):
    windows = abb.get("windows", {})
    abb1 = windows.get(1, {}).get("average")
    abb3 = windows.get(3, {}).get("average")
    if abb1 is None or abb3 is None or abb3 <= 0:
        return None
    if abb1 < abb3 * _ABB_DECLINE_RATIO:
        return _flag(
            "DECLINING_BALANCE_TREND", "MEDIUM",
            f"Average balance over the last month (Rs.{abb1:,.0f}) is "
            f"{100 * (1 - abb1 / abb3):.0f}% below the 3-month average "
            f"(Rs.{abb3:,.0f}) - a real downward trend, not a single low day.",
        )
    return None


def _cash_dependency_flag(cashflow: dict):
    ratio = cashflow.get("cash_dependency_ratio")
    if ratio is None or ratio < _CASH_DEPENDENCY_THRESHOLD:
        return None
    return _flag(
        "HIGH_CASH_DEPENDENCY", "MEDIUM",
        f"{ratio:.0%} of total money movement is cash (ATM/CDM) rather than "
        "digital - harder to independently verify than UPI/NEFT activity.",
    )


def _near_zero_balance_flag(transactions):
    instances = [
        t for t in transactions
        if t.status != "OPENING" and t.balance is not None and t.balance < _NEAR_ZERO_BALANCE
    ]
    if not instances:
        return None
    lowest = min(t.balance for t in instances)
    return _flag(
        "NEAR_ZERO_BALANCE", "MEDIUM" if lowest >= 0 else "HIGH",
        f"{len(instances)} day(s) with closing balance under Rs.{_NEAR_ZERO_BALANCE:,.0f}"
        + (f", including a negative balance of Rs.{lowest:,.2f}" if lowest < 0 else
           f" (lowest: Rs.{lowest:,.2f})") + ".",
    )


def _undisclosed_loan_flag(transactions):
    """Groups EMI-category debits into "series" (same rounded amount, same
    narration prefix) - two or more distinct recurring series suggests more
    than one loan obligation, which is exactly the pattern an undisclosed
    second loan looks like from the bank statement alone. Flagged for
    analyst review, not auto-classified as fraud - a legitimate borrower can
    genuinely have two EMIs."""
    from .categorize import EMI

    series = {}
    for t in transactions:
        if t.category != EMI or not t.debit or t.date is None:
            continue
        key = (round(t.debit / 100) * 100, t.narration[:24].strip().upper())
        series.setdefault(key, []).append(t)

    recurring = {k: v for k, v in series.items() if len(v) >= _EMI_SERIES_MIN_OCCURRENCES}
    if len(recurring) < _MULTIPLE_EMI_SERIES_THRESHOLD:
        return None

    detail_lines = [
        f"Rs.{k[0]:,.0f} x{len(v)} - \"{k[1]}\""
        for k, v in sorted(recurring.items(), key=lambda kv: -len(kv[1]))[:10]
    ]
    return {
        "code": "MULTIPLE_EMI_SERIES",
        "severity": "HIGH",
        "detail": (
            f"{len(recurring)} distinct recurring EMI-like debit series found - "
            "worth checking against the bureau report for undisclosed loans, "
            "though a borrower can legitimately have more than one EMI."
        ),
        "instances": [{"Amount (Rs.)": k[0], "Occurrences": len(v), "Narration": k[1]} for k, v in recurring.items()],
    }


def analyze_red_flags(transactions, bounces: dict, salary: dict, abb: dict, cashflow: dict) -> list:
    checks = [
        _bounce_flag(bounces),
        _salary_irregularity_flag(salary),
        _abb_decline_flag(abb),
        _cash_dependency_flag(cashflow),
        _near_zero_balance_flag(transactions),
        _undisclosed_loan_flag(transactions),
    ]
    return [f for f in checks if f is not None]
