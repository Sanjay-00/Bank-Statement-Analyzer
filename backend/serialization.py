"""
serialization.py - AnalysisResult (dataclasses + plain dicts, whatever shape
was convenient inside engine/) -> the Pydantic AnalysisResponse the API
promises in schemas.py.

Keeping this conversion in one place, separate from both engine/ and the
routes, means engine/ never has to know an HTTP layer exists, and a route
handler never has to know engine/'s internal dict shapes - each side only
has to agree with this one file.
"""

from dataclasses import asdict

from engine.statement import AnalysisResult, QuickAnalysisResult

from . import schemas


def _due_date_month_row(row: dict) -> schemas.DueDateMonthRow:
    # due_date.py keys these rows by int anchor day (4/9/14/19) - not valid
    # Pydantic/JSON field names, so they get renamed here, once, in the only
    # place that needs to know both shapes.
    return schemas.DueDateMonthRow(
        year=row["year"], month=row["month"],
        day_4=row.get(4), day_9=row.get(9), day_14=row.get(14), day_19=row.get(19),
    )


def _due_date_analysis_out(dda: dict) -> schemas.DueDateAnalysisOut:
    return schemas.DueDateAnalysisOut(
        monthly=[_due_date_month_row(r) for r in dda["monthly"]],
        averages={str(k): v for k, v in dda["averages"].items()},
        recommendations=[schemas.DueDateRecommendation(**r) for r in dda["recommendations"]],
        months_used=dda["months_used"],
    )


def _monthly_out(monthly) -> list:
    return [schemas.MonthlyEntryOut(year=y, month=m, **b) for (y, m), b in monthly.items()]


def _abb_out(abb: dict) -> schemas.AbbOut:
    return schemas.AbbOut(
        as_of=abb["as_of"],
        windows={str(w): schemas.AbbWindowOut(**win) for w, win in abb["windows"].items()},
    )


def to_response(result: AnalysisResult) -> schemas.AnalysisResponse:
    cf = result.cashflow

    return schemas.AnalysisResponse(
        bank_key=result.bank_key,
        bank_name=result.bank_name,
        account_holder=result.account_holder,
        page_count=result.page_count,
        scanned_pages=result.scanned_pages,
        transactions=[schemas.TransactionOut(**asdict(t)) for t in result.transactions],
        summary=schemas.SummaryOut(**result.summary),
        due_date_analysis=_due_date_analysis_out(result.due_date_analysis),
        monthly=_monthly_out(result.monthly),
        fraud_signals=[schemas.FlagOut(**f) for f in result.fraud_signals],
        category_summary={
            cat: schemas.CategoryBucketOut(**b) for cat, b in result.category_summary.items()
        },
        cashflow=schemas.CashflowOut(
            cash_dependency_ratio=cf.get("cash_dependency_ratio"),
            expense_concentration=(
                schemas.ExpenseConcentrationOut(**cf["expense_concentration"])
                if cf.get("expense_concentration") else None
            ),
        ),
        abb=_abb_out(result.abb),
        salary=schemas.SalaryOut(**result.salary),
        bounces=schemas.BouncesOut(**result.bounces),
        red_flags=[schemas.FlagOut(**f) for f in result.red_flags],
        score=schemas.ScoreOut(
            score=result.score["score"],
            components=result.score["components"],
            weights=result.score["weights"],
            red_flag_penalty=result.score["red_flag_penalty"],
            volatility=result.score["volatility"],
            foir_dscr=schemas.FoirDscrOut(**result.score["foir_dscr"]),
        ),
    )


def to_quick_response(result: QuickAnalysisResult) -> schemas.QuickAnalysisResponse:
    return schemas.QuickAnalysisResponse(
        bank_key=result.bank_key,
        bank_name=result.bank_name,
        account_holder=result.account_holder,
        page_count=result.page_count,
        scanned_pages=result.scanned_pages,
        summary=schemas.SummaryOut(**result.summary),
        due_date_analysis=_due_date_analysis_out(result.due_date_analysis),
        monthly=_monthly_out(result.monthly),
        abb=_abb_out(result.abb),
    )
