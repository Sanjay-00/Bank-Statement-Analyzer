import { LogoMark } from "./logo-mark";
import { ThemeToggle } from "./theme-toggle";

interface TopNavProps {
  dark: boolean;
  onToggleTheme: () => void;
  /** When set, the logo becomes a clickable "go back to upload" affordance
   * - the standard expectation (click the logo to go home) doubles as the
   * app's only navigation, since there's no router/URL state yet. */
  onLogoClick?: () => void;
}

/** Slim top bar - product name, theme toggle. No marketing nav: this is a
 * working tool, not a marketing site (frontend.md's Layout spec). */
export function TopNav({ dark, onToggleTheme, onLogoClick }: TopNavProps) {
  const brand = (
    <>
      <LogoMark />
      <span className="font-semibold text-[0.95rem]">Bank Statement Analyser</span>
    </>
  );

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-paper/85 backdrop-blur-sm">
      <div className="max-w-[1440px] mx-auto px-6 h-16 flex items-center justify-between">
        {onLogoClick ? (
          <button
            onClick={onLogoClick}
            className="flex items-center gap-2.5 rounded-md -ml-1.5 pl-1.5 pr-2 py-1 hover:bg-surface transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            {brand}
          </button>
        ) : (
          <div className="flex items-center gap-2.5">{brand}</div>
        )}
        <ThemeToggle dark={dark} onToggle={onToggleTheme} />
      </div>
    </header>
  );
}
