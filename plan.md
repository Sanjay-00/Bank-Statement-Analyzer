# Migration plan — Streamlit → FastAPI + React

## Context

The Streamlit build (Phase 1-2 of the original plan) proved the hard part: PDF extraction, generic-structure transaction parsing, running-balance reconciliation, EMI due-date recommendation, monthly summary, and deterministic fraud signals, all validated against 22 real bank statements across 11+ banks. What it can't do is look or feel like a real product — Streamlit's component model has a visual ceiling this project has now hit (see `frontend.md`'s design notes on why). The fix is a proper frontend, not more CSS injected into Streamlit.

**Goal**: rebuild the UI as a React SPA served by a FastAPI backend, without touching the `engine/` package's logic. The backend is a thin HTTP wrapper around code that already works; the frontend is a from-scratch build against `frontend.md`'s design system.

**This is a standalone product going forward** — no "Underwriting Intelligence Platform" suite framing in the UI or in user-facing copy anywhere in this rewrite.

**Sequencing decision**: finish the remaining analysis features (transaction categorization, salary consistency, ABB, CIBIL/ITR cross-check, FOIR/DSCR credit scoring — the original "deep analysis" scope) as a Streamlit POC *before* starting the React/FastAPI build, not after. All of that is `engine/` logic that carries over unchanged into the FastAPI backend regardless of frontend, so building it now means the API contract in this document gets written against a data model that's already proven, not guessed at. The Streamlit UI from this point on stays strictly minimal/functional — no further visual polish work, since anything decorative here is thrown away the moment React replaces it. `frontend.md` and this plan stay as the target to build toward once the POC's logic is validated, not something to start on yet.

## Expanded feature scope (from market research)

Two rounds of competitor research since the original plan - a LinkedIn writeup of an "AI bank statement analyzer" product (CART by Novel Patterns) and Digitap's bank-statement-analyzer product page - surfaced concrete signals worth adding to the deep-analysis POC, and a few real scope decisions.

### New signals to fold into the ABB/salary-consistency build

**Built.** Cheap additions on top of `categorize.py` and `monthly_summary()`, which already had the data these needed:

- **Income volatility/seasonality** - `engine/signals/salary.py`: recurrence rate + coefficient-of-variation on salary amounts over the last 6 months, `irregular` flag when either falls outside threshold.
- **Cash dependency ratio** - `categorize.cashflow_ratios()`: cash (ATM/CDM) share of total money movement.
- **Expense concentration** - same function: largest spending category's share of total debit.

Explicitly not chasing: "mule account identification" and "peer-benchmark usage patterns" (both need a network of other accounts or a peer population dataset a single-statement tool doesn't have and can't fabricate) and the vendor's specific ROI percentage claims (40-70% turnaround reduction etc.) - that's sales copy, not methodology.

### Feature-parity checklist against Digitap's Bank Statement Analyzer

| Digitap feature | Our status |
|---|---|
| Creditworthiness (income+expenses+liabilities → credit profile) | **Built** - `engine\signals\scoring.py`: FOIR (capped 50%/60%) and DSCR (floor 1.25) against published thresholds, plus a 0-1000 composite score with every weight/component visible - a transparent policy default, not a fitted model. Surfaced in the Excel report and the Overview tab |
| Automated Red Flag Detection ("35+ risky patterns") | **Built** - `engine/signals/redflags.py`: frequent bounces, salary irregularity/absence, declining ABB trend, high cash dependency, near-zero/negative balance days, multiple recurring EMI-like debit series (possible undisclosed loan) - 6 rules today, on top of `fraud.py`'s 3 content checks + `pdf_forensics.py`'s tamper checks. Getting to "35+" needs a deliberate broader rule pass on top of this foundation, not a rewrite |
| Tampered PDF Detection by AI & ML | We already do this deterministically (metadata forensics, `%%EOF` incremental-save counting, font-consistency) - deliberately *not* matching their "AI & ML" framing; a rule an analyst can read and verify beats a model verdict they can't, consistent with this whole project's philosophy |
| Cheque/ECS Returns tracking | **Built** - `engine/signals/bounces.py`: count, rate per month, and instance list, feeding the `FREQUENT_BOUNCES` red flag |
| Income Verification (declared vs actual) | This is the CIBIL/ITR cross-check already in scope - matches exactly, no new work implied. Still not built |
| Loan & EMI Analysis (liabilities mapping) | Partial - `redflags.py`'s `MULTIPLE_EMI_SERIES` check groups EMI-category debits into recurring series (amount + narration match) and flags 2+ distinct series; a fuller "liabilities mapped" report (one row per series with amount/frequency/first-seen date, independent of the red-flag threshold) is still open and feeds FOIR calculation directly once built |
| Cash Flow Analysis | **Built** - `monthly_summary()` + `category_summary()` + `cashflow_ratios()` (cash dependency, expense concentration) together cover this; presented as separate Monthly/Category tabs plus ratios on the Overview tab rather than one consolidated view - cosmetic, not a gap |
| Multi-Bank Aggregation (consolidate multiple statements into one report) | **Not in scope, real decision needed.** Every part of this project so far assumes one statement, one account, one report. Aggregating several accounts (possibly several banks) into a single borrower-level view is a genuine architecture question - does `AnalysisResult` become a list, does reconciliation/signals run per-account then combine, does the Excel/UI need a "consolidated" mode - not a small addition. Flagging for a decision, not building blind |

## What doesn't change

`engine/` is pure Python with no Streamlit dependency already (`app.py` only ever imports `analyze()` and `generate_excel()` from it) — this is the whole reason the migration is cheap. None of the following gets touched:

- `engine/parser.py`, `engine/ingest/` — PDF I/O, password handling, word-box extraction
- `engine/extract/` — table extraction, reconciliation, PDF forensics
- `engine/mapping/` — bank identification
- `engine/signals/` — due-date recommendation, monthly summary, fraud signals
- `engine/statement.py` — `analyze()` orchestration, returns `AnalysisResult`
- `engine/excel_generator.py` — `generate_excel()`, `get_filename()`

## What's new

```
backend/
  main.py                 # FastAPI app, CORS, exception handlers
  routes/
    analyze.py              # POST /api/analyze
    export.py                # POST /api/analyze/excel
  schemas.py               # Pydantic response models mirroring AnalysisResult
  serialization.py          # AnalysisResult (dataclasses) -> Pydantic/JSON
frontend/
  (see frontend.md's file structure)
```

`engine/` stays exactly where it is at the repo root; `backend/` imports it the same way `app.py` does today (`from engine.statement import analyze`). `app.py` (Streamlit) can stay in the repo as a reference/fallback until the React version is validated end-to-end, then gets deleted.

## API contract

Kept deliberately small — two endpoints, both synchronous. No job queue, no WebSocket, no polling.

**Why synchronous**: every real sample tested processes in under 1.5 seconds, including a 320-page, 2936-transaction statement. A plain HTTP request/response is the right tool at this latency; adding async job infrastructure now would be solving a problem that doesn't exist yet. Revisit this decision only when Phase 3 (OCR for scanned pages) lands — Tesseract OCR on a large scanned document could genuinely take tens of seconds to minutes, and *that's* when a job-status pattern (`POST /api/analyze` returns a job id, `GET /api/jobs/{id}` polls) earns its complexity.

### `POST /api/analyze`

Multipart form: `file` (PDF), optional `password` (string).

Response `200`: JSON mirroring `AnalysisResult` — `bank_key`, `bank_name`, `page_count`, `scanned_pages`, `transactions[]`, `summary`, `due_date_analysis`, `monthly[]`, `fraud_signals[]`. Every fraud signal's `instances` field is structured data (list of objects), never pre-formatted prose strings — this is the fix already made in the Streamlit version (see `frontend.md`'s fraud-signal-card note) and the API contract is where it has to be enforced so the frontend can never regress back to string-concatenated instance lists.

Response `422`: password-protected PDF, wrong/missing password (`LockedPDFError` mapped to a specific error code + message the frontend can render actionably, not a raw 500).

Response `400`: not a PDF / unreadable file.

The response is held client-side (TanStack Query cache keyed by file hash + password), matching the Streamlit version's `st.session_state` caching behavior — re-rendering a tab shouldn't re-hit the API.

### `POST /api/analyze/excel`

Same multipart input as `/api/analyze` (the backend doesn't persist analysis results server-side in v1, so this re-runs `analyze()` — cheap enough at current speeds; revisit if that changes). Returns the `.xlsx` bytes with the correct filename via `Content-Disposition`, using the existing `generate_excel()` / `get_filename()` unchanged.

An alternative worth considering once the frontend is stable: cache the `AnalysisResult` server-side keyed by an analysis id returned from `/api/analyze`, and have Excel download be `GET /api/analyze/{id}/excel` — avoids re-parsing the PDF for a download. Deferred to a later phase; not needed for v1 given current speeds.

## Non-functional requirements

- **CORS**: frontend dev server (Vite, port 5173) and the production frontend origin both allowlisted explicitly, not `*`.
- **File size limit**: match Streamlit's current 200MB default at the FastAPI layer (`Request` body size limit via the ASGI server config, e.g. Uvicorn's `--limit-max-requests` isn't the right lever — use a request-size-limiting middleware or check `Content-Length` early).
- **No auth in v1.** This mirrors the Streamlit version (single-user, run-it-yourself tool). If this needs to be shared with other analysts before auth is built, that's a real gap to flag, not something to silently ship without.
- **Error handling**: FastAPI exception handlers map `LockedPDFError` and any parsing failure to structured JSON errors (`{"error_code": "...", "message": "..."}`), never a bare 500 with a Python traceback reaching the client.
- **Logging**: keep it simple — structured request logs (file name, size, processing time, bank detected, signal count) to stdout; no analytics/telemetry service in v1.

## Testing

- **Backend**: `pytest` + FastAPI's `TestClient`, reusing the same 22-sample regression approach already established (`tests/test_reconciliation_units.py`'s pattern) — hit `/api/analyze` with each real sample, assert response shape and key figures match what direct `engine.statement.analyze()` calls already produce. This is mostly a serialization-correctness check, not a re-test of extraction logic (that's already covered).
- **Frontend**: Vitest + React Testing Library for components (KPI card, severity badge, transactions table rendering); no e2e framework in v1 — manual verification against the real sample set, same as how the Streamlit version was validated, until the UI stabilizes enough to justify Playwright.

## Deployment

**Decision: split hosting, zero cost.** Frontend on Vercel, backend on Render — both free tiers, no ops burden. Ruled out AWS EC2 + Docker for now: full control isn't needed yet, and it trades zero cost/zero maintenance for real ongoing cost (EC2's free tier is 12 months only) and operational work (patching, TLS renewal, container orchestration, uptime monitoring) that doesn't buy anything at this stage. Revisit only if Render's free-tier cold start becomes a real problem or a future phase needs infrastructure control Render can't offer.

**Frontend — Vercel (free/Hobby plan).**
1. Push the repo to GitHub.
2. Vercel → New Project → import the repo → set the project **root directory to `frontend/`** (Vercel auto-detects Vite).
3. Add an environment variable `VITE_API_URL` pointing at the Render backend's URL (e.g. `https://bank-statement-analyser.onrender.com`).
4. Every push to `main` auto-deploys; every PR gets its own preview URL for free.

**Backend — Render (free tier).**
1. Render → New → Web Service → connect the same GitHub repo, **root directory** left at the repo root (so `engine/` is importable from `backend/`).
2. Build command: `pip install -r requirements.txt`.
3. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
4. Free tier spins down after ~15 minutes idle and takes roughly 30-50s to cold-start on the next request — acceptable for a low-traffic personal tool, worth knowing if it ever needs to feel instant for someone else.

**CORS**: FastAPI's `allow_origins` must list the actual Vercel domain (`https://<project>.vercel.app`, plus any custom domain later) — never `*`, since the API accepts file uploads.

Local dev stays simple regardless of this split: `uvicorn backend.main:app --reload` for the API, `npm run dev` (Vite) for the frontend, same as today's `streamlit run app.py` in spirit — two commands instead of one, not a bigger leap than that.

## Build order

1. **FastAPI skeleton** — `backend/main.py`, `POST /api/analyze` wrapping `engine.statement.analyze()`, Pydantic schemas, error handling for `LockedPDFError`. Demonstrable: `curl -F file=@statement.pdf localhost:8000/api/analyze` returns correct JSON for a real sample.
2. **Excel export endpoint** — `POST /api/analyze/excel`, verified byte-identical output to what `app.py` produces today for the same file.
3. **Backend regression tests** — the 22-sample sweep, adapted to hit the API instead of calling `analyze()` directly.
4. **React scaffold** — Vite + TypeScript + Tailwind configured with `frontend.md`'s tokens, upload screen wired to `/api/analyze`, raw JSON rendered unstyled just to prove the pipe works end-to-end.
5. **Design system components** — KPI card, severity badge, tabs shell, styled per `frontend.md`.
6. **Results dashboard** — Overview, Fraud signals (with structured instance tables), Due date (with the average row), Monthly summary, Transactions (virtualized table) — one tab at a time, each checked against the same real sample set already used throughout this project.
7. **Excel download wired**, loading/error/empty states, polish pass (motion, focus states, responsive collapse below 1024px).
8. **Deploy** — Render for the backend, Vercel for the frontend (see Deployment above), CORS locked to the real Vercel domain.
9. **Retire `app.py`** once the React version has been run against the full 22-sample set and matches the Streamlit version's figures exactly.

## Open decisions (need your call before or during the build)

- **Auth, now that hosting is a public URL, not local-only.** Vercel/Render both give the app a real internet-reachable address. If real bank statements (PII, account numbers, transaction history) get uploaded to it, an unauthenticated public endpoint is a genuine exposure, not just a nice-to-have gap. At minimum this needs *something* before real data goes anywhere near it — even a single shared password gate is better than nothing. Needs a decision before Phase 8 (deploy), not after.
- **Keep `Sample Data/` and `.streamlit/` around** or clean them out once Streamlit is retired — `Sample Data/` is still useful as the regression fixture set regardless of frontend stack, `.streamlit/` becomes dead weight the moment `app.py` is deleted.
- **Server-side result caching** (the `GET /api/analyze/{id}/excel` alternative above) — worth building now or genuinely fine to defer, given re-parsing takes under 1.5s even for the largest sample tested.
