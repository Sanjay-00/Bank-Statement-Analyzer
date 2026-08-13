import { motion } from "framer-motion";
import { fmtInr } from "../lib/format";
import type { z } from "zod";
import type { DueDateRecommendationSchema } from "../lib/schema";

type Recommendation = z.infer<typeof DueDateRecommendationSchema>;

/**
 * A ranked due-date recommendation, not four equal options: priority 1 is
 * visually heavier (larger value, accent-colored), 2-4 recede to muted
 * framing - per frontend.md's "Due-date recommendation" spec.
 */
export function DueDateCard({ rec }: { rec: Recommendation }) {
  const isTop = rec.priority === 1;
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.3, delay: (rec.priority - 1) * 0.06 }}
      className={[
        "rounded-md p-4 flex flex-col gap-1 border shadow-[0_1px_2px_rgb(var(--ink)/0.04)] hover:shadow-[0_6px_18px_rgb(var(--ink)/0.08)] transition-shadow",
        isTop ? "border-accent bg-accent/[0.06]" : "border-border bg-surface",
      ].join(" ")}
    >
      <div className={["text-xs font-medium uppercase tracking-wide", isTop ? "text-accent" : "text-muted"].join(" ")}>
        Priority {rec.priority} · {rec.due_date} of the month
      </div>
      <div
        className={[
          "font-mono font-semibold tabular-nums leading-tight",
          isTop ? "text-[1.75rem] text-ink" : "text-lg text-ink/80",
        ].join(" ")}
      >
        {fmtInr(rec.avg_balance)}
      </div>
      <div className="text-xs text-muted">Avg. closing balance on the {rec.anchor_day}th</div>
    </motion.div>
  );
}
