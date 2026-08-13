/**
 * schema.ts - Zod schemas mirroring backend/schemas.py field-for-field.
 * Validated at the client boundary (see api.ts) so a backend/frontend
 * contract drift shows up immediately as a dev-time error, never a silent
 * runtime crash three components deep.
 */
import { z } from "zod";

export const TransactionSchema = z.object({
  date: z.string().nullable(),
  narration: z.string(),
  chq_ref: z.string().nullable(),
  debit: z.number().nullable(),
  credit: z.number().nullable(),
  balance: z.number().nullable(),
  status: z.string(),
  expected_balance: z.number().nullable().optional(),
  category: z.string().nullable().optional(),
  category_confidence: z.string().nullable().optional(),
});
export type Transaction = z.infer<typeof TransactionSchema>;

export const SummarySchema = z.object({
  counts: z.record(z.string(), z.number()),
  total_debit: z.number(),
  total_credit: z.number(),
  opening_balance: z.number().nullable(),
  closing_balance: z.number().nullable(),
  transaction_count: z.number(),
});

export const DueDateMonthRowSchema = z.object({
  year: z.number(),
  month: z.number(),
  day_4: z.number().nullable().optional(),
  day_9: z.number().nullable().optional(),
  day_14: z.number().nullable().optional(),
  day_19: z.number().nullable().optional(),
});

export const DueDateRecommendationSchema = z.object({
  priority: z.number(),
  anchor_day: z.number(),
  due_date: z.string(),
  avg_balance: z.number(),
});

export const DueDateAnalysisSchema = z.object({
  monthly: z.array(DueDateMonthRowSchema),
  averages: z.record(z.string(), z.number().nullable()),
  recommendations: z.array(DueDateRecommendationSchema),
  months_used: z.number(),
});

export const MonthlyEntrySchema = z.object({
  year: z.number(),
  month: z.number(),
  debit: z.number(),
  credit: z.number(),
  debit_count: z.number(),
  credit_count: z.number(),
  txn_count: z.number(),
  net: z.number(),
});

export const FlagSchema = z.object({
  code: z.string(),
  severity: z.enum(["HIGH", "MEDIUM", "LOW"]),
  detail: z.string(),
  instances: z.array(z.record(z.string(), z.unknown())).nullable().optional(),
});
export type Flag = z.infer<typeof FlagSchema>;

export const CategoryBucketSchema = z.object({
  count: z.number(),
  total_debit: z.number(),
  total_credit: z.number(),
});

export const CashflowSchema = z.object({
  cash_dependency_ratio: z.number().nullable(),
  expense_concentration: z.object({ category: z.string(), ratio: z.number() }).nullable(),
});

export const AbbWindowSchema = z.object({
  average: z.number().nullable(),
  covered_days: z.number(),
  total_days: z.number(),
  window_start: z.string().nullable(),
  window_end: z.string().nullable(),
});

export const AbbSchema = z.object({
  as_of: z.string().nullable(),
  windows: z.record(z.string(), AbbWindowSchema),
});

export const SalaryMonthSchema = z.object({
  year: z.number(),
  month: z.number(),
  amount: z.number(),
  date: z.string(),
});

export const SalarySchema = z.object({
  detected: z.boolean(),
  months_covered: z.number(),
  months_with_salary: z.number(),
  recurrence_rate: z.number(),
  average_amount: z.number().nullable(),
  coefficient_of_variation: z.number().nullable(),
  day_spread: z.number(),
  irregular: z.boolean(),
  monthly: z.array(SalaryMonthSchema),
});

export const BounceInstanceSchema = z.object({
  date: z.string(),
  amount: z.number().nullable(),
  narration: z.string(),
});

export const BouncesSchema = z.object({
  count: z.number(),
  rate_per_month: z.number().nullable(),
  instances: z.array(BounceInstanceSchema),
});

export const FoirDscrSchema = z.object({
  monthly_income: z.number().nullable(),
  income_source: z.string().nullable(),
  monthly_debt_service: z.number(),
  monthly_fixed_obligations: z.number(),
  foir: z.number().nullable(),
  foir_band: z.string().nullable(),
  dscr: z.number().nullable(),
  dscr_band: z.string().nullable(),
  months_used: z.number(),
});

export const ScoreSchema = z.object({
  score: z.number(),
  components: z.record(z.string(), z.number()),
  weights: z.record(z.string(), z.number()),
  red_flag_penalty: z.number(),
  volatility: z.number(),
  foir_dscr: FoirDscrSchema,
});

export const AnalysisResponseSchema = z.object({
  bank_key: z.string().nullable(),
  bank_name: z.string(),
  account_holder: z.string().nullable(),
  page_count: z.number(),
  scanned_pages: z.number(),
  transactions: z.array(TransactionSchema),
  summary: SummarySchema,
  due_date_analysis: DueDateAnalysisSchema,
  monthly: z.array(MonthlyEntrySchema),
  fraud_signals: z.array(FlagSchema),
  category_summary: z.record(z.string(), CategoryBucketSchema),
  cashflow: CashflowSchema,
  abb: AbbSchema,
  salary: SalarySchema,
  bounces: BouncesSchema,
  red_flags: z.array(FlagSchema),
  score: ScoreSchema,
});
export type AnalysisResponse = z.infer<typeof AnalysisResponseSchema>;
