import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { QueryClient, QueryClientProvider, useMutation } from "@tanstack/react-query";
import { ApiError, analyzeStatement, downloadExcel, type AnalysisMode } from "./lib/api";
import type { AnalysisResponse, QuickAnalysisResponse } from "./lib/schema";
import { UploadPage } from "./pages/upload";
import { ResultsPage } from "./pages/results";
import { QuickResultsPage } from "./pages/quick-results";
import { TooltipProvider } from "./components/ui/tooltip";

const queryClient = new QueryClient();

function useDarkMode() {
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem("theme");
    if (stored) return stored === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  return { dark, toggle: () => setDark((d) => !d) };
}

function AppShell() {
  const { dark, toggle } = useDarkMode();
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<AnalysisMode>("deep");
  const [result, setResult] = useState<AnalysisResponse | QuickAnalysisResponse | null>(null);

  const analyzeMutation = useMutation({
    mutationFn: ({ file, mode, password }: { file: File; mode: AnalysisMode; password?: string }) =>
      mode === "quick" ? analyzeStatement(file, password, "quick") : analyzeStatement(file, password, "deep"),
    onSuccess: (data, vars) => {
      setResult(data);
      setFile(vars.file);
      setMode(vars.mode);
    },
  });

  const downloadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file to export.");
      return downloadExcel(file, undefined, mode);
    },
  });

  const passwordRequired = analyzeMutation.error instanceof ApiError && analyzeMutation.error.errorCode === "LOCKED_PDF";

  const errorMessage =
    analyzeMutation.error instanceof ApiError
      ? lockedPdfMessage(analyzeMutation.error)
      : analyzeMutation.error instanceof Error
        ? analyzeMutation.error.message
        : null;

  // No separate "loading" page - the upload page shows its own inline
  // progress indicator while the mutation is pending (UploadPage's `loading`
  // prop), so the transition into results is a single swap the moment data
  // arrives instead of upload -> skeleton page -> results.
  const view = result && !analyzeMutation.isPending ? "results" : "upload";

  return (
    <div className="min-h-screen bg-paper text-ink font-sans">
      <AnimatePresence mode="wait">
        {view === "upload" && (
          <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
            <UploadPage
              onAnalyze={(f, mode, password) => analyzeMutation.mutate({ file: f, mode, password })}
              loading={analyzeMutation.isPending}
              error={errorMessage}
              passwordRequired={passwordRequired}
              dark={dark}
              onToggleTheme={toggle}
            />
          </motion.div>
        )}

        {view === "results" && result && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
          >
            {mode === "quick" ? (
              <QuickResultsPage
                result={result as QuickAnalysisResponse}
                onDownload={() => downloadMutation.mutate()}
                downloading={downloadMutation.isPending}
                onReset={() => {
                  setResult(null);
                  setFile(null);
                  analyzeMutation.reset();
                }}
                dark={dark}
                onToggleTheme={toggle}
              />
            ) : (
              <ResultsPage
                result={result as AnalysisResponse}
                onDownload={() => downloadMutation.mutate()}
                downloading={downloadMutation.isPending}
                onReset={() => {
                  setResult(null);
                  setFile(null);
                  analyzeMutation.reset();
                }}
                dark={dark}
                onToggleTheme={toggle}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function lockedPdfMessage(err: ApiError): string {
  if (err.errorCode === "LOCKED_PDF") {
    return "This statement is password-protected. Enter the PDF's password below and try again.";
  }
  return err.message;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <AppShell />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
