import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.extract.reconciliation import verify
from engine.extract.statement_table import RawTransaction


def _txn(date, narration, debit, credit, balance, is_opening=False, ambiguous=False):
    return RawTransaction(
        date=date, narration=narration, chq_ref=None,
        debit=debit, credit=credit, balance=balance,
        is_opening=is_opening, ambiguous=ambiguous,
    )


def test_clean_ledger_all_verified():
    d = datetime.date(2026, 1, 1)
    txns = [
        _txn(d, "B/F", None, None, 1000.0, is_opening=True),
        _txn(d, "salary", None, 500.0, 1500.0),
        _txn(d, "rent", 300.0, None, 1200.0),
    ]
    out = verify(txns)
    assert [t.status for t in out] == ["OPENING", "VERIFIED", "VERIFIED"]


def test_mismatched_row_fails():
    d = datetime.date(2026, 1, 1)
    txns = [
        _txn(d, "B/F", None, None, 1000.0, is_opening=True),
        _txn(d, "bad row", 300.0, None, 999.0),  # should be 700.0
    ]
    out = verify(txns)
    assert out[1].status == "FAILED"


def test_missing_amount_is_unverified_not_zero():
    d = datetime.date(2026, 1, 1)
    txns = [
        _txn(d, "B/F", None, None, 1000.0, is_opening=True),
        _txn(d, "unreadable amount", None, None, 1200.0),
    ]
    out = verify(txns)
    assert out[1].status == "UNVERIFIED"
    assert out[1].debit is None and out[1].credit is None


def test_ambiguous_single_amount_resolved_by_balance_delta():
    d = datetime.date(2026, 1, 1)
    txns = [
        _txn(d, "B/F", None, None, 1000.0, is_opening=True),
        _txn(d, "ambiguous credit", 200.0, None, 1200.0, ambiguous=True),
    ]
    out = verify(txns)
    assert out[1].status == "VERIFIED"
    assert out[1].credit == 200.0
    assert out[1].debit is None


def test_no_opening_row_infers_starting_balance():
    d = datetime.date(2026, 1, 1)
    txns = [
        _txn(d, "first real txn", None, 500.0, 1500.0),
        _txn(d, "second", 100.0, None, 1400.0),
    ]
    out = verify(txns)
    assert [t.status for t in out] == ["VERIFIED", "VERIFIED"]
