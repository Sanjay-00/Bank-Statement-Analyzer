"""
app.py - Streamlit UI for the Bank Statement Analyser.

Upload -> parse -> reconcile -> browse results in tabs -> download a
formatted Excel. Full-width, no sidebar. Each discrete item (a red flag, a
fraud signal, a due-date priority) gets its own bordered placeholder card
with a severity-accent left border - same pattern as the sibling FinSight
project's fs-card, adapted to this app's light/amber palette instead of
FinSight's dark theme - so a screen with many flags reads as a scannable
stack of separated cards rather than one continuous block of text.
"""

import pandas as pd
import streamlit as st

from engine.parser import LockedPDFError
from engine.statement import analyze
from engine.excel_generator import generate_excel, get_filename

st.set_page_config(
    page_title="Bank Statement Analyser",
    page_icon=":material/account_balance:",
    layout="wide",
)

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.7rem !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { font-size: 0.78rem !important; color: #666; }
    .stTabs [data-baseweb="tab-list"] { gap: 1.5rem; }
    .stTabs [data-baseweb="tab"] { font-size: 0.92rem; padding: 0.5rem 0.4rem; }
    hr { margin: 1.6rem 0 !important; }

    /* Warm amber pill CTA, matching the digitap.ai reference (frontend.md) -
       navy/white page, one warm accent reserved for actions, not the flatter
       theme default. Pill shape (not the 8px app-wide radius) marks these
       specifically as the page's calls to action. */
    button[kind="primary"], [data-testid="stBaseButton-primary"] {
        background-color: #F59E0B !important;
        border: 1px solid #F59E0B !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 999px !important;
        padding-left: 1.4rem !important;
        padding-right: 1.4rem !important;
        box-shadow: 0 1px 3px rgba(245, 158, 11, 0.35) !important;
        transition: background-color 0.15s ease-out, box-shadow 0.15s ease-out;
    }
    button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
        background-color: #D97706 !important;
        border-color: #D97706 !important;
        box-shadow: 0 2px 6px rgba(245, 158, 11, 0.45) !important;
    }
    button[kind="primary"]:disabled, [data-testid="stBaseButton-primary"]:disabled {
        background-color: #CBD5E1 !important;
        border-color: #CBD5E1 !important;
        box-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)

_SEVERITY_BADGE = {"HIGH": "red", "MEDIUM": "orange", "LOW": "blue"}
_SEVERITY_ICON = {
    "HIGH": ":material/error:",
    "MEDIUM": ":material/warning:",
    "LOW": ":material/info:",
}
# Solid-fill card palette (background/border/dot/text), one per severity - the
# FinSight reference tints the whole card, not just a border, so a screen of
# many flags reads by colour before anyone reads a word. GOOD is the same
# language for a clean checklist item (no risk equivalent, but a card can
# still report "fine" the same way FinSight's green checklist rows do).
_FILL = {
    "HIGH":   {"bg": "#FEF2F2", "border": "#FCA5A5", "dot": "#DC2626", "text": "#7F1D1D"},
    "MEDIUM": {"bg": "#FFFBEB", "border": "#FCD34D", "dot": "#D97706", "text": "#78350F"},
    "LOW":    {"bg": "#EFF6FF", "border": "#93C5FD", "dot": "#2563EB", "text": "#1E3A8A"},
    "GOOD":   {"bg": "#ECFDF5", "border": "#6EE7B7", "dot": "#059669", "text": "#065F46"},
    "NEUTRAL":{"bg": "#F8FAFC", "border": "#E2E8F0", "dot": "#64748B", "text": "#1E293B"},
    "ACCENT": {"bg": "#FFFBEB", "border": "#F59E0B", "dot": "#F59E0B", "text": "#78350F"},
    "VIOLET": {"bg": "#F5F3FF", "border": "#C4B5FD", "dot": "#7C3AED", "text": "#4C1D95"},
    "CYAN":   {"bg": "#ECFEFF", "border": "#67E8F9", "dot": "#0891B2", "text": "#164E63"},
    "ORANGE": {"bg": "#FFF7ED", "border": "#FDBA74", "dot": "#EA580C", "text": "#7C2D12"},
}
# Category -> palette status, a fixed per-category identity colour (not a
# risk severity) - salary/bounce reuse the green/red that already carry that
# meaning elsewhere in the app, the rest are just distinct accents so a grid
# of category cards reads as separated groups at a glance.
_CATEGORY_STATUS = {
    "salary": "GOOD", "emi": "VIOLET", "rent": "LOW", "bounce": "HIGH",
    "upi": "CYAN", "cash": "ORANGE", "charges": "MEDIUM",
    "interest": "NEUTRAL", "uncategorized": "NEUTRAL",
}


def _inr(value) -> str:
    if value is None:
        return "NA"
    return f"Rs. {value:,.0f}"


def _fill_css(keys_status: dict, extra: str = "") -> None:
    """Scoped solid-fill background+border for a set of st.container(key=...)
    cards, one <style> block per call (not one per card). `extra` is raw CSS
    appended inside each rule - e.g. padding/min-height for a card family
    that needs a bigger, more consistent footprint than the default."""
    rules = "".join(
        f'.st-key-{key} {{ background-color: {_FILL[status]["bg"]} !important; '
        f'border: 1px solid {_FILL[status]["border"]} !important; '
        f'border-radius: 10px !important; {extra} }}\n'
        for key, status in keys_status.items()
    )
    st.markdown(f"<style>{rules}</style>", unsafe_allow_html=True)


def _flag_card(key: str, sev: str, code: str, detail: str, instances=None) -> None:
    """One flag/signal, its own solid-fill placeholder card - colour by
    severity, a leading dot + title, detail line, optional evidence table.
    Mirrors the FinSight reference's filled checklist card."""
    c = _FILL[sev]
    with st.container(key=key, border=True):
        st.markdown(
            f'<span style="color:{c["dot"]};">●</span> '
            f'<span style="font-weight:700;color:{c["text"]};">{code.replace("_", " ").title()}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div style="color:{c["text"]}; opacity:0.85; font-size:0.85rem; margin-top:2px;">{detail}</div>',
                    unsafe_allow_html=True)
        if instances:
            inst_df = pd.DataFrame(instances)
            num_cols = [c2 for c2 in inst_df.columns if "Rs." in c2]
            st.dataframe(
                inst_df,
                hide_index=True,
                width="stretch",
                height=min(38 * (len(inst_df) + 1) + 3, 250),
                column_config={
                    c2: st.column_config.NumberColumn(c2, format="Rs. %.2f")
                    for c2 in num_cols
                },
            )


def _category_card(key: str, status: str, label: str, txns: int,
                    debit: float, credit: float, net: float) -> None:
    """One category, its own solid-fill card - identity colour by category
    (not severity), title + txn count up top, Debit/Credit/Net as a mini
    stat row below. Sized via the CATEGORY_CARD_CSS padding/min-height so
    every card in the grid matches regardless of title length."""
    c = _FILL[status]
    with st.container(key=key, border=True):
        st.markdown(
            f'<span style="color:{c["dot"]};">●</span> '
            f'<span style="font-weight:700; font-size:1.05rem; color:{c["text"]};">{label}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="color:{c["text"]}; opacity:0.7; font-size:0.78rem; margin-top:1px;">{txns} txn(s)</div>',
            unsafe_allow_html=True,
        )
        st.space("small")
        stat_cols = st.columns(3)
        for col, stat_label, value in zip(
            stat_cols, ("Debit", "Credit", "Net"), (debit, credit, net)
        ):
            col.markdown(
                f'<div style="font-size:0.66rem; font-weight:700; letter-spacing:0.03em; '
                f'text-transform:uppercase; color:{c["text"]}; opacity:0.6;">{stat_label}</div>'
                f'<div style="font-size:1rem; font-weight:700; color:{c["text"]}; margin-top:1px;">{_inr(value)}</div>',
                unsafe_allow_html=True,
            )


def _card_grid(items: list, render_fn, n_cols: int = 2) -> None:
    """Lay `items` into an n-column grid, FinSight-style, instead of one
    long vertical stack - each render_fn(item) draws one card. A small
    spacer after every card keeps cards stacked in the same column from
    touching, without ballooning into empty space."""
    cols = st.columns(n_cols)
    for i, item in enumerate(items):
        with cols[i % n_cols]:
            render_fn(item, i)
            st.space("small")


def _kpi_box(key: str, label: str, value: str, status: str = "NEUTRAL") -> None:
    """One solid-fill KPI tile (uppercase label + big value), FinSight-style,
    in place of a bare st.metric floating on the page."""
    c = _FILL[status]
    with st.container(key=key, border=True):
        st.markdown(
            f'<div style="font-size:0.68rem; font-weight:700; letter-spacing:0.04em; '
            f'text-transform:uppercase; color:{c["text"]}; opacity:0.7;">{label}</div>'
            f'<div style="font-size:1.55rem; font-weight:700; color:{c["text"]}; margin-top:2px;">{value}</div>',
            unsafe_allow_html=True,
        )


st.markdown("## :material/account_balance: Bank statement analyser")
st.caption("Upload a bank statement PDF to extract, reconcile, and analyse its transactions.")
st.divider()

uploaded = st.file_uploader("Upload a bank statement (PDF)", label_visibility="visible", type=["pdf"])
st.space("small")

col_btn, col_pwd, _ = st.columns([1, 2, 2])
with col_btn:
    run = st.button("Analyze", type="primary", icon=":material/bolt:", disabled=not uploaded)
with col_pwd:
    password = st.text_input(
        "PDF password", type="password", label_visibility="collapsed",
        placeholder="PDF password, only if locked",
    ) or None

if uploaded and run:
    file_bytes = uploaded.getvalue()
    try:
        with st.spinner("Extracting and reconciling transactions...", show_time=True):
            result = analyze(file_bytes, password=password)
    except LockedPDFError:
        st.error(
            "This statement is password-protected and the password above "
            "didn't unlock it (or none was supplied). Enter the PDF's "
            "password and try again.",
            icon=":material/lock:",
        )
        st.stop()
    st.session_state["result"] = result
    st.session_state["file_name"] = uploaded.name

if "result" not in st.session_state:
    st.stop()

result = st.session_state["result"]
s = result.summary

st.divider()

left, right = st.columns([3, 1])
with left:
    st.markdown(f"### {result.bank_name}")
    if result.account_holder:
        st.caption(f"Account holder: {result.account_holder}")
with right:
    high_fraud = sum(1 for f in result.fraud_signals if f.get("severity") == "HIGH")
    if result.bank_key is None:
        st.badge("Bank not recognised", icon=":material/help:", color="gray")
    elif high_fraud:
        st.badge(f"{high_fraud} high-severity signal(s)", icon=":material/error:", color="red")
    elif result.fraud_signals:
        st.badge(f"{len(result.fraud_signals)} signal(s) to review", icon=":material/warning:", color="orange")
    else:
        st.badge("No fraud signals", icon=":material/verified:", color="green")

if result.scanned_pages:
    st.caption(
        f":material/document_scanner: {result.scanned_pages} of {result.page_count} pages look scanned "
        "(no digital text layer) and were skipped. OCR support for scans is a later phase, not yet built."
    )

st.space("small")

failed_n = s["counts"].get("FAILED", 0)
unverified_n = s["counts"].get("UNVERIFIED", 0)
verified_n = s["counts"].get("VERIFIED", 0)
all_verified = s["transaction_count"] > 0 and verified_n == s["transaction_count"]

# Only the metrics that actually signal something get colour - a healthy 0
# for Failed/Check-statement is quiet good news (green), a nonzero count is
# the one number on this row that needs attention (red/amber), everything
# else stays the plain neutral tile. FinSight-style solid-fill KPI tiles
# rather than bare st.metric floating on the page.
_fill_css({
    "kpi_txns": "NEUTRAL",
    "kpi_verified": "GOOD" if all_verified else "NEUTRAL",
    "kpi_failed": "HIGH" if failed_n else "GOOD",
    "kpi_check": "MEDIUM" if unverified_n else "GOOD",
    "kpi_open": "NEUTRAL",
    "kpi_close": "NEUTRAL",
})
m1, m2, m3, m4, m5, m6 = st.columns(6)
with m1:
    _kpi_box("kpi_txns", "Transactions", str(s["transaction_count"]), "NEUTRAL")
with m2:
    _kpi_box("kpi_verified", "Verified", str(verified_n), "GOOD" if all_verified else "NEUTRAL")
with m3:
    _kpi_box("kpi_failed", "Failed", str(failed_n), "HIGH" if failed_n else "GOOD")
with m4:
    _kpi_box("kpi_check", "Check statement", str(unverified_n), "MEDIUM" if unverified_n else "GOOD")
with m5:
    _kpi_box("kpi_open", "Opening balance", _inr(s["opening_balance"]), "NEUTRAL")
with m6:
    _kpi_box("kpi_close", "Closing balance", _inr(s["closing_balance"]), "NEUTRAL")

if s["counts"].get("FAILED", 0):
    st.caption(
        f":material/rule: {s['counts']['FAILED']} row(s) failed reconciliation, flagged "
        "in the Transactions tab rather than silently included. Check "
        "those rows against the source PDF before relying on the totals."
    )

st.divider()

tab_overview, tab_flags, tab_fraud, tab_due, tab_cashflow, tab_cat, tab_txns = st.tabs([
    "Overview",
    f"Red flags ({len(result.red_flags)})",
    f"Fraud signals ({len(result.fraud_signals)})",
    "Due date",
    "Cash flow",
    "Categories",
    f"Transactions ({s['transaction_count']})",
])

with tab_overview:
    st.caption("At-a-glance dashboard. Every number here has a dedicated tab with the full detail.")

    with st.container(border=True):
        st.markdown("#### Cash-flow score")
        score = result.score
        fd = score["foir_dscr"]
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Composite score", f"{score['score']:.0f} / 1000",
                   help="Policy-default weights, not a fitted model - see components below.")
        sc2.metric("FOIR", f"{fd['foir']:.0f}%" if fd["foir"] is not None else "NA",
                   help=fd["foir_band"] or "No fixed obligations (EMI/rent) detected.")
        sc3.metric("DSCR", f"{fd['dscr']:.2f}" if fd["dscr"] is not None else "NA",
                   help=fd["dscr_band"] or "No EMI debt service detected.")
        sc4.metric("Volatility", f"{score['volatility']:.2f}", help="0 = stable income, 1 = volatile")
        with st.expander("Score components & FOIR/DSCR detail"):
            comp_df = pd.DataFrame([
                {"Component": k.replace("_", " ").title(), "Score (0-100)": v, "Weight": score["weights"][k]}
                for k, v in score["components"].items()
            ])
            st.dataframe(comp_df, hide_index=True, width="stretch")
            st.caption(
                f"Estimated monthly income: {_inr(fd['monthly_income']) if fd['monthly_income'] else 'NA'} "
                f"({fd['income_source'] or 'NA'}) - fixed obligations: {_inr(fd['monthly_fixed_obligations'])} "
                f"- {fd['months_used']} month(s) used - red-flag penalty: -{score['red_flag_penalty']}"
            )

    st.space("small")

    with st.container(border=True):
        st.markdown("#### Average bank balance")
        abb = result.abb
        ac1, ac2, ac3, ac4 = st.columns(4)
        for col, w in zip((ac1, ac2, ac3, ac4), (1, 3, 6, 12)):
            win = abb["windows"].get(w, {})
            avg = win.get("average")
            col.metric(
                f"ABB{w}",
                _inr(avg) if avg is not None else "NA",
                help=None if avg is not None else
                     f"Not enough history - {win.get('covered_days', 0)}/{win.get('total_days', 0)} days covered",
            )

    st.space("small")

    with st.container(border=True):
        st.markdown("#### Signals at a glance")
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("Red flags & fraud signals")
            flag_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for f in result.red_flags + result.fraud_signals:
                flag_counts[f.get("severity", "LOW")] = flag_counts.get(f.get("severity", "LOW"), 0) + 1
            if any(flag_counts.values()):
                st.markdown(
                    " ".join(
                        f":{_SEVERITY_BADGE[sev]}-badge[{sev.title()}: {n}]"
                        for sev, n in flag_counts.items() if n
                    )
                )
            else:
                st.badge("Clean, no signals", icon=":material/verified:", color="green")
            st.caption(f"{len(result.red_flags)} red flag(s), {len(result.fraud_signals)} fraud signal(s) - see their tabs for details.")
        with col_b:
            st.caption("Recommended EMI due date")
            dda = result.due_date_analysis
            if dda["recommendations"]:
                top = dda["recommendations"][0]
                st.metric(f"Priority 1: {top['due_date']} of the month", _inr(top["avg_balance"]))
                st.caption(f"Based on the last {dda['months_used']} month(s) - see the Due date tab for all priorities.")
            else:
                st.caption("Not enough reconciled data to recommend a due date.")

with tab_flags:
    if not result.red_flags:
        st.success("No red flags raised.", icon=":material/verified:")
    else:
        st.caption(
            "Each flag reads a number already computed elsewhere (ABB, salary "
            "consistency, bounce frequency, cash-flow ratios) against a "
            "threshold - the detail line always names the number that triggered it."
        )
        _fill_css({
            f"rf_{i}": flag.get("severity", "LOW")
            for i, flag in enumerate(result.red_flags)
        })

        def _render_rf(flag, i):
            _flag_card(
                f"rf_{i}", flag.get("severity", "LOW"),
                flag.get("code", ""), flag.get("detail", ""), flag.get("instances"),
            )

        _card_grid(result.red_flags, _render_rf)

with tab_fraud:
    if not result.fraud_signals:
        st.success("No fraud/tamper signals detected.", icon=":material/verified:")
    else:
        st.caption(
            "Cheap, deterministic checks only (PDF metadata, edit-history, "
            "font consistency, round-tripping, duplicates, round-number "
            "clustering). Each is a signal to look at, not a verdict."
        )
        _fill_css({
            f"fs_{i}": sig.get("severity", "LOW")
            for i, sig in enumerate(result.fraud_signals)
        })

        def _render_fs(sig, i):
            _flag_card(
                f"fs_{i}", sig.get("severity", "LOW"),
                sig.get("code", ""), sig.get("detail", ""), sig.get("instances"),
            )

        _card_grid(result.fraud_signals, _render_fs)

with tab_due:
    dda = result.due_date_analysis
    if not dda["recommendations"]:
        st.info("Not enough reconciled data to recommend a due date.", icon=":material/info:")
    else:
        st.caption(
            f"Closing balance on the 4th/9th/14th/19th of each month (the day "
            f"before the 5th/10th/15th/20th due dates), averaged over the last "
            f"{dda['months_used']} month(s) of this statement."
        )
        _fill_css({
            f"due_{rec['priority']}": "ACCENT" if rec["priority"] == 1 else "NEUTRAL"
            for rec in dda["recommendations"]
        })
        cols = st.columns(len(dda["recommendations"]))
        for col, rec in zip(cols, dda["recommendations"]):
            with col:
                _kpi_box(
                    f"due_{rec['priority']}",
                    f"Priority {rec['priority']}: {rec['due_date']}",
                    _inr(rec["avg_balance"]),
                    "ACCENT" if rec["priority"] == 1 else "NEUTRAL",
                )
                st.caption(f"Avg. closing balance on the {rec['anchor_day']}th")

        st.space("small")
        st.markdown("**Month-by-month closing balance on each anchor day**")
        st.caption(f"Average row reflects the last {dda['months_used']} month(s), same window as the recommendation above.")
        rows = []
        for row in dda["monthly"]:
            rows.append({
                "Month": f"{row['year']}-{row['month']:02d}",
                "4th (→ 5th due)": row.get(4),
                "9th (→ 10th due)": row.get(9),
                "14th (→ 15th due)": row.get(14),
                "19th (→ 20th due)": row.get(19),
            })
        rows.append({
            "Month": "Average",
            "4th (→ 5th due)": dda["averages"].get(4),
            "9th (→ 10th due)": dda["averages"].get(9),
            "14th (→ 15th due)": dda["averages"].get(14),
            "19th (→ 20th due)": dda["averages"].get(19),
        })
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            width="stretch",
            column_config={
                c: st.column_config.NumberColumn(c, format="Rs. %.0f")
                for c in ["4th (→ 5th due)", "9th (→ 10th due)",
                          "14th (→ 15th due)", "19th (→ 20th due)"]
            },
        )

with tab_cashflow:
    if not result.monthly:
        st.info("No dated transactions to summarize.", icon=":material/info:")
    else:
        with st.container(border=True):
            st.markdown("#### Monthly totals")
            rows = []
            for (year, month), b in result.monthly.items():
                rows.append({
                    "Month": f"{year}-{month:02d}",
                    "Total debit": b["debit"],
                    "Total credit": b["credit"],
                    "Net": b["net"],
                    "Txns": b["txn_count"],
                })
            st.dataframe(
                pd.DataFrame(rows),
                hide_index=True,
                width="stretch",
                column_config={
                    "Total debit": st.column_config.NumberColumn("Total debit", format="Rs. %.0f"),
                    "Total credit": st.column_config.NumberColumn("Total credit", format="Rs. %.0f"),
                    "Net": st.column_config.NumberColumn("Net", format="Rs. %.0f"),
                },
            )
            st.space("small")
            chart_df = pd.DataFrame([
                {"Month": f"{y}-{m:02d}", "Net": b["net"]}
                for (y, m), b in result.monthly.items()
            ])
            st.bar_chart(chart_df, x="Month", y="Net")

        st.space("small")

        with st.container(border=True):
            st.markdown("#### Salary & bounces")
            col_a, col_b = st.columns(2)
            with col_a:
                sal = result.salary
                if sal["detected"]:
                    st.write(
                        f"Salary detected - {sal['months_with_salary']}/{sal['months_covered']} "
                        f"month(s) ({sal['recurrence_rate']:.0%} recurrence)"
                        + (", **irregular**" if sal["irregular"] else ", regular")
                    )
                else:
                    st.write("No salary-pattern credit detected.")
            with col_b:
                bnc = result.bounces
                st.write(f"Bounces/returns: **{bnc['count']}**" + (
                    f" ({bnc['rate_per_month']:.1f}/month)" if bnc["rate_per_month"] else ""
                ))

        st.space("small")

        with st.container(border=True):
            st.markdown("#### Cash-flow ratios")
            cf = result.cashflow
            cdr = cf.get("cash_dependency_ratio")
            ec = cf.get("expense_concentration")
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"Cash dependency: **{cdr:.0%}**" if cdr is not None else "Cash dependency: NA")
            with col_b:
                st.write(f"Expense concentration: **{ec['ratio']:.0%}** in \"{ec['category'].title()}\"" if ec else "Expense concentration: NA")

with tab_cat:
    if not result.category_summary:
        st.info("No dated transactions to categorize.", icon=":material/info:")
    else:
        st.caption(
            "Rule-based narration matching (salary, EMI, rent, bounce/NSF, UPI, "
            "cash, charges). Uncategorized means no rule matched confidently, "
            "not a guess - a transaction never gets forced into the nearest-looking bucket."
        )
        cat_rows = [
            {
                "cat": cat,
                "Category": cat.replace("_", " ").title(),
                "Txns": b["count"],
                "Total debit": b["total_debit"],
                "Total credit": b["total_credit"],
                "Net": b["total_credit"] - b["total_debit"],
            }
            for cat, b in result.category_summary.items()
        ]
        _fill_css(
            {f"cat_{r['cat']}": _CATEGORY_STATUS.get(r["cat"], "NEUTRAL") for r in cat_rows},
            extra="padding: 1.25rem 1.5rem !important; min-height: 148px;",
        )

        def _render_cat(r, i):
            _category_card(
                f"cat_{r['cat']}", _CATEGORY_STATUS.get(r["cat"], "NEUTRAL"),
                r["Category"], r["Txns"], r["Total debit"], r["Total credit"], r["Net"],
            )

        _card_grid(cat_rows, _render_cat, n_cols=3)

        st.space("small")
        with st.expander("Raw table"):
            st.dataframe(
                pd.DataFrame([{k: v for k, v in r.items() if k != "cat"} for r in cat_rows]),
                hide_index=True,
                width="stretch",
                column_config={
                    "Total debit": st.column_config.NumberColumn("Total debit", format="Rs. %.0f"),
                    "Total credit": st.column_config.NumberColumn("Total credit", format="Rs. %.0f"),
                    "Net": st.column_config.NumberColumn("Net", format="Rs. %.0f"),
                },
            )

        st.space("small")
        chart_df = pd.DataFrame([
            {"Category": r["Category"], "Amount": r["Total debit"] + r["Total credit"]}
            for r in cat_rows
        ])
        st.bar_chart(chart_df, x="Category", y="Amount")

with tab_txns:
    df = pd.DataFrame([{
        "Date": t.date,
        "Narration": t.narration,
        "Chq/Ref": t.chq_ref or "",
        "Debit": t.debit,
        "Credit": t.credit,
        "Balance": t.balance,
        "Category": (t.category or "uncategorized").replace("_", " ").title(),
        "Status": t.status,
    } for t in result.transactions])
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        height=520,
        column_config={
            "Debit": st.column_config.NumberColumn("Debit", format="Rs. %.2f"),
            "Credit": st.column_config.NumberColumn("Credit", format="Rs. %.2f"),
            "Balance": st.column_config.NumberColumn("Balance", format="Rs. %.2f"),
            "Category": st.column_config.TextColumn("Category", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )

st.divider()
st.space("small")
_, dl_col, _ = st.columns([1, 3, 1])
with dl_col:
    excel_bytes = generate_excel(result)
    excel_filename = get_filename(result.bank_name, result.account_holder)
    st.download_button(
        f"Download Excel report - {excel_filename}",
        data=excel_bytes,
        file_name=excel_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        icon=":material/download:",
        width="stretch",
    )
