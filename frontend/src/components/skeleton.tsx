/**
 * Skeleton screens shaped like the real content (skeleton KPI cards, skeleton
 * table rows), not a centered spinner - per frontend.md's Loading state
 * spec: the layout shouldn't jump when data arrives.
 */
function Shimmer({ className = "" }: { className?: string }) {
  return (
    <div
      className={`rounded bg-[length:200%_100%] bg-gradient-to-r from-surface via-border to-surface animate-shimmer ${className}`}
    />
  );
}

export function KpiSkeletonRow() {
  return (
    <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="bg-surface rounded-md p-4 flex flex-col gap-2">
          <Shimmer className="h-3 w-16" />
          <Shimmer className="h-7 w-20" />
        </div>
      ))}
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Shimmer className="h-6 w-48" />
        <Shimmer className="h-6 w-32" />
      </div>
      <KpiSkeletonRow />
      <div className="border-b border-border flex gap-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <Shimmer key={i} className="h-4 w-20 my-3" />
        ))}
      </div>
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Shimmer key={i} className="h-9 w-full" />
        ))}
      </div>
    </div>
  );
}
