/**
 * api.ts - typed fetch wrapper around the FastAPI backend, validated at the
 * client boundary with the Zod schema in schema.ts. A backend contract
 * change that doesn't match schema.ts fails loudly here in dev, instead of
 * producing an `undefined` deep inside a component render.
 */
import { AnalysisResponseSchema, QuickAnalysisResponseSchema, type AnalysisResponse, type QuickAnalysisResponse } from "./schema";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type AnalysisMode = "deep" | "quick";

export class ApiError extends Error {
  errorCode: string;
  status: number;

  constructor(status: number, errorCode: string, message: string) {
    super(message);
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function parseErrorDetail(resp: Response): Promise<{ errorCode: string; message: string }> {
  try {
    const body = await resp.json();
    const detail = body?.detail;
    if (detail?.error_code) {
      return { errorCode: detail.error_code, message: detail.message };
    }
    return { errorCode: "UNKNOWN", message: typeof detail === "string" ? detail : resp.statusText };
  } catch {
    return { errorCode: "UNKNOWN", message: resp.statusText };
  }
}

function buildStatementForm(file: File, password?: string, mode: AnalysisMode = "deep"): FormData {
  const form = new FormData();
  form.append("file", file);
  if (password) form.append("password", password);
  form.append("mode", mode);
  return form;
}

/** POSTs the statement file to `path`, throwing ApiError on a non-2xx response. */
async function postStatement(path: string, file: File, password?: string, mode: AnalysisMode = "deep"): Promise<Response> {
  const resp = await fetch(`${API_BASE}${path}`, { method: "POST", body: buildStatementForm(file, password, mode) });
  if (!resp.ok) {
    const { errorCode, message } = await parseErrorDetail(resp);
    throw new ApiError(resp.status, errorCode, message);
  }
  return resp;
}

export async function analyzeStatement(file: File, password: string | undefined, mode: "deep"): Promise<AnalysisResponse>;
export async function analyzeStatement(file: File, password: string | undefined, mode: "quick"): Promise<QuickAnalysisResponse>;
export async function analyzeStatement(
  file: File,
  password: string | undefined,
  mode: AnalysisMode,
): Promise<AnalysisResponse | QuickAnalysisResponse> {
  const resp = await postStatement("/api/analyze", file, password, mode);

  const json = await resp.json();
  const schema = mode === "quick" ? QuickAnalysisResponseSchema : AnalysisResponseSchema;
  const parsed = schema.safeParse(json);
  if (!parsed.success) {
    // eslint-disable-next-line no-console
    console.error("API response failed schema validation:", parsed.error);
    throw new ApiError(resp.status, "SCHEMA_MISMATCH", "The server response didn't match the expected shape.");
  }
  return parsed.data;
}

export async function downloadExcel(file: File, password: string | undefined, mode: AnalysisMode = "deep"): Promise<void> {
  const resp = await postStatement("/api/analyze/excel", file, password, mode);

  const disposition = resp.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] ?? "statement_analysis.xlsx";

  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
