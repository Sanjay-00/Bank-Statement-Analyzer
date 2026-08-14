import { motion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * A genuinely elevated section card - bg-surface against the page's bg-paper,
 * a hairline border, and a soft shadow so it reads as raised rather than
 * blending into the page. Used for the "headline number" groupings (score,
 * ABB, monthly totals) - the sections that need to look like the report's
 * actual findings, not just another paragraph. Fades in on mount and lifts
 * slightly on hover, matching the KPI cards' motion idiom.
 */
export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={`bg-surface rounded-xl border border-border/60 p-6 shadow-card hover:shadow-[0_10px_30px_rgb(var(--ink)/0.08)] transition-shadow ${className}`}
    >
      {children}
    </motion.div>
  );
}
