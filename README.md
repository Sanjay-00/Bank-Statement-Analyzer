# Bank Statement Analyser

Turns a bank statement PDF into a reconciled, categorized, colour-coded Excel transaction ledger, with fraud signals and an EMI due-date recommendation. Standalone product - see `plan.md` for the in-progress FastAPI + React rebuild.

## Problem

Reading a 50-300 page bank statement by hand to check average balance, salary consistency, or bounced cheques is slow and error-prone.

## Solution

- **Rule-based extraction first.** A generic table engine reads the structural contract every Indian bank statement shares (date, narration, debit/credit amount(s), running balance) - no LLM calls on the default path.
- **Self-validation, not trust.** Every row's running balance is checked against the row before it (`opening + credit - debit == closing`). A row that doesn't reconcile is flagged `FAILED`, not silently included.
- **`None` vs `0` is never blurred.** An unreadable amount short-circuits to `UNVERIFIED` / "Check Statement" rather than being coerced to zero.
- **LLM only as a gated fallback** (Phase 4, not yet built) - never the primary path.

## Status - Streamlit POC, deep-analysis signals mostly built (of 6 original phases)

Digital-text PDF statements, transaction extraction, per-row reconciliation, EMI due-date recommendation, monthly summary, transaction categorization, ABB, salary consistency, bounce frequency, cash-flow ratios, a red-flags rule engine, FOIR/DSCR and a transparent composite cash-flow score, and cheap deterministic fraud/tamper signals are all working end-to-end, with a formatted 7-sheet Excel report (Statement Summary, Red Flags, Fraud Flags, Due Date Analysis, Monthly Summary, Category Summary, Transactions).

**Fraud/tamper signals** (`engine/extract/pdf_forensics.py`, `engine/signals/fraud.py`) - deliberately restricted to the deterministic tier, no ML/training data required: PDF metadata forensics, structural edit-history (`%%EOF` incremental-save counting), font-consistency per page, round-tripping, duplicate transactions, round-number clustering.

**Transaction categorization** (`engine/signals/categorize.py`) - regex/keyword rules (salary, EMI, rent, bounce/NSF, cash, charges, UPI), each with a confidence tier; unmatched stays `uncategorized` rather than guessed.

**Underwriting signals** (`engine/signals/balances.py`, `salary.py`, `bounces.py`, `redflags.py`) - Average Bank Balance over trailing 1/3/6/12-month windows (forward-filled daily series, `None` below an 80% coverage threshold rather than a misleadingly-low partial average); salary recurrence and amount-consistency (coefficient of variation) over the last 6 months; bounce/return frequency; cash-dependency and expense-concentration ratios; and a red-flags rule engine (frequent bounces, salary irregularity, declining ABB trend, high cash dependency, near-zero/negative balance days, multiple recurring EMI-like debit series suggesting an undisclosed loan) - every flag names the specific number that triggered it.

**Creditworthiness scoring** (`engine/signals/scoring.py`) - FOIR (fixed obligations / estimated income, capped 50%/60% per published guidance) and DSCR (net operating income / EMI debt service, floor 1.25), plus a 0-1000 composite cash-flow score built entirely from this project's own signals (ABB, FOIR, bounce rate, income stability, cash dependency) with every component and weight shown in the output - a transparent, tunable policy default, explicitly not a fitted/validated model or a reverse-engineered copy of anyone's proprietary formula.

Validated against 22 real sample statements spanning HDFC, SBI, ICICI, Axis, Bank of Maharashtra, South Indian Bank, TJSB Sahakari Bank, Bassein Catholic Co-op Bank, PNB, and Parshwanath Sahakari Bank - 17 of 22 reconcile at 100%, the rest at 98.7-99.9% with every remaining gap flagged `FAILED` rather than silently wrong; the full signals pipeline (ABB/salary/bounces/red-flags/Excel) runs clean with 0 exceptions across all 22, verified via Streamlit's `AppTest` headless testing framework rather than manual browser clicks. Known gaps:

- A few Axis Bank statements still show a handful of failed rows from a rarer variant of a physical-line-ordering quirk (the common case is fixed - see `_extract_page`'s docstring in `statement_table.py`).
- Two files each have 1-2 failures from a genuine source-data anomaly (ICICI) or a stray reference-number fragment matching the amount pattern (TJSB) - both self-flagged, not silent.
- Scanned/photographed statements are detected and skipped cleanly (no OCR yet).
- Not yet built: LLM gated fallback, CIBIL/ITR cross-check, multi-bank aggregation (see `plan.md`'s "Expanded feature scope").

**UI/UX**: Streamlit app themed via `.streamlit/config.toml` (light-first, amber accent on white/navy - matches the [digitap.ai](https://www.digitap.ai/bank-statement-analyzer-api.html) reference in `frontend.md`) plus scoped CSS for pill CTAs and conditional KPI coloring (red/amber/green only where a number actually signals something). Tabs: Overview, Red flags, Fraud signals, Due date, Monthly summary, Categories, Transactions. The downloaded Excel report matches the same palette so the in-app view and the report read as one product. This is intentionally the ceiling for the Streamlit build - see `plan.md` for the planned FastAPI + React rebuild once the remaining signals are done.

## Running it

```
.BS\Scripts\python.exe -m streamlit run app.py
```

Upload a bank statement PDF, review the reconciliation summary, download the Excel report.

## Architecture

See the full design rationale and build order in the approved plan this project was built from (`.claude/` in this repo, or ask the assistant that built it). In short:

```
engine/
  parser.py            PDF I/O, password unlock
  statement.py          orchestration
  ingest/               layout.py (word-box -> row/cell reconstruction), password.py
  extract/               statement_table.py (generic row extraction), reconciliation.py
  mapping/                bank_config.py, bank_detect.py
  excel_generator.py      Statement Summary + Transactions sheets
```

`engine/mapping/bank_config.py` only carries a bank's display name and identification tokens, not a column layout - the generic table engine (`statement_table.py`) reads column structure positionally (trailing numeric cells, in convention order) rather than by per-bank header mapping, which is what lets new banks work without new parser code. See the module docstrings in `statement_table.py` and `reconciliation.py` for the reasoning.
