import { useMemo, useRef, useState } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from "lucide-react";
import { fmtDate, fmtInr, titleCase } from "../lib/format";
import type { Transaction } from "../lib/schema";

const columnHelper = createColumnHelper<Transaction>();

// Shared between the header row and every body row so columns always line
// up - a real <table> lets the browser's table-layout algorithm and a
// virtualizer's absolutely-positioned rows fight each other (that's what
// produced the overlapping/garbled render); a CSS grid with one explicit
// template string sidesteps that class of bug entirely. This is the
// pattern TanStack Virtual's own table examples use.
const GRID_TEMPLATE = "104px minmax(240px,1fr) 116px 112px 112px 124px 96px";

const columns = [
  columnHelper.accessor("date", {
    header: "Date",
    cell: (info) => <span className="font-mono tabular-nums text-xs">{fmtDate(info.getValue())}</span>,
  }),
  columnHelper.accessor("narration", {
    header: "Narration",
    cell: (info) => (
      <span className="truncate block" title={info.getValue()}>
        {info.getValue()}
      </span>
    ),
  }),
  columnHelper.accessor("category", {
    header: "Category",
    cell: (info) => <span className="text-xs text-muted truncate block">{titleCase(info.getValue() ?? "uncategorized")}</span>,
  }),
  columnHelper.accessor("debit", {
    header: "Debit",
    cell: (info) => (
      <span className="font-mono tabular-nums text-xs block text-right">
        {info.getValue() != null ? fmtInr(info.getValue(), true) : ""}
      </span>
    ),
  }),
  columnHelper.accessor("credit", {
    header: "Credit",
    cell: (info) => (
      <span className="font-mono tabular-nums text-xs block text-right">
        {info.getValue() != null ? fmtInr(info.getValue(), true) : ""}
      </span>
    ),
  }),
  columnHelper.accessor("balance", {
    header: "Balance",
    cell: (info) => (
      <span className="font-mono tabular-nums text-xs block text-right font-medium">{fmtInr(info.getValue(), true)}</span>
    ),
  }),
  columnHelper.accessor("status", {
    header: "Status",
    cell: (info) => {
      const v = info.getValue();
      const tone = v === "FAILED" ? "text-critical" : v === "UNVERIFIED" ? "text-warn" : "text-muted";
      return <span className={`text-xs font-medium ${tone}`}>{titleCase(v)}</span>;
    },
  }),
];

const ALIGN_RIGHT = new Set(["debit", "credit", "balance"]);
const ROW_HEIGHT = 40;

export function TransactionsTable({ transactions }: { transactions: Transaction[] }) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [filter, setFilter] = useState("");

  const filtered = useMemo(() => {
    if (!filter.trim()) return transactions;
    const q = filter.toLowerCase();
    return transactions.filter((t) => t.narration.toLowerCase().includes(q));
  }, [transactions, filter]);

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const rows = table.getRowModel().rows;
  const scrollRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
  });

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <div className="relative w-72">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted" />
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter narration..."
            className="w-full pl-8 pr-3 py-1.5 text-sm rounded-md border border-border bg-paper focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          />
        </div>
        <span className="text-xs text-muted">
          {filtered.length.toLocaleString("en-IN")} of {transactions.length.toLocaleString("en-IN")} rows
        </span>
      </div>

      <div
        className="border border-border rounded-lg overflow-hidden shadow-[0_1px_3px_rgb(var(--ink)/0.05)]"
        role="table"
      >
        {/* Header */}
        <div
          role="row"
          className="grid bg-surface border-b border-border"
          style={{ gridTemplateColumns: GRID_TEMPLATE }}
        >
          {table.getFlatHeaders().map((header) => {
            const sorted = header.column.getIsSorted();
            const alignRight = ALIGN_RIGHT.has(header.column.id);
            return (
              <div
                key={header.id}
                role="columnheader"
                onClick={header.column.getToggleSortingHandler()}
                className={[
                  "text-xs font-medium uppercase tracking-wide text-muted px-3 py-2.5 select-none flex items-center gap-1",
                  alignRight ? "justify-end" : "justify-start",
                  header.column.getCanSort() ? "cursor-pointer hover:text-ink" : "",
                ].join(" ")}
              >
                <span className={alignRight ? "order-2" : ""}>
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </span>
                {header.column.getCanSort() &&
                  (sorted === "asc" ? (
                    <ArrowUp className="h-3 w-3" />
                  ) : sorted === "desc" ? (
                    <ArrowDown className="h-3 w-3" />
                  ) : (
                    <ArrowUpDown className="h-3 w-3 opacity-40" />
                  ))}
              </div>
            );
          })}
        </div>

        {/* Virtualized body */}
        <div ref={scrollRef} style={{ height: 560, overflow: "auto" }}>
          <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
            {virtualizer.getVirtualItems().map((vRow) => {
              const row = rows[vRow.index];
              const status = row.original.status;
              return (
                <div
                  key={row.id}
                  role="row"
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: vRow.size,
                    transform: `translateY(${vRow.start}px)`,
                    gridTemplateColumns: GRID_TEMPLATE,
                  }}
                  className={[
                    "grid items-center border-b border-border/70",
                    status === "UNVERIFIED"
                      ? "bg-warn/10"
                      : status === "FAILED"
                        ? "bg-critical/10"
                        : vRow.index % 2
                          ? "bg-surface/40"
                          : "",
                  ].join(" ")}
                >
                  {row.getVisibleCells().map((cell) => (
                    <div key={cell.id} role="cell" className="px-3 overflow-hidden">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
