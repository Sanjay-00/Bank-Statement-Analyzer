import { CalendarClock, Layers, ShieldAlert, ShieldX, Table2 } from "lucide-react";
import { CategoryTable } from "../components/category-table";
import { EmptyState } from "../components/empty-state";
import { Panel } from "../components/panel";
import { ResultsHeader } from "../components/results-header";
import { ResultsKpiRow } from "../components/results-kpi-row";
import { SectionHeading } from "../components/section-heading";
import { SignalCard } from "../components/signal-card";
import { TopNav } from "../components/top-nav";
import { TransactionsTable } from "../components/transactions-table";
import { CashflowTab } from "./tabs/cashflow-tab";
import { DueDateTab } from "./tabs/due-date-tab";
import { OverviewTab } from "./tabs/overview-tab";
import type { AnalysisResponse } from "../lib/schema";

interface ResultsPageProps {
  result: AnalysisResponse;
  onDownload: () => void;
  downloading: boolean;
  onReset: () => void;
  dark: boolean;
  onToggleTheme: () => void;
}

/**
 * One continuous scroll, same idiom as quick-results.tsx, instead of a tab
 * shell - every section is a Panel stacked top to bottom, so deep and quick
 * analysis read as the same product at two depths rather than two different
 * UIs. Transactions stays last since it's the heaviest section (virtualized
 * table, thousands of rows) and the least likely thing to be read first.
 */
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
      <div className="max-w-[1100px] mx-auto px-6 py-6">
        <ResultsHeader
          result={result}
          highFraud={highFraud}
          totalSignals={totalSignals}
          onDownload={onDownload}
          downloading={downloading}
          onReset={onReset}
        />

        <div className="h-6" />

        <ResultsKpiRow
          summary={summary}
          verifiedN={verifiedN}
          failedN={failedN}
          unverifiedN={unverifiedN}
          allVerified={allVerified}
        />

        {failedN > 0 && (
          <p className="text-xs text-muted -mt-6 mb-8">
            {failedN} row(s) failed reconciliation - flagged in the Transactions section rather than silently included.
          </p>
        )}

        <div className="space-y-6">
          <OverviewTab result={result} />

          <Panel>
            <SectionHeading icon={ShieldAlert} help="Deterministic checks on the reconciled ledger and the signals it feeds - see each card for the exact rule that triggered it.">
              Red flags ({red_flags.length})
            </SectionHeading>
            {red_flags.length === 0 ? (
              <EmptyState message="No red flags raised." />
            ) : (
              <div className="grid sm:grid-cols-2 gap-3">
                {red_flags.map((f, i) => (
                  <SignalCard key={i} flag={f} />
                ))}
              </div>
            )}
          </Panel>

          <Panel>
            <SectionHeading icon={ShieldX} help="PDF metadata forensics, incremental-save history, font consistency, and content-level checks - deterministic, not an ML verdict.">
              Fraud signals ({fraud_signals.length})
            </SectionHeading>
            {fraud_signals.length === 0 ? (
              <EmptyState message="No fraud/tamper signals detected." />
            ) : (
              <div className="grid sm:grid-cols-2 gap-3">
                {fraud_signals.map((f, i) => (
                  <SignalCard key={i} flag={f} />
                ))}
              </div>
            )}
          </Panel>

          <Panel>
            <SectionHeading icon={CalendarClock}>Due date</SectionHeading>
            <DueDateTab dda={due_date_analysis} />
          </Panel>

          <CashflowTab result={result} salary={salary} bounces={bounces} cashflow={cashflow} />

          <Panel>
            <SectionHeading icon={Layers}>Categories</SectionHeading>
            <CategoryTable
              rows={Object.entries(result.category_summary).map(([category, b]) => ({ category, ...b }))}
            />
          </Panel>

          <Panel>
            <SectionHeading icon={Table2}>Transactions ({summary.transaction_count})</SectionHeading>
            <TransactionsTable transactions={result.transactions} />
          </Panel>
        </div>
      </div>
    </div>
  );
}
