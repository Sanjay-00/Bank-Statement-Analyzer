/**
 * format.ts - INR currency, date, and percentage formatting shared across
 * every component that renders a figure. One place so "Rs. 1,23,456" (Indian
 * digit grouping) is never accidentally reformatted differently in two spots.
 */

const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const inrFormatterPrecise = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function fmtInr(value: number | null | undefined, precise = false): string {
  if (value === null || value === undefined) return "NA";
  return precise ? inrFormatterPrecise.format(value) : inrFormatter.format(value);
}

export function fmtDate(value: string | null | undefined): string {
  if (!value) return "NA";
  const d = new Date(value + "T00:00:00");
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

export function fmtMonth(year: number, month: number): string {
  return new Date(year, month - 1, 1).toLocaleDateString("en-IN", { month: "short", year: "numeric" });
}

export function fmtPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "NA";
  return `${(value * 100).toFixed(digits)}%`;
}

export function titleCase(s: string): string {
  return s
    .replace(/_/g, " ")
    .split(" ")
    .map((w) => (w.length ? w[0].toUpperCase() + w.slice(1).toLowerCase() : w))
    .join(" ");
}
