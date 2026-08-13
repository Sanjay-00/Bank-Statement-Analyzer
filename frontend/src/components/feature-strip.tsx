import { motion } from "framer-motion";
import {
  FileSearch,
  FileSpreadsheet,
  GitCompareArrows,
  LineChart,
  Percent,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";

interface Feature {
  icon: LucideIcon;
  title: string;
  desc: string;
}

const FEATURES: Feature[] = [
  { icon: FileSearch, title: "Rule-based extraction", desc: "No LLM guessing on the default path." },
  { icon: GitCompareArrows, title: "Row-level reconciliation", desc: "Every balance checked against the one before it." },
  { icon: ShieldAlert, title: "Fraud and tamper signals", desc: "Deterministic checks, never a black-box score." },
  { icon: LineChart, title: "Underwriting signals", desc: "ABB, salary consistency, bounces, cash-flow ratios." },
  { icon: Percent, title: "Transparent credit score", desc: "FOIR and DSCR, every weight visible." },
  { icon: FileSpreadsheet, title: "One-click Excel report", desc: "Formatted and ready to file." },
];

/**
 * A proper card grid with icons, replacing an earlier numbered-circle +
 * dashed-connector layout whose line never rendered visibly against the
 * section background. Staggered entrance on scroll into view for a touch of
 * motion without being gratuitous (frontend.md's Motion spec: functional,
 * once, not charming-every-time).
 */
export function FeatureStrip() {
  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {FEATURES.map((f, i) => (
        <motion.div
          key={f.title}
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.4, delay: i * 0.06, ease: "easeOut" }}
          whileHover={{ y: -3 }}
          className="rounded-xl border border-border bg-paper p-5 shadow-[0_1px_3px_rgb(var(--ink)/0.05)] hover:shadow-[0_8px_24px_rgb(var(--ink)/0.08)] hover:border-accent/30 transition-shadow"
        >
          <div className="h-10 w-10 rounded-lg bg-accent/12 text-accent grid place-items-center mb-3.5">
            <f.icon className="h-5 w-5" />
          </div>
          <h3 className="text-sm font-semibold mb-1">{f.title}</h3>
          <p className="text-sm text-muted leading-relaxed">{f.desc}</p>
        </motion.div>
      ))}
    </div>
  );
}
