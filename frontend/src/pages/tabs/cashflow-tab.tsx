import { Banknote, Landmark, TrendingUp } from "lucide-react";
import { CashflowChart } from "../../components/cashflow-chart";
import { EmptyState } from "../../components/empty-state";
import { Panel } from "../../components/panel";
import { SectionHeading } from "../../components/section-heading";
import { fmtPercent, titleCase } from "../../lib/format";
import type { AnalysisResponse } from "../../lib/schema";

export function CashflowTab({
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
