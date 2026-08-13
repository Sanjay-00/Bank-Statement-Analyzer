/** Simple geometric mark - a ledger/checkmark motif in the accent color, no
 * stock iconography, matching frontend.md's "simple SVG icons instead of
 * photography or illustration". */
export function LogoMark({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className}>
      <rect x="2" y="2" width="28" height="28" rx="7" className="fill-accent" />
      <path
        d="M9 16.5l4.5 4.5L23 11"
        stroke="white"
        strokeWidth="2.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
