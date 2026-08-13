export type Severity = "HIGH" | "MEDIUM" | "LOW" | "GOOD" | "INFO";

const SEVERITY_STYLE: Record<Severity, { color: string; label: string }> = {
  HIGH: { color: "rgb(var(--critical))", label: "High" },
  MEDIUM: { color: "rgb(var(--warn))", label: "Medium" },
  LOW: { color: "rgb(var(--info))", label: "Low" },
  GOOD: { color: "rgb(var(--good))", label: "Clean" },
  INFO: { color: "rgb(var(--info))", label: "Info" },
};

/**
 * Pill shape, semantic color at ~12% opacity background with full-opacity
 * text and a small dot - never a solid Material-style filled badge (see
 * frontend.md's "Severity badge / status chip" spec). Quiet enough to sit in
 * a dense table row without competing with the numbers.
 */
export function SeverityBadge({ severity, label }: { severity: Severity; label?: string }) {
  const { color, label: defaultLabel } = SEVERITY_STYLE[severity];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ backgroundColor: `color-mix(in srgb, ${color} 14%, transparent)`, color }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {label ?? defaultLabel}
    </span>
  );
}
