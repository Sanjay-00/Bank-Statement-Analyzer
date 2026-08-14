import { HelpCircle } from "lucide-react";
import type { ComponentType } from "react";
import { Tooltip } from "./ui/tooltip";

export function SectionHeading({
  children,
  help,
  icon: Icon,
}: {
  children: string;
  help?: string;
  icon?: ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex items-center gap-2 mb-5">
      {Icon && (
        <span className="grid place-items-center h-7 w-7 rounded-md bg-accent/12 text-accent shrink-0">
          <Icon className="h-3.5 w-3.5" />
        </span>
      )}
      <h2 className="text-[1.0625rem] font-semibold">{children}</h2>
      {help && (
        <Tooltip label={help}>
          <HelpCircle className="h-3.5 w-3.5 text-muted cursor-help" />
        </Tooltip>
      )}
    </div>
  );
}
