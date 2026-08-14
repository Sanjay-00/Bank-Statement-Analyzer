import { CalendarClock, ShieldAlert, TrendingUp, Wallet } from "lucide-react";
import { Disclosure } from "../../components/disclosure";
import { Metric, StatRow } from "../../components/metric";
import { Panel } from "../../components/panel";
import { SectionHeading } from "../../components/section-heading";
import { SeverityBadge } from "../../components/severity-badge";
import { fmtInr, titleCase } from "../../lib/format";
import type { AnalysisResponse } from "../../lib/schema";

export function OverviewTab({ result }: { result: AnalysisResponse }) {
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
