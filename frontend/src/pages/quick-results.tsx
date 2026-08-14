import { CalendarClock, Download, Loader2, ScanLine, TrendingUp, Upload as UploadIcon, Wallet } from "lucide-react";
import { CashflowChart } from "../components/cashflow-chart";
import { Metric, StatRow } from "../components/metric";
import { Panel } from "../components/panel";
import { SectionHeading } from "../components/section-heading";
import { TopNav } from "../components/top-nav";
import { DueDateTab } from "./tabs/due-date-tab";
import { fmtInr, fmtMonth } from "../lib/format";
import type { QuickAnalysisResponse } from "../lib/schema";

interface QuickResultsPageProps {
  result: QuickAnalysisResponse;
  onDownload: () => void;
  downloading: boolean;
  onReset: () => void;
  dark: boolean;
  onToggleTheme: () => void;
}

/**
 * Single-tab quick-analysis view - deliberately not the deep-analysis
 * ResultsPage's tab shell, since quick mode's whole point is "the three
 * numbers that matter, on one screen" rather than a dashboard to browse.
 */
export function QuickResultsPage({ result, onDownload, downloading, onReset, dark, onToggleTheme }: QuickResultsPageProps) {
  const { summary, due_date_analysis, abb, monthly } = result;

  return (
    <div>
      <TopNav dark={dark} onToggleTheme={onToggleTheme} onLogoClick={onReset} />
      <div className="max-w-[1100px] mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-1">
          <div>
            <div className="flex items-baseline gap-2">
              <h1 className="text-xl font-bold">{result.bank_name}</h1>
              <span className="text-xs font-semibold uppercase tracking-wide text-accent bg-accent/10 rounded-full px-2 py-0.5">
                Quick analysis
              </span>
            </div>
            {result.account_holder && (
              <p className="text-xs text-muted mt-0.5">Account holder: {result.account_holder}</p>
            )}
          </div>
          <div className="flex items-center gap-3">
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

        <p className="text-xs text-muted mb-6">
          {summary.transaction_count.toLocaleString("en-IN")} transaction(s) reconciled · opening {fmtInr(summary.opening_balance)} ·
          closing {fmtInr(summary.closing_balance)}
        </p>

        <div className="space-y-6">
          <Panel>
            <SectionHeading
              icon={Wallet}
              help="Average of the account's daily closing balance over each trailing window, forward-filled on days with no transaction."
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

          <Panel>
            <SectionHeading icon={CalendarClock}>Recommended EMI due date</SectionHeading>
            <DueDateTab dda={due_date_analysis} />
          </Panel>

          <Panel>
            <SectionHeading icon={TrendingUp}>Monthly credit / debit</SectionHeading>
            {monthly.length === 0 ? (
              <p className="text-sm text-muted">No dated transactions to summarize.</p>
            ) : (
              <>
                <CashflowChart data={monthly} />
                <div className="overflow-x-auto rounded-lg border border-border shadow-card mt-5">
                  <table className="w-full text-sm">
                    <thead className="bg-surface">
                      <tr>
                        <th className="text-left font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Month</th>
                        <th className="text-right font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Debit</th>
                        <th className="text-right font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Credit</th>
                        <th className="text-right font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Net</th>
                      </tr>
                    </thead>
                    <tbody>
                      {monthly.map((m) => (
                        <tr key={`${m.year}-${m.month}`} className="border-t border-border">
                          <td className="px-4 py-2 font-mono tabular-nums">{fmtMonth(m.year, m.month)}</td>
                          <td className="px-4 py-2 text-right font-mono tabular-nums">{fmtInr(m.debit)}</td>
                          <td className="px-4 py-2 text-right font-mono tabular-nums">{fmtInr(m.credit)}</td>
                          <td className={`px-4 py-2 text-right font-mono tabular-nums ${m.net < 0 ? "text-critical" : ""}`}>
                            {fmtInr(m.net)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
