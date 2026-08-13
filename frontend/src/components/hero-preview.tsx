import { motion } from "framer-motion";
import { useCountUp } from "../lib/useCountUp";

/**
 * A stylized preview of the actual dashboard - real KPI-tile and severity-
 * badge idioms at reduced scale inside a browser-chrome frame - rather than
 * an abstract illustration. Showing the real product (even a mocked static
 * version of it) reads as a credible SaaS tool; a soft illustrated diagram
 * reads as a hobby project. This was the single biggest gap against the
 * credilens.baseworks.in reference the user pointed at. Bars grow in and
 * the score counts up on mount so the preview feels alive, not a screenshot.
 */
const BARS = [38, 62, 45, 78, 54, 90, 70];

export function HeroPreview() {
  const score = useCountUp(792, 1400);

  return (
    <div className="w-full max-w-md rounded-2xl border border-border bg-paper shadow-[0_20px_60px_-15px_rgb(var(--ink)/0.25)] overflow-hidden">
      {/* window chrome */}
      <div className="flex items-center gap-1.5 px-4 py-3 border-b border-border bg-surface">
        <span className="h-2.5 w-2.5 rounded-full bg-critical/50" />
        <span className="h-2.5 w-2.5 rounded-full bg-warn/50" />
        <span className="h-2.5 w-2.5 rounded-full bg-good/50" />
        <span className="ml-3 text-[11px] text-muted font-mono">statement_analysis.pdf</span>
      </div>

      <div className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[15px] font-semibold leading-tight">HDFC Bank</div>
            <div className="text-xs text-muted">1,495 transactions</div>
          </div>
          <span className="text-[10px] font-semibold bg-good/12 text-good px-2.5 py-1 rounded-full">
            All verified
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-4">
          <MiniKpi label="Score" value={Math.round(score).toString()} accent />
          <MiniKpi label="Failed" value="0" />
          <MiniKpi label="FOIR" value="14%" />
        </div>

        <div className="rounded-lg bg-surface p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-2">Net cash flow</div>
          <div className="flex items-end gap-1.5 h-16">
            {BARS.map((h, i) => (
              <motion.div
                key={i}
                className="flex-1 rounded-sm bg-accent"
                style={{ opacity: 0.35 + (i / BARS.length) * 0.55 }}
                initial={{ height: 0 }}
                animate={{ height: `${h}%` }}
                transition={{ duration: 0.6, delay: 0.15 + i * 0.05, ease: "easeOut" }}
              />
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 mt-4">
          <span className="text-[11px] font-medium bg-critical/10 text-critical px-2 py-1 rounded-full">
            1 high-severity
          </span>
          <span className="text-[11px] font-medium bg-warn/10 text-warn px-2 py-1 rounded-full">3 to review</span>
        </div>
      </div>
    </div>
  );
}

function MiniKpi({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-lg border border-border/60 bg-paper px-2.5 py-2">
      <div className="text-[9px] font-semibold uppercase tracking-wide text-muted">{label}</div>
      <div className={`font-mono text-sm font-bold tabular-nums ${accent ? "text-accent" : ""}`}>{value}</div>
    </div>
  );
}
