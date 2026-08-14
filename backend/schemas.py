"""
schemas.py - Pydantic response models mirroring engine.statement.AnalysisResult.

One model per shape AnalysisResult (or a signal module) already returns.
Field names/types are copied from the actual dataclasses and dict shapes in
engine/ - this file doesn't invent a new contract, it just gives the existing
one a schema FastAPI can validate against and auto-document.
"""

import datetime
from typing import Optional

from pydantic import BaseModel


class TransactionOut(BaseModel):
    date: Optional[datetime.date]
    narration: str
    chq_ref: Optional[str]
    debit: Optional[float]
    credit: Optional[float]
    balance: Optional[float]
    status: str
    expected_balance: Optional[float] = None
    category: Optional[str] = None
    category_confidence: Optional[str] = None


class SummaryOut(BaseModel):
    counts: dict[str, int]
    total_debit: float
    total_credit: float
    opening_balance: Optional[float]
    closing_balance: Optional[float]
    transaction_count: int


class DueDateMonthRow(BaseModel):
    year: int
    month: int
    day_4: Optional[float] = None
    day_9: Optional[float] = None
    day_14: Optional[float] = None
    day_19: Optional[float] = None


class DueDateRecommendation(BaseModel):
    priority: int
    anchor_day: int
    due_date: str
    avg_balance: float


class DueDateAnalysisOut(BaseModel):
    monthly: list[DueDateMonthRow]
    averages: dict[str, Optional[float]]  # keys "4"/"9"/"14"/"19" - JSON object keys are always strings
    recommendations: list[DueDateRecommendation]
    months_used: int


class MonthlyEntryOut(BaseModel):
    year: int
    month: int
    debit: float
    credit: float
    debit_count: int
    credit_count: int
    txn_count: int
    net: float


class FlagOut(BaseModel):
    """Shared shape for both red_flags and fraud_signals - same dict shape
    in engine/, same model here."""
    code: str
    severity: str
    detail: str
    instances: Optional[list[dict]] = None


class CategoryBucketOut(BaseModel):
    count: int
    total_debit: float
    total_credit: float


class ExpenseConcentrationOut(BaseModel):
    category: str
    ratio: float


class CashflowOut(BaseModel):
    cash_dependency_ratio: Optional[float]
    expense_concentration: Optional[ExpenseConcentrationOut]


class AbbWindowOut(BaseModel):
    average: Optional[float]
    covered_days: int
    total_days: int
    window_start: Optional[datetime.date]
    window_end: Optional[datetime.date]


class AbbOut(BaseModel):
    as_of: Optional[datetime.date]
    windows: dict[str, AbbWindowOut]  # keys "1"/"3"/"6"/"12"


class SalaryMonthOut(BaseModel):
    year: int
    month: int
    amount: float
    date: str


class SalaryOut(BaseModel):
    detected: bool
    months_covered: int
    months_with_salary: int
    recurrence_rate: float
    average_amount: Optional[float]
    coefficient_of_variation: Optional[float]
    day_spread: int
    irregular: bool
    monthly: list[SalaryMonthOut]


class BounceInstanceOut(BaseModel):
    date: str
    amount: Optional[float]
    narration: str


class BouncesOut(BaseModel):
    count: int
    rate_per_month: Optional[float]
    instances: list[BounceInstanceOut]


class FoirDscrOut(BaseModel):
    monthly_income: Optional[float]
    income_source: Optional[str]
    monthly_debt_service: float
    monthly_fixed_obligations: float
    foir: Optional[float]
    foir_band: Optional[str]
    dscr: Optional[float]
    dscr_band: Optional[str]
    months_used: int


class ScoreOut(BaseModel):
    score: float
    components: dict[str, float]
    weights: dict[str, float]
    red_flag_penalty: int
    volatility: float
    foir_dscr: FoirDscrOut


class AnalysisResponse(BaseModel):
    bank_key: Optional[str]
    bank_name: str
    account_holder: Optional[str]
    page_count: int
    scanned_pages: int
    transactions: list[TransactionOut]
    summary: SummaryOut
    due_date_analysis: DueDateAnalysisOut
    monthly: list[MonthlyEntryOut]
    fraud_signals: list[FlagOut]
    category_summary: dict[str, CategoryBucketOut]
    cashflow: CashflowOut
    abb: AbbOut
    salary: SalaryOut
    bounces: BouncesOut
    red_flags: list[FlagOut]
    score: ScoreOut


class QuickAnalysisResponse(BaseModel):
    """Mirrors engine.statement.QuickAnalysisResult - the condensed sibling
    of AnalysisResponse for the quick-analysis path (ABB, due-date
    recommendation, monthly credit/debit only, no signal stack)."""
    bank_key: Optional[str]
    bank_name: str
    account_holder: Optional[str]
    page_count: int
    scanned_pages: int
    summary: SummaryOut
    due_date_analysis: DueDateAnalysisOut
    monthly: list[MonthlyEntryOut]
    abb: AbbOut


class ErrorResponse(BaseModel):
    error_code: str
    message: str
