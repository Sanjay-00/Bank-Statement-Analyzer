import { HelpCircle } from "lucide-react";
import { Children, type ReactNode } from "react";
import { Tooltip } from "./ui/tooltip";

export function Metric({
  label,
  value,
  sub,
  small,
  hero,
  accent,
  help,
}: {
  label: string;
  value: string;
  sub?: string;
  small?: boolean;
  hero?: boolean;
  accent?: boolean;
  help?: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-1 text-xs text-muted mb-0.5">
        <span>{label}</span>
        {help && (
          <Tooltip label={help}>
            <HelpCircle className="h-3 w-3 cursor-help shrink-0" />
          </Tooltip>
        )}
      </div>
      <div
        className={`font-mono font-semibold tabular-nums ${small ? "text-base" : hero ? "text-[2.25rem] leading-none" : "text-xl"} ${accent ? "text-accent" : ""}`}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );
}

/**
 * A left-clustered row of stats, each in its own light card - gives every
 * number room to breathe (a bare divider-separated row read as too tight
 * once the panel-wide grid was fixed) while still clustering together
 * instead of stretching edge-to-edge across a wide panel.
 */
export function StatRow({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-3">
      {Children.map(children, (child) =>
        child ? (
          <div className="rounded-lg border border-border/60 bg-paper px-4 py-3 min-w-[128px]">{child}</div>
        ) : null
      )}
    </div>
  );
}
