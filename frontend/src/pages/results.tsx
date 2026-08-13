import {
  AlertTriangle,
  Banknote,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  Download,
  HelpCircle,
  Landmark,
  Loader2,
  ScanLine,
  ShieldAlert,
  TrendingUp,
  Upload as UploadIcon,
  Wallet,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Children, useState, type ComponentType, type ReactNode } from "react";
import { CashflowChart } from "../components/cashflow-chart";
import { CategoryTable } from "../components/category-table";
import { DueDateCard } from "../components/due-date-card";
import { KpiCard } from "../components/kpi-card";
import { Panel } from "../components/panel";
import { SeverityBadge } from "../components/severity-badge";
import { SignalCard } from "../components/signal-card";
import { TopNav } from "../components/top-nav";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Tooltip } from "../components/ui/tooltip";
import { TransactionsTable } from "../components/transactions-table";
import { fmtInr, fmtPercent, titleCase } from "../lib/format";
import type { AnalysisResponse } from "../lib/schema";

interface ResultsPageProps {
  result: AnalysisResponse;
  onDownload: () => void;
  downloading: boolean;
  onReset: () => void;
  dark: boolean;
  onToggleTheme: () => void;
}

export function ResultsPage({ result, onDownload, downloading, onReset, dark, onToggleTheme }: ResultsPageProps) {
  const { summary, due_date_analysis, red_flags, fraud_signals, salary, bounces, cashflow } = result;

  const failedN = summary.counts.FAILED ?? 0;
  const unverifiedN = summary.counts.UNVERIFIED ?? 0;
  const verifiedN = summary.counts.VERIFIED ?? 0;
  const allVerified = summary.transaction_count > 0 && verifiedN === summary.transaction_count;

  const highFraud = fraud_signals.filter((f) => f.severity === "HIGH").length;
  const totalSignals = red_flags.length + fraud_signals.length;

  return (
    <div>
      <TopNav dark={dark} onToggleTheme={onToggleTheme} onLogoClick={onReset} />
      <div className="max-w-[1440px] mx-auto px-6 py-6">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-1">
        <div>
          <div className="flex items-baseline gap-2">
            <h1 className="text-xl font-bold">{result.bank_name}</h1>
            {result.bank_key === null && (
              <span className="text-xs text-muted">(bank not recognised)</span>
            )}
          </div>
          {result.account_holder && (
            <p className="text-xs text-muted mt-0.5">Account holder: {result.account_holder}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {highFraud > 0 ? (
            <span className="inline-flex items-center gap-1.5 text-sm text-critical">
              <AlertTriangle className="h-4 w-4" /> {highFraud} high-severity signal(s)
            </span>
          ) : totalSignals > 0 ? (
            <span className="inline-flex items-center gap-1.5 text-sm text-warn">
              <AlertTriangle className="h-4 w-4" /> {totalSignals} signal(s) to review
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-sm text-good">
              <CheckCircle2 className="h-4 w-4" /> No signals
            </span>
          )}
          <div className="h-5 w-px bg-border" />
          <button
            onClick={onReset}
            className="inline-flex items-center gap-2 border border-border rounded-full px-4 py-2 text-sm font-semibold hover:border-ink/30 hover:bg-surface transition-colors"
          >
            <UploadIcon className="h-3.5 w-3.5" />
            New upload
          </button>
          <button
            onClick={onDownload}
            disabled={downloading}
            className="inline-flex items-center gap-2 bg-accent text-ink rounded-full px-4 py-2 text-sm font-bold hover:brightness-95 disabled:opacity-50 transition-[filter] shadow-[0_4px_14px_rgb(var(--accent)/0.3)]"
          >
            {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
            {downloading ? "Preparing" : "Download Excel"}
          </button>
        </div>
      </div>

      {result.scanned_pages > 0 && (
        <div className="flex items-center gap-2 text-xs text-info mb-4">
          <ScanLine className="h-3.5 w-3.5" />
          {result.scanned_pages} of {result.page_count} pages look scanned (no digital text layer) and were skipped.
        </div>
      )}

      <div className="h-6" />

      {/* KPI row */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-8">
        <KpiCard
          label="Transactions"
          value={summary.transaction_count.toLocaleString("en-IN")}
          countFrom={summary.transaction_count}
          format={(n) => n.toLocaleString("en-IN")}
        />
        <KpiCard
          label="Verified"
          value={verifiedN.toLocaleString("en-IN")}
          countFrom={verifiedN}
          format={(n) => n.toLocaleString("en-IN")}
          signal={allVerified ? "good" : undefined}
          help="Rows where the running balance matches the row before it exactly (opening + credit - debit = closing)."
        />
        <KpiCard
          label="Failed"
          value={failedN.toLocaleString("en-IN")}
          countFrom={failedN}
          format={(n) => n.toLocaleString("en-IN")}
          signal={failedN > 0 ? "critical" : undefined}
          help="Rows where the running balance doesn't reconcile. Flagged, not silently included in totals. See the Transactions tab."
        />
        <KpiCard
          label="Check statement"
          value={unverifiedN.toLocaleString("en-IN")}
          countFrom={unverifiedN}
          format={(n) => n.toLocaleString("en-IN")}
          signal={unverifiedN > 0 ? "warn" : undefined}
          help="Rows where an amount or balance couldn't be read confidently, so no reconciliation check could run at all."
        />
        <KpiCard
          label="Opening balance"
          value={fmtInr(summary.opening_balance)}
          countFrom={summary.opening_balance ?? undefined}
          format={(n) => fmtInr(n)}
          help="The statement's printed opening balance, or NA if no opening-balance row was found."
        />
        <KpiCard
          label="Closing balance"
          value={fmtInr(summary.closing_balance)}
          countFrom={summary.closing_balance ?? undefined}
          format={(n) => fmtInr(n)}
          help="The running balance after the last transaction in this statement."
        />
      </div>

      {failedN > 0 && (
        <p className="text-xs text-muted -mt-6 mb-8">
          {failedN} row(s) failed reconciliation - flagged in the Transactions tab rather than silently included.
        </p>
      )}

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="redflags">Red flags ({red_flags.length})</TabsTrigger>
          <TabsTrigger value="fraud">Fraud signals ({fraud_signals.length})</TabsTrigger>
          <TabsTrigger value="duedate">Due date</TabsTrigger>
          <TabsTrigger value="cashflow">Cash flow</TabsTrigger>
          <TabsTrigger value="categories">Categories</TabsTrigger>
          <TabsTrigger value="transactions">Transactions ({summary.transaction_count})</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab result={result} />
        </TabsContent>

        <TabsContent value="redflags">
          {red_flags.length === 0 ? (
            <EmptyState message="No red flags raised." />
          ) : (
            <div className="grid sm:grid-cols-2 gap-3">
              {red_flags.map((f, i) => (
                <SignalCard key={i} flag={f} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="fraud">
          {fraud_signals.length === 0 ? (
            <EmptyState message="No fraud/tamper signals detected." />
          ) : (
            <div className="grid sm:grid-cols-2 gap-3">
              {fraud_signals.map((f, i) => (
                <SignalCard key={i} flag={f} />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="duedate">
          <DueDateTab dda={due_date_analysis} />
        </TabsContent>

        <TabsContent value="cashflow">
          <CashflowTab result={result} salary={salary} bounces={bounces} cashflow={cashflow} />
        </TabsContent>

        <TabsContent value="categories">
          <CategoryTable
            rows={Object.entries(result.category_summary).map(([category, b]) => ({ category, ...b }))}
          />
        </TabsContent>

        <TabsContent value="transactions">
          <TransactionsTable transactions={result.transactions} />
        </TabsContent>
      </Tabs>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-good border border-good/20 bg-good/5 rounded-md p-4">
      <CheckCircle2 className="h-4 w-4 shrink-0" />
      {message}
    </div>
  );
}

function SectionHeading({
  children,
  help,
  icon: Icon,
}: {
  children: string;
  help?: string;
  icon?: ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex items-center gap-2 mb-5">
      {Icon && (
        <span className="grid place-items-center h-7 w-7 rounded-md bg-accent/12 text-accent shrink-0">
          <Icon className="h-3.5 w-3.5" />
        </span>
      )}
      <h2 className="text-[1.0625rem] font-semibold">{children}</h2>
      {help && (
        <Tooltip label={help}>
          <HelpCircle className="h-3.5 w-3.5 text-muted cursor-help" />
        </Tooltip>
      )}
    </div>
  );
}

function OverviewTab({ result }: { result: AnalysisResponse }) {
  const { score, abb, due_date_analysis, red_flags, fraud_signals } = result;
  const fd = score.foir_dscr;

  return (
    <div className="space-y-6">
      <Panel>
        <SectionHeading icon={TrendingUp} help="Policy-default weights, not a fitted model - every component is shown below.">
          Cash-flow score
        </SectionHeading>
        <div className="flex flex-wrap items-start gap-x-12 gap-y-5 mb-4">
          <Metric label="Composite score" value={`${Math.round(score.score)} / 1000`} accent hero />
          <div className="hidden sm:block w-px self-stretch bg-border" aria-hidden />
          <StatRow>
            <Metric
              label="FOIR"
              value={fd.foir != null ? `${fd.foir.toFixed(0)}%` : "NA"}
              sub={fd.foir_band ?? undefined}
              help="Fixed Obligations to Income Ratio: EMI and rent as a share of estimated monthly income. Lower is safer; above 50% is typically outside standard lending caps."
            />
            <Metric
              label="DSCR"
              value={fd.dscr != null ? fd.dscr.toFixed(2) : "NA"}
              sub={fd.dscr_band ?? undefined}
              help="Debt Service Coverage Ratio: income left after expenses, divided by EMI obligations. Above 1.25 means comfortable repayment headroom."
            />
            <Metric
              label="Volatility"
              value={score.volatility.toFixed(2)}
              sub="0 = stable, 1 = volatile"
              help="How much month-to-month income varies, derived from the coefficient of variation in monthly credits. Lower means more predictable income."
            />
          </StatRow>
        </div>
        <Disclosure summary="Score components & FOIR/DSCR detail">
          <div className="pt-4 border-t border-border">
            <StatRow>
              {Object.entries(score.components).map(([k, v]) => (
                <Metric key={k} label={titleCase(k)} value={v.toFixed(0)} sub={`weight ${score.weights[k]}`} small />
              ))}
            </StatRow>
          </div>
          <p className="text-xs text-muted mt-3">
            Estimated monthly income: {fmtInr(fd.monthly_income)} ({fd.income_source ?? "NA"}) · fixed obligations:{" "}
            {fmtInr(fd.monthly_fixed_obligations)} · {fd.months_used} month(s) used · red-flag penalty: -
            {score.red_flag_penalty}
          </p>
        </Disclosure>
      </Panel>

      <Panel>
        <SectionHeading
          icon={Wallet}
          help="Average of the account's daily closing balance over each trailing window, forward-filled on days with no transaction. A window shows NA rather than a partial average when the statement doesn't cover enough of it."
        >
          Average bank balance
        </SectionHeading>
        <StatRow>
          {(["1", "3", "6", "12"] as const).map((w) => {
            const win = abb.windows[w];
            return (
              <Metric
                key={w}
                label={`ABB${w}`}
                value={win?.average != null ? fmtInr(win.average) : "NA"}
                sub={win?.average == null ? `${win?.covered_days ?? 0}/${win?.total_days ?? 0} days covered` : undefined}
                help={`Average daily closing balance over the trailing ${w} month${w === "1" ? "" : "s"} of this statement.`}
              />
            );
          })}
        </StatRow>
      </Panel>

      <div className="grid sm:grid-cols-2 gap-6">
        <Panel>
          <SectionHeading icon={ShieldAlert}>Red flags &amp; fraud signals</SectionHeading>
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {red_flags.length + fraud_signals.length === 0 ? (
              <SeverityBadge severity="GOOD" />
            ) : (
              (["HIGH", "MEDIUM", "LOW"] as const).map((sev) => {
                const n = [...red_flags, ...fraud_signals].filter((f) => f.severity === sev).length;
                return n > 0 ? <SeverityBadge key={sev} severity={sev} label={`${titleCase(sev)}: ${n}`} /> : null;
              })
            )}
          </div>
          <p className="text-xs text-muted">
            {red_flags.length} red flag(s), {fraud_signals.length} fraud signal(s). See their tabs for details.
          </p>
        </Panel>
        <Panel>
          <SectionHeading icon={CalendarClock}>Recommended EMI due date</SectionHeading>
          {due_date_analysis.recommendations.length > 0 ? (
            <>
              <Metric
                label={`Priority 1 · ${due_date_analysis.recommendations[0].due_date} of the month`}
                value={fmtInr(due_date_analysis.recommendations[0].avg_balance)}
                accent
              />
              <p className="text-xs text-muted mt-2">
                Based on the last {due_date_analysis.months_used} month(s). See the Due date tab for all priorities.
              </p>
            </>
          ) : (
            <p className="text-sm text-muted">Not enough reconciled data to recommend a due date.</p>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  sub,
  small,
  hero,
  accent,
  help,
}: {
  label: string;
  value: string;
  sub?: string;
  small?: boolean;
  hero?: boolean;
  accent?: boolean;
  help?: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-1 text-xs text-muted mb-0.5">
        <span>{label}</span>
        {help && (
          <Tooltip label={help}>
            <HelpCircle className="h-3 w-3 cursor-help shrink-0" />
          </Tooltip>
        )}
      </div>
      <div
        className={`font-mono font-semibold tabular-nums ${small ? "text-base" : hero ? "text-[2.25rem] leading-none" : "text-xl"} ${accent ? "text-accent" : ""}`}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );
}

/**
 * A left-clustered row of stats, each in its own light card - gives every
 * number room to breathe (a bare divider-separated row read as too tight
 * once the panel-wide grid was fixed) while still clustering together
 * instead of stretching edge-to-edge across a wide panel.
 */
function StatRow({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-3">
      {Children.map(children, (child) =>
        child ? (
          <div className="rounded-lg border border-border/60 bg-paper px-4 py-3 min-w-[128px]">{child}</div>
        ) : null
      )}
    </div>
  );
}

/**
 * A smoothly animated expand/collapse, replacing a plain <details> - the
 * native element's show/hide is instant with no way to animate height,
 * which read as an abrupt jump next to everything else's motion.
 */
function Disclosure({ summary, children }: { summary: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="text-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-muted hover:text-ink transition-colors"
      >
        <motion.span animate={{ rotate: open ? 90 : 0 }} transition={{ duration: 0.2 }} className="inline-flex">
          <ChevronRight className="h-3.5 w-3.5" />
        </motion.span>
        {summary}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function DueDateTab({ dda }: { dda: AnalysisResponse["due_date_analysis"] }) {
  if (dda.recommendations.length === 0) {
    return <EmptyState message="Not enough reconciled data to recommend a due date." />;
  }

  const anchors = [4, 9, 14, 19] as const;
  const anchorLabel: Record<number, string> = { 4: "4th (→ 5th due)", 9: "9th (→ 10th due)", 14: "14th (→ 15th due)", 19: "19th (→ 20th due)" };
  const dayKey: Record<number, "day_4" | "day_9" | "day_14" | "day_19"> = {
    4: "day_4",
    9: "day_9",
    14: "day_14",
    19: "day_19",
  };

  return (
    <div>
      <p className="text-sm text-muted mb-5">
        Closing balance on the 4th/9th/14th/19th of each month (the day before the 5th/10th/15th/20th due dates),
        averaged over the last {dda.months_used} month(s) of this statement.
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        {dda.recommendations.map((rec) => (
          <DueDateCard key={rec.priority} rec={rec} />
        ))}
      </div>

      <h3 className="text-sm font-semibold mb-1">Month-by-month closing balance on each anchor day</h3>
      <p className="text-xs text-muted mb-3">
        Average row reflects the last {dda.months_used} month(s), same window as the recommendation above.
      </p>
      <div className="overflow-x-auto rounded-lg border border-border shadow-[0_1px_3px_rgb(var(--ink)/0.05)]">
        <table className="w-full text-sm">
          <thead className="bg-surface">
            <tr>
              <th className="text-left font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Month</th>
              {anchors.map((a) => (
                <th key={a} className="text-right font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">
                  {anchorLabel[a]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dda.monthly.map((row) => (
              <tr key={`${row.year}-${row.month}`} className="border-t border-border">
                <td className="px-4 py-2 font-mono tabular-nums">
                  {row.year}-{String(row.month).padStart(2, "0")}
                </td>
                {anchors.map((a) => (
                  <td key={a} className="px-4 py-2 text-right font-mono tabular-nums">
                    {fmtInr(row[dayKey[a]] ?? null)}
                  </td>
                ))}
              </tr>
            ))}
            <tr className="border-t border-border bg-surface font-semibold">
              <td className="px-4 py-2 font-mono">Average</td>
              {anchors.map((a) => (
                <td key={a} className="px-4 py-2 text-right font-mono tabular-nums">
                  {fmtInr(dda.averages[String(a)] ?? null)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CashflowTab({
  result,
  salary,
  bounces,
  cashflow,
}: {
  result: AnalysisResponse;
  salary: AnalysisResponse["salary"];
  bounces: AnalysisResponse["bounces"];
  cashflow: AnalysisResponse["cashflow"];
}) {
  if (result.monthly.length === 0) {
    return <EmptyState message="No dated transactions to summarize." />;
  }

  return (
    <div className="space-y-6">
      <Panel>
        <SectionHeading icon={TrendingUp}>Monthly net cash flow</SectionHeading>
        <CashflowChart data={result.monthly} />
      </Panel>

      <div className="grid sm:grid-cols-2 gap-6">
        <Panel>
          <SectionHeading icon={Banknote}>Salary &amp; bounces</SectionHeading>
          <p className="text-sm mb-1">
            {salary.detected ? (
              <>
                Salary detected: {salary.months_with_salary}/{salary.months_covered} month(s) (
                {fmtPercent(salary.recurrence_rate)} recurrence){salary.irregular ? ", irregular" : ", regular"}
              </>
            ) : (
              "No salary-pattern credit detected."
            )}
          </p>
          <p className="text-sm text-muted">
            Bounces/returns: <span className="font-medium text-ink">{bounces.count}</span>
            {bounces.rate_per_month ? ` (${bounces.rate_per_month.toFixed(1)}/month)` : ""}
          </p>
        </Panel>
        <Panel>
          <SectionHeading icon={Landmark}>Cash-flow ratios</SectionHeading>
          <p className="text-sm mb-1">Cash dependency: {fmtPercent(cashflow.cash_dependency_ratio)}</p>
          <p className="text-sm text-muted">
            Expense concentration:{" "}
            {cashflow.expense_concentration
              ? `${fmtPercent(cashflow.expense_concentration.ratio)} in "${titleCase(cashflow.expense_concentration.category)}"`
              : "NA"}
          </p>
        </Panel>
      </div>
    </div>
  );
}
