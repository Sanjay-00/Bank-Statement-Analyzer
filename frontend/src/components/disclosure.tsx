import { ChevronRight } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useState, type ReactNode } from "react";

/**
 * A smoothly animated expand/collapse, replacing a plain <details> - the
 * native element's show/hide is instant with no way to animate height,
 * which read as an abrupt jump next to everything else's motion.
 */
export function Disclosure({ summary, children }: { summary: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="text-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-muted hover:text-ink transition-colors"
      >
        <motion.span animate={{ rotate: open ? 90 : 0 }} transition={{ duration: 0.2 }} className="inline-flex">
          <ChevronRight className="h-3.5 w-3.5" />
        </motion.span>
        {summary}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
