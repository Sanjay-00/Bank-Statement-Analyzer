import { AlertTriangle, CheckCircle2, Download, Loader2, ScanLine, Upload as UploadIcon } from "lucide-react";
import type { AnalysisResponse } from "../lib/schema";

interface ResultsHeaderProps {
  result: AnalysisResponse;
  highFraud: number;
  totalSignals: number;
  onDownload: () => void;
  downloading: boolean;
  onReset: () => void;
}

export function ResultsHeader({ result, highFraud, totalSignals, onDownload, downloading, onReset }: ResultsHeaderProps) {
  return (
    <>
      <div className="flex items-center justify-between mb-1">
        <div>
          <div className="flex items-baseline gap-2">
            <h1 className="text-xl font-bold">{result.bank_name}</h1>
            {result.bank_key === null && (
              <span className="text-xs text-muted">(bank not recognised)</span>
            )}
          </div>
          {result.account_holder && (
            <p className="text-xs text-muted mt-0.5">Account holder: {result.account_holder}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {highFraud > 0 ? (
            <span className="inline-flex items-center gap-1.5 text-sm text-critical">
              <AlertTriangle className="h-4 w-4" /> {highFraud} high-severity signal(s)
            </span>
          ) : totalSignals > 0 ? (
            <span className="inline-flex items-center gap-1.5 text-sm text-warn">
              <AlertTriangle className="h-4 w-4" /> {totalSignals} signal(s) to review
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-sm text-good">
              <CheckCircle2 className="h-4 w-4" /> No signals
            </span>
          )}
          <div className="h-5 w-px bg-border" />
          <button
            onClick={onReset}
            className="inline-flex items-center gap-2 border border-border rounded-full px-4 py-2 text-sm font-semibold hover:border-ink/30 hover:bg-surface transition-colors"
          >
            <UploadIcon className="h-3.5 w-3.5" />
            New upload
          </button>
          <button
            onClick={onDownload}
            disabled={downloading}
            className="inline-flex items-center gap-2 bg-accent text-ink rounded-full px-4 py-2 text-sm font-bold hover:brightness-95 disabled:opacity-50 transition-[filter] shadow-[0_4px_14px_rgb(var(--accent)/0.3)]"
          >
            {downloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
            {downloading ? "Preparing" : "Download Excel"}
          </button>
        </div>
      </div>

      {result.scanned_pages > 0 && (
        <div className="flex items-center gap-2 text-xs text-info mb-4">
          <ScanLine className="h-3.5 w-3.5" />
          {result.scanned_pages} of {result.page_count} pages look scanned (no digital text layer) and were skipped.
        </div>
      )}
    </>
  );
}
