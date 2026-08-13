import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { QueryClient, QueryClientProvider, useMutation } from "@tanstack/react-query";
import { ApiError, analyzeStatement, downloadExcel } from "./lib/api";
import type { AnalysisResponse } from "./lib/schema";
import { UploadPage } from "./pages/upload";
import { ResultsPage } from "./pages/results";
import { DashboardSkeleton } from "./components/skeleton";
import { TooltipProvider } from "./components/ui/tooltip";
import { TopNav } from "./components/top-nav";

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
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  const analyzeMutation = useMutation({
    mutationFn: ({ file, password }: { file: File; password: string }) => analyzeStatement(file, password),
    onSuccess: (data, vars) => {
      setResult(data);
      setFile(vars.file);
    },
  });

  const downloadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file to export.");
      return downloadExcel(file);
    },
  });

  const errorMessage =
    analyzeMutation.error instanceof ApiError
      ? lockedPdfMessage(analyzeMutation.error)
      : analyzeMutation.error instanceof Error
        ? analyzeMutation.error.message
        : null;

  const view = result && !analyzeMutation.isPending ? "results" : analyzeMutation.isPending ? "loading" : "upload";

  return (
    <div className="min-h-screen bg-paper text-ink font-sans">
      <AnimatePresence mode="wait">
        {view === "upload" && (
          <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
            <UploadPage
              onAnalyze={(f, password) => analyzeMutation.mutate({ file: f, password })}
              loading={analyzeMutation.isPending}
              error={errorMessage}
              dark={dark}
              onToggleTheme={toggle}
            />
          </motion.div>
        )}

        {view === "loading" && (
          <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
            <TopNav dark={dark} onToggleTheme={toggle} />
            <div className="max-w-[1440px] mx-auto px-6 py-6">
              <DashboardSkeleton />
            </div>
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
            <ResultsPage
              result={result}
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
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function lockedPdfMessage(err: ApiError): string {
  if (err.errorCode === "LOCKED_PDF") {
    return "This statement is password-protected and the password (if any) didn't unlock it. Enter the PDF's password and try again.";
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
