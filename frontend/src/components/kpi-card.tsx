import { motion } from "framer-motion";
import { HelpCircle } from "lucide-react";
import type { ReactNode } from "react";
import { useCountUp } from "../lib/useCountUp";
import { Tooltip } from "./ui/tooltip";

interface KpiCardProps {
  label: string;
  value: ReactNode;
  /** When set, the displayed value counts up from 0 on mount instead of
   * appearing static - `format` turns the animated number back into the
   * display string (e.g. Indian digit grouping, a currency prefix). */
  countFrom?: number;
  format?: (n: number) => string;
  /** Semantic rule color, only when this metric itself is a signal - omit
   * entirely for a healthy/neutral value (frontend.md: "0 -> no rule at all,
   * not a green one - silence is the everything's-fine state"). */
  signal?: "critical" | "warn" | "good";
  help?: string;
}

const SIGNAL_COLOR: Record<NonNullable<KpiCardProps["signal"]>, string> = {
  critical: "rgb(var(--critical))",
  warn: "rgb(var(--warn))",
  good: "rgb(var(--good))",
};

function AnimatedValue({ n, format }: { n: number; format: (n: number) => string }) {
  const animated = useCountUp(n);
  return <>{format(Math.round(animated))}</>;
}

export function KpiCard({ label, value, signal, countFrom, format, help }: KpiCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.3 }}
      className="bg-surface rounded-lg p-4 flex flex-col gap-1 border border-border/60 shadow-card hover:shadow-card-hover transition-shadow"
      style={signal ? { borderLeft: `3px solid ${SIGNAL_COLOR[signal]}` } : undefined}
    >
      <div className="flex items-center gap-1 text-xs font-medium uppercase tracking-wide text-muted">
        <span>{label}</span>
        {help && (
          <Tooltip label={help}>
            <HelpCircle className="h-3 w-3 cursor-help shrink-0 normal-case tracking-normal" />
          </Tooltip>
        )}
      </div>
      <div className="font-mono text-[1.75rem] leading-tight font-semibold tabular-nums">
        {countFrom !== undefined && format ? <AnimatedValue n={countFrom} format={format} /> : value}
      </div>
    </motion.div>
  );
}
