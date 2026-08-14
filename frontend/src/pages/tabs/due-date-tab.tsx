import { DueDateCard } from "../../components/due-date-card";
import { EmptyState } from "../../components/empty-state";
import { fmtInr } from "../../lib/format";
import type { AnalysisResponse } from "../../lib/schema";

const ANCHORS = [4, 9, 14, 19] as const;
const ANCHOR_LABEL: Record<number, string> = {
  4: "4th (→ 5th due)",
  9: "9th (→ 10th due)",
  14: "14th (→ 15th due)",
  19: "19th (→ 20th due)",
};
const DAY_KEY: Record<number, "day_4" | "day_9" | "day_14" | "day_19"> = {
  4: "day_4",
  9: "day_9",
  14: "day_14",
  19: "day_19",
};

export function DueDateTab({ dda }: { dda: AnalysisResponse["due_date_analysis"] }) {
  if (dda.recommendations.length === 0) {
    return <EmptyState message="Not enough reconciled data to recommend a due date." />;
  }

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
      <div className="overflow-x-auto rounded-lg border border-border shadow-card">
        <table className="w-full text-sm">
          <thead className="bg-surface">
            <tr>
              <th className="text-left font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Month</th>
              {ANCHORS.map((a) => (
                <th key={a} className="text-right font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">
                  {ANCHOR_LABEL[a]}
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
                {ANCHORS.map((a) => (
                  <td key={a} className="px-4 py-2 text-right font-mono tabular-nums">
                    {fmtInr(row[DAY_KEY[a]] ?? null)}
                  </td>
                ))}
              </tr>
            ))}
            <tr className="border-t border-border bg-surface font-semibold">
              <td className="px-4 py-2 font-mono">Average</td>
              {ANCHORS.map((a) => (
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
