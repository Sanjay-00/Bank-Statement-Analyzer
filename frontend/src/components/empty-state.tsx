import { CheckCircle2 } from "lucide-react";

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-good border border-good/20 bg-good/5 rounded-md p-4">
      <CheckCircle2 className="h-4 w-4 shrink-0" />
      {message}
    </div>
  );
}
