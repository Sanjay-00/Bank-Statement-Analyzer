"""
statement.py - orchestration: bytes in, a fully reconciled transaction
ledger + bank identity out. app.py and excel_generator.py both work off this
one result shape, same "converge on a unified output" habit as CIBIL_EXCEL's
parser.py orchestrator and ITR Extractor's columns.py.
"""

from dataclasses import dataclass

from .parser import LockedPDFError, load_statement
from .mapping.bank_detect import detect, extract_account_holder
from .extract.statement_table import extract_transactions
from .extract.reconciliation import verify, summary
from .extract.pdf_forensics import analyze as pdf_forensics
from .signals.due_date import analyze_due_dates, monthly_summary
from .signals.fraud import content_fraud_signals
from .signals.categorize import categorize_transactions, category_summary, cashflow_ratios
from .signals.balances import analyze_abb
from .signals.salary import analyze_salary
from .signals.bounces import analyze_bounces
from .signals.redflags import analyze_red_flags
from .signals.scoring import analyze_cashflow_score


@dataclass
class AnalysisResult:
    bank_key: str
    bank_name: str
    account_holder: str        # best-effort from the header block, else None
    page_count: int
    scanned_pages: int
    transactions: list        # list[VerifiedTransaction], .category set
    summary: dict
    due_date_analysis: dict
    monthly: "object"          # OrderedDict[(year, month) -> dict]
    fraud_signals: list        # [{"code","severity","detail",...}, ...]
    category_summary: dict     # {category: {"count","total_debit","total_credit"}}
    cashflow: dict             # {"cash_dependency_ratio", "expense_concentration"}
    abb: dict                  # {"as_of", "windows": {1,3,6,12: {...}}}
    salary: dict                # recurrence/consistency, see signals/salary.py
    bounces: dict                # count/rate/instances, see signals/bounces.py
    red_flags: list               # [{"code","severity","detail",...}, ...]
    score: dict                    # FOIR/DSCR + composite score, see signals/scoring.py


@dataclass
class QuickAnalysisResult:
    """Lightweight sibling of AnalysisResult for the "quick analysis" path:
    reconciled balances only, none of the deep-analysis signal stack
    (categorization, salary, bounces, red flags, scoring, fraud/tamper
    checks). Exists as its own shape rather than AnalysisResult with fields
    defaulted/omitted, so nothing downstream (schemas, Excel) has to guess
    which of AnalysisResult's fields are meaningful in this mode."""
    bank_key: str
    bank_name: str
    account_holder: str
    page_count: int
    scanned_pages: int
    summary: dict
    due_date_analysis: dict
    monthly: "object"          # OrderedDict[(year, month) -> dict]
    abb: dict                  # {"as_of", "windows": {1,3,6,12: {...}}}


_SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _chronological(raw: list) -> list:
    """
    Most Indian bank statements print oldest-first, but a few (seen in the
    sample set: a PNB-issued statement) print newest-first instead. Every
    downstream stage - reconciliation's running-balance propagation, due-date
    analysis's "last transaction of the day wins" balance lookup, monthly
    summaries - assumes ascending date order, so this normalises it once
    here rather than each consumer having to guard against both directions.
    Detected structurally (majority of consecutive pairs descending), not
    per-bank, so it generalises to any statement printed either way.
    """
    dated = [t.date for t in raw if t.date is not None]
    if len(dated) < 2:
        return raw
    descending = sum(1 for a, b in zip(dated, dated[1:]) if b < a)
    ascending = sum(1 for a, b in zip(dated, dated[1:]) if b > a)
    return list(reversed(raw)) if descending > ascending else raw


def analyze(file_bytes: bytes, password: str = None,
            pan: str = None, dob: str = None, name: str = None) -> AnalysisResult:
    stmt = load_statement(file_bytes, password=password, pan=pan, dob=dob, name=name)

    bank_key, bank_name = detect(stmt)
    account_holder = extract_account_holder(stmt)

    digital_pages = [p for p in stmt.pages if not p.is_scanned]
    raw = _chronological(extract_transactions(digital_pages))
    verified = verify(raw)

    categories = categorize_transactions(verified)
    for t, (cat, conf) in zip(verified, categories):
        t.category, t.category_confidence = cat, conf

    monthly = monthly_summary(verified)
    cat_summary = category_summary(verified, categories)
    cashflow = cashflow_ratios(cat_summary)
    abb = analyze_abb(verified)
    salary = analyze_salary(verified)
    bounces = analyze_bounces(verified)
    red_flags = analyze_red_flags(verified, bounces, salary, abb, cashflow)
    score = analyze_cashflow_score(verified, monthly, salary, bounces, abb, cashflow, red_flags)

    fraud_signals = pdf_forensics(file_bytes, password=password) + content_fraud_signals(verified)
    fraud_signals.sort(key=lambda s: _SEVERITY_ORDER.get(s.get("severity"), 9))

    return AnalysisResult(
        bank_key=bank_key,
        bank_name=bank_name,
        account_holder=account_holder,
        page_count=stmt.page_count,
        scanned_pages=stmt.page_count - len(digital_pages),
        transactions=verified,
        summary=summary(verified),
        due_date_analysis=analyze_due_dates(verified),
        monthly=monthly,
        fraud_signals=fraud_signals,
        category_summary=cat_summary,
        cashflow=cashflow,
        abb=abb,
        salary=salary,
        bounces=bounces,
        red_flags=red_flags,
        score=score,
    )


def analyze_quick(file_bytes: bytes, password: str = None,
                   pan: str = None, dob: str = None, name: str = None) -> QuickAnalysisResult:
    """Same PDF-to-reconciled-ledger path as analyze(), but stops there:
    no categorization, salary/bounce/red-flag signals, scoring, or fraud
    forensics - just what "quick analysis" actually needs (ABB, due-date
    recommendation, monthly credit/debit), computed without paying for the
    rest of the deep-analysis stack."""
    stmt = load_statement(file_bytes, password=password, pan=pan, dob=dob, name=name)

    bank_key, bank_name = detect(stmt)
    account_holder = extract_account_holder(stmt)

    digital_pages = [p for p in stmt.pages if not p.is_scanned]
    raw = _chronological(extract_transactions(digital_pages))
    verified = verify(raw)

    return QuickAnalysisResult(
        bank_key=bank_key,
        bank_name=bank_name,
        account_holder=account_holder,
        page_count=stmt.page_count,
        scanned_pages=stmt.page_count - len(digital_pages),
        summary=summary(verified),
        due_date_analysis=analyze_due_dates(verified),
        monthly=monthly_summary(verified),
        abb=analyze_abb(verified),
    )
