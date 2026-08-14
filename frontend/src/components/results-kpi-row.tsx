import { KpiCard } from "./kpi-card";
import { fmtInr } from "../lib/format";
import type { AnalysisResponse } from "../lib/schema";

interface ResultsKpiRowProps {
  summary: AnalysisResponse["summary"];
  verifiedN: number;
  failedN: number;
  unverifiedN: number;
  allVerified: boolean;
}

export function ResultsKpiRow({ summary, verifiedN, failedN, unverifiedN, allVerified }: ResultsKpiRowProps) {
  return (
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
  );
}
