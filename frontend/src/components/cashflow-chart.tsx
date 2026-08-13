import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtInr, fmtMonth } from "../lib/format";

interface MonthlyPoint {
  year: number;
  month: number;
  debit: number;
  credit: number;
}

/**
 * Monthly debit/credit bars, muted red/green (reduced saturation from the
 * semantic-status colors) so this reads as a trend, not an alarm - per
 * frontend.md's Charts spec. Faint gridlines, no 3D, no gradient fill.
 */
export function CashflowChart({ data }: { data: MonthlyPoint[] }) {
  const points = data.map((d) => ({
    label: fmtMonth(d.year, d.month),
    Debit: Math.round(d.debit),
    Credit: Math.round(d.credit),
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={points} margin={{ top: 8, right: 8, left: 8, bottom: 0 }} barGap={2}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgb(var(--border))" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "rgb(var(--muted))" }}
          axisLine={{ stroke: "rgb(var(--border))" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "rgb(var(--muted))" }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => fmtInr(v)}
          width={80}
        />
        <Tooltip
          formatter={(value) => fmtInr(typeof value === "number" ? value : Number(value), true)}
          contentStyle={{
            background: "rgb(var(--paper))",
            border: "1px solid rgb(var(--border))",
            borderRadius: 6,
            fontSize: 12,
          }}
        />
        <Bar dataKey="Debit" fill="rgb(var(--critical) / 0.55)" radius={[3, 3, 0, 0]} />
        <Bar dataKey="Credit" fill="rgb(var(--good) / 0.55)" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
