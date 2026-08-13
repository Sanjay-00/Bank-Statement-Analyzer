import { motion } from "framer-motion";
import { titleCase } from "../lib/format";
import type { Flag } from "../lib/schema";
import { SeverityBadge } from "./severity-badge";

const TINT: Record<Flag["severity"], string> = {
  HIGH: "bg-critical/[0.04] border-l-critical",
  MEDIUM: "bg-warn/[0.05] border-l-warn",
  LOW: "bg-info/[0.04] border-l-info",
};

/**
 * One red flag / fraud signal: a left accent rule + subtle tint in the
 * signal's severity color (the same idiom KpiCard uses for a metric that's
 * itself a signal), severity badge + name on one line, the detail sentence
 * below, and - only when the signal carries structured instances
 * (round-tripping pairs, duplicate transactions, bounce dates) - a small
 * inline table. Never a wall of concatenated text; this is the exact bug
 * the Streamlit build fixed, carried into the API contract itself so the
 * frontend never has to re-parse a sentence to render a table.
 */
export function SignalCard({ flag }: { flag: Flag }) {
  const instances = flag.instances ?? [];
  const columns = instances.length > 0 ? Object.keys(instances[0]) : [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.3 }}
      className={`border border-border border-l-[3px] rounded-lg p-4 shadow-[0_1px_3px_rgb(var(--ink)/0.05)] hover:shadow-[0_8px_22px_rgb(var(--ink)/0.08)] transition-shadow ${TINT[flag.severity]}`}
    >
      <div className="flex items-center justify-between gap-3 mb-1.5">
        <span className="font-semibold text-sm">{titleCase(flag.code)}</span>
        <SeverityBadge severity={flag.severity} />
      </div>
      <p className="text-sm text-muted leading-relaxed">{flag.detail}</p>

      {instances.length > 0 && (
        <div className="mt-3 overflow-x-auto rounded border border-border">
          <table className="w-full text-xs">
            <thead className="bg-surface">
              <tr>
                {columns.map((col) => (
                  <th key={col} className="text-left font-medium uppercase tracking-wide text-muted px-3 py-2 whitespace-nowrap">
                    {titleCase(col)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {instances.slice(0, 8).map((inst, i) => (
                <tr key={i} className="border-t border-border">
                  {columns.map((col) => (
                    <td key={col} className="px-3 py-2 font-mono tabular-nums whitespace-nowrap">
                      {String((inst as Record<string, unknown>)[col] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {instances.length > 8 && (
            <div className="px-3 py-1.5 text-xs text-muted bg-surface border-t border-border">
              and {instances.length - 8} more
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
