import { motion } from "framer-motion";
import { fmtInr, titleCase } from "../lib/format";

interface CategoryRow {
  category: string;
  count: number;
  total_debit: number;
  total_credit: number;
}

/**
 * A plain labelled table, not an icon-in-a-box card grid - frontend.md is
 * explicit that feature-style content (this, the fraud/red-flag lists)
 * reads calmer as a list at this tool's information density than as cards.
 */
export function CategoryTable({ rows }: { rows: CategoryRow[] }) {
  const sorted = [...rows].sort(
    (a, b) => b.total_debit + b.total_credit - (a.total_debit + a.total_credit)
  );

  return (
    <div className="overflow-x-auto rounded-lg border border-border shadow-[0_1px_3px_rgb(var(--ink)/0.05)]">
      <table className="w-full text-sm">
        <thead className="bg-surface">
          <tr>
            <th className="text-left font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Category</th>
            <th className="text-right font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Txns</th>
            <th className="text-right font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Debit</th>
            <th className="text-right font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Credit</th>
            <th className="text-right font-medium uppercase tracking-wide text-xs text-muted px-4 py-2.5">Net</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => (
            <motion.tr
              key={r.category}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.25, delay: i * 0.03 }}
              className="border-t border-border hover:bg-surface/70 transition-colors"
            >
              <td className="px-4 py-2.5 font-medium">{titleCase(r.category)}</td>
              <td className="px-4 py-2.5 text-right font-mono tabular-nums text-muted">{r.count}</td>
              <td className="px-4 py-2.5 text-right font-mono tabular-nums">{fmtInr(r.total_debit)}</td>
              <td className="px-4 py-2.5 text-right font-mono tabular-nums">{fmtInr(r.total_credit)}</td>
              <td className="px-4 py-2.5 text-right font-mono tabular-nums font-medium">
                {fmtInr(r.total_credit - r.total_debit)}
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
