# Frontend design system — Bank Statement Analyser

Design reference for the React rewrite. This is a working tool for credit analysts, not a marketing site — the standard here is Mercury / Ramp / Brex-grade "fintech ops" polish: calm, dense, fast, trustworthy. It should look like software a bank would actually run, not a demo.

Standalone product. No "Underwriting Intelligence Platform" suite branding anywhere in the UI copy.

## Design philosophy

The subject is a ledger — reconciled, verified, audited. The design should feel like that: precise, tabular, quietly confident. Not playful, not generic-SaaS-purple. The one visual idea worth committing to: **numbers are the product**. Every screen should make the numbers easier to trust and scan, not compete with them for attention.

Avoid the current-generation AI-SaaS look: no purple-to-blue gradient hero, no Inter-by-default with zero justification, no `rounded-lg` on literally everything, no accent-bar-on-card cliché, no emoji as section markers.

**External reference validated**: [digitap.ai's bank statement analyzer page](https://www.digitap.ai/bank-statement-analyzer-api.html) — white ground, restrained color (accent used only in nav/CTAs, not decoration), large clear section headings with generous whitespace between blocks, simple SVG icons instead of photography or illustration, a numbered grid for feature listing rather than a wall of cards. That's the right minimal register for this product too — it confirms the direction already set above (numbers-are-the-product, no decorative color) rather than changing it. Two things worth pulling in explicitly for the dashboard itself, not just a marketing page: (1) don't let a section header and its content crowd each other — the whitespace *is* the hierarchy, not a bolded label; (2) prefer a plain numbered/labelled list over an icon-in-a-box card grid for feature-style content (e.g. the fraud-signal list, the red-flag list) — it reads calmer at the density this tool needs.

## Color

Named tokens, not raw hex scattered through components. Values match the Streamlit POC's `.streamlit/config.toml` exactly (not just in spirit) so the eventual React build and the current working tool never visually disagree.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--ink` | `#1E293B` | `#F1F5F9` | Primary text |
| `--accent` | `#F59E0B` | `#FBBF24` | Primary accent — CTAs, links, active states, focus rings |
| `--paper` | `#FFFFFF` | `#0F172A` | App background |
| `--surface` | `#F3F6FB` | `#1E293B` | Cards, table rows, panels |
| `--border` | `#E2E8F0` | `#334155` | Hairlines, dividers, input borders |
| `--muted` | `#64748B` | `#94A3B8` | Secondary text, captions, placeholder |

Superseded: earlier drafts of this doc specified a deep teal-green accent (named `--ledger`) as a departure from generic fintech blue. Overridden by a concrete external reference the user pointed at — [digitap.ai's bank statement analyzer page](https://www.digitap.ai/bank-statement-analyzer-api.html) — which uses navy text on a plain white ground with one warm amber accent reserved for calls to action. That reference wins over the abstract preference for a green-tinted neutral: `--accent` is now amber (`#F59E0B` light / `#FBBF24` dark, matching what's already live in the Streamlit POC), and `--paper` is plain white rather than green-tinted, matching the reference and this project's own already-shipped theme rather than a hypothetical ideal.

**Semantic color is separate from the accent** and never doubles as decoration:

| Token | Light | Dark | Meaning |
|---|---|---|---|
| `--good` | `#1A7F4E` | `#4ADE9C` | Verified, reconciled, no signal |
| `--warn` | `#9A6B00` | `#F2B84B` | Medium-severity signal, needs review |
| `--critical` | `#B3261E` | `#FF6B5E` | High-severity signal, failed reconciliation |
| `--info` | `#3E5C76` | `#7FA8C9` | Low-severity, informational |

Reused consistently: fraud severity badges, reconciliation status chips, metric deltas, chart accents for debit/credit. Never introduce a second decorative accent color — every non-neutral color on screen means something.

### Dark mode

Light is the default, matching the digitap reference and the Streamlit POC's own theme; dark is fully supported for long analyst sessions, not an afterthought. Both are real token sets, not an inverted filter — `--paper` in dark mode is `#0F172A`, a navy-black, not pure `#000000`, and `--accent` shifts from `#F59E0B` to a slightly brighter `#FBBF24` so it still carries the same perceived weight against the darker ground.

## Typography

Two faces, both doing real work:

- **UI / body — Public Sans.** Geometric-humanist, used across US federal financial and government digital services — it reads as institutional and legible at small sizes without being the generic Inter/Space Grotesk default. Weights: 400 (body), 500 (labels, table headers), 600 (headings), 700 (page title only).
- **Figures — IBM Plex Mono.** Every rupee amount, balance, date, and reference number renders in this face with `font-variant-numeric: tabular-nums`. This is the single biggest driver of a "real ledger" feel: monospaced figures align vertically in tables the way they do on an actual bank statement, and it visually separates "data" from "label" at a glance without color or weight tricks.

Type scale (rem, 16px root):

| Role | Size | Weight | Face |
|---|---|---|---|
| Page title | 1.5 | 700 | Public Sans |
| Section heading | 1.125 | 600 | Public Sans |
| Body / table cell text | 0.875 | 400 | Public Sans |
| Label / table header / caption | 0.75 | 500, uppercase, +0.02em tracking | Public Sans |
| KPI stat value | 1.75 | 600 | IBM Plex Mono |
| Table figures (amounts, dates) | 0.875 | 500 | IBM Plex Mono |

Both are Google Fonts (no license cost, no CDN-fallback risk if self-hosted via `next/font` or a build-time download — don't link the Google Fonts CSS URL directly in production, vendor the woff2 files).

## Layout

12-column grid, max content width **1440px**, 24px page gutters, 8px base spacing unit (all gaps/padding are multiples of 8, occasionally 4 for tight table cells). No sidebar (matches the decision already made for the Streamlit version) — a slim top bar (product name, upload action, theme toggle) and the page body is the entire canvas below it. Sections separated by whitespace and hairline dividers, not boxed cards stacked on boxed cards — reserve `--surface` card backgrounds for genuinely distinct groupings (the KPI row, a data table), not for every paragraph.

Breakpoints: this is a desktop-first analyst tool (nobody reconciles a 300-page statement on a phone), but the layout should not break below 1024px — collapse the KPI row from 6 columns to 3×2, and let tables scroll horizontally inside their own container rather than the page.

## Core screens

**Upload / empty state.** A single, calm dropzone as the entire hero — no illustration, no marketing copy. Drag state highlights the dropzone border in `--accent`. Below it, a one-line trust statement ("Processed locally, nothing leaves this session until you download") if that's actually true for the deployed architecture — don't write it if it isn't.

**Results dashboard.** Top bar → bank name + status chip (reconciliation health, fraud signal count) on one row → KPI stat row (6 cards: transactions, verified, failed, check-statement, opening, closing) → tabbed content (Overview, Fraud signals, Due date, Monthly summary, Transactions). This mirrors the Streamlit IA because it's already been validated with real files — the rewrite changes the skin, not the information architecture, unless something in it is actually broken.

**KPI stat card.** Label (caption style, `--muted`) above a large `IBM Plex Mono` value. A colored 2px left rule in semantic color only when the metric itself is a signal (Failed > 0 → `--critical` rule; 0 → no rule at all, not a green one — silence is the "everything's fine" state, not a green flourish).

**Severity badge / status chip.** Pill shape, `--good`/`--warn`/`--critical`/`--info` background at 12% opacity with full-opacity text and a small dot, not a Material-style filled badge — quieter, sits well in a dense table row.

**Data table (Transactions).** This is the highest-stakes surface in the app — 300-2900+ rows in real files tested. Requirements: virtualized rendering (TanStack Virtual), sticky header, tabular-nums right-aligned amount columns, sortable by date/amount, a text filter over narration, and the amber "Check Statement" row treatment carried over from the Excel/Streamlit convention (a subtle `--warn`-tinted row background, not just a text label) so an unreconciled row is visible while scanning, not just readable.

**Charts.** Monthly net cash-flow bar chart and (later) an ABB trend sparkline. Debit bars in `--critical`-adjacent muted red, credit bars in `--good`-adjacent muted green, at reduced saturation from the semantic-status colors so the chart doesn't read as an alarm. Faint gridlines, no 3D, no gradient fills. Recharts is sufficient for v1; move to visx only if a custom interaction (brush-to-filter transactions by date range) is actually built.

**Fraud signal card.** Severity badge + signal name on one line, one-sentence explanation below, and — where the signal has structured instances (round-tripping pairs, duplicate transactions) — a small inline table, never a wall of concatenated text. This was a real bug found and fixed in the Streamlit version; carry the fix's *shape* (structured data, not string-templated prose) into the API contract itself so the frontend never has to re-parse a sentence to render a table.

**Due-date recommendation.** Ranked priority cards (1st/2nd/3rd/4th), each showing the due date, the anchor day it's based on, and the average balance — priority 1 visually heavier (larger value, `--accent` accent) than 2-4, which recede to `--muted` framing. This is a recommendation, not four equal options.

## States

- **Loading**: skeleton screens shaped like the real content (skeleton KPI cards, skeleton table rows), not a centered spinner — the layout shouldn't jump when data arrives.
- **Empty**: every tab needs a real empty state (no fraud signals, no monthly data) with a one-line explanation, not a blank panel.
- **Error**: specific and actionable ("This PDF is password-protected — enter the password above and try again"), never a raw exception.
- **Partial data**: scanned pages skipped, some rows unverified — these are normal outcomes of this domain, not errors; treat them as informational banners (`--info` or `--warn`, never `--critical` unless reconciliation actually failed).

## Motion

Minimal and functional: 150ms ease-out for hover/focus states, 200ms for tab transitions, skeleton shimmer while loading. No page-load choreography, no scroll-triggered reveals — this is a tool that gets opened dozens of times a day; motion that's charming once is friction on the fortieth use. Respect `prefers-reduced-motion` throughout.

## Accessibility

WCAG AA minimum. Every color pair above is chosen to clear 4.5:1 for text. Keyboard focus states are visible (a 2px `--accent` outline, never `outline: none` without a replacement). Table sort/filter controls are reachable and announced. Status conveyed by color always has a second channel (icon or text), per the severity badge design above.

## Tech stack

- **Vite + React + TypeScript.** No Next.js needed — this isn't a marketing site with SEO requirements, and a pure SPA behind FastAPI is simpler to deploy as one unit.
- **Tailwind CSS**, configured with the tokens above as theme values (not ad hoc utility colors) — `bg-surface`, `text-ink`, `border-border`, etc.
- **Radix UI primitives** (or shadcn/ui, which is Radix + Tailwind pre-wired) for tabs, dialogs, tooltips, dropdowns — accessible by default, unstyled enough to actually look like this system rather than shadcn's default look.
- **TanStack Query** for API state (upload → analyze → cache result by file hash, matching the Streamlit version's session-state caching behavior).
- **TanStack Table + TanStack Virtual** for the transactions grid.
- **Recharts** for the cash-flow bar chart.
- **Zod** to validate the FastAPI response shape at the client boundary — catches backend/frontend contract drift immediately in dev rather than as a runtime crash.

## File structure

```
frontend/
  src/
    components/
      ui/              # Radix/shadcn primitives styled to this system
      kpi-card.tsx
      severity-badge.tsx
      fraud-signal-card.tsx
      due-date-card.tsx
      transactions-table.tsx
      cashflow-chart.tsx
    pages/
      upload.tsx
      results.tsx
    lib/
      api.ts           # typed fetch wrappers + Zod schemas matching the FastAPI response models
      format.ts         # INR formatting, date formatting, tabular-nums helpers
    styles/
      tokens.css         # the color/type tokens as CSS custom properties, light + dark
    App.tsx
  index.html
  tailwind.config.ts
  vite.config.ts
```
