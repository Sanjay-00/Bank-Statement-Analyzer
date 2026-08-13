import * as RadixTabs from "@radix-ui/react-tabs";
import { motion } from "framer-motion";
import { createContext, useContext, useState, type ReactNode } from "react";

const ActiveTabContext = createContext<string>("");

/**
 * A single shared underline that slides between tabs (framer-motion's
 * layoutId) instead of each tab growing its own underline in place - the
 * sliding motion is what reads as "designed" (Linear/Vercel-style tabs)
 * rather than a plain state-color-change. Tabs.Root is made controlled
 * internally so TabsTrigger can know which value is active without the
 * caller having to manage state.
 */
export function Tabs({ defaultValue, children }: { defaultValue: string; children: ReactNode }) {
  const [value, setValue] = useState(defaultValue);
  return (
    <RadixTabs.Root value={value} onValueChange={setValue}>
      <ActiveTabContext.Provider value={value}>{children}</ActiveTabContext.Provider>
    </RadixTabs.Root>
  );
}

export function TabsList({ children }: { children: ReactNode }) {
  return (
    <RadixTabs.List className="flex items-center gap-6 border-b border-border overflow-x-auto">
      {children}
    </RadixTabs.List>
  );
}

export function TabsTrigger({ value, children }: { value: string; children: ReactNode }) {
  const active = useContext(ActiveTabContext) === value;
  return (
    <RadixTabs.Trigger
      value={value}
      className={[
        "relative whitespace-nowrap py-3 text-sm font-medium transition-colors",
        "hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 rounded-sm",
        active ? "text-ink" : "text-muted",
      ].join(" ")}
    >
      {children}
      {active && (
        <motion.div
          layoutId="tab-underline"
          className="absolute left-0 right-0 -bottom-px h-0.5 bg-accent rounded-full"
          transition={{ type: "spring", stiffness: 500, damping: 40 }}
        />
      )}
    </RadixTabs.Trigger>
  );
}

export function TabsContent({ value, children }: { value: string; children: ReactNode }) {
  return (
    <RadixTabs.Content value={value} className="pt-6 focus-visible:outline-none" asChild>
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
      >
        {children}
      </motion.div>
    </RadixTabs.Content>
  );
}
