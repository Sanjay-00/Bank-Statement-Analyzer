# Bank Statement Analyser

Turns a raw bank statement PDF into underwriting-ready intelligence: a reconciled transaction ledger, income/expense signals, fraud indicators, and a credit score — in seconds, with zero manual spreadsheet work.

**Stack:** FastAPI · React 18 + TypeScript · Tailwind · TanStack Query/Table/Virtual · Zod · Python rule engine (PyMuPDF, openpyxl)

## What it does

- **Extracts** transactions from any Indian bank's digital PDF statement — no per-bank parser, one generic table engine reads the date/narration/debit/credit/balance structure every bank shares.
- **Reconciles** every row (`opening + credit − debit == closing`) and flags anything that doesn't check out instead of silently trusting it.
- **Scores creditworthiness**: FOIR, DSCR, Average Bank Balance (1/3/6/12-month), salary consistency, cash-flow ratios, and a transparent 0–1000 composite score with every weight shown.
- **Flags risk**: bounced payments, undisclosed EMIs, declining balance trends, near-zero balance days, round-tripping transactions, duplicate entries.
- **Detects tampering**: PDF metadata forensics, incremental-save history, font-consistency checks — deterministic, no ML black box.
- **Recommends an EMI due date** based on historical balance patterns.
- **Exports** a polished, colour-coded 7-sheet Excel report, and serves the same analysis as JSON over a REST API.

## Architecture

```
engine/          Pure Python analysis core — PDF parsing, reconciliation,
                  categorization, scoring, fraud signals, Excel generation
backend/          FastAPI layer — validates uploads, calls engine/, returns
                  typed JSON (Pydantic) or a streamed .xlsx
frontend/         React + TypeScript SPA — upload, results dashboard,
                  virtualized transaction table, charts
```

Rule-based extraction runs first and is auditable end-to-end; nothing is silently guessed. An unreadable field is surfaced as "unverified," never coerced to zero. This makes every number in the output traceable to a specific row in the source PDF.

## Engineering highlights

- **Bank-agnostic parsing** — new bank support is a config entry, not a new parser module.
- **Contract-tested API** — Pydantic schemas on the backend, Zod validation on the frontend; a shape mismatch fails loudly at the boundary instead of producing `undefined` deep in a component.
- **Validated at scale** — regression-tested against 22 real statements across 10 banks; 100% row-level reconciliation on the majority, with every remaining gap explicitly flagged rather than hidden.
- **Virtualized, type-safe UI** — thousands of transactions render smoothly via windowed rendering; the full frontend is TypeScript strict-mode clean.
- **Deterministic fraud detection** — every signal traces back to a specific, explainable check, not an opaque model score.

## Running locally

```bash
# Backend
pip install -r requirements.txt
uvicorn backend.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Tests

```bash
pytest tests/
```
