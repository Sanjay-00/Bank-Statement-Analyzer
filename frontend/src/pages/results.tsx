import { CategoryTable } from "../components/category-table";
import { EmptyState } from "../components/empty-state";
import { ResultsHeader } from "../components/results-header";
import { ResultsKpiRow } from "../components/results-kpi-row";
import { SignalCard } from "../components/signal-card";
import { TopNav } from "../components/top-nav";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
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
