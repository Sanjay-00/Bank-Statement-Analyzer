import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, FileText, Loader2, Lock, Sparkles, UploadCloud, X } from "lucide-react";
import { FeatureStrip } from "../components/feature-strip";
import { HeroPreview } from "../components/hero-preview";
import { TopNav } from "../components/top-nav";
import type { AnalysisMode } from "../lib/api";

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.05 } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

interface UploadPageProps {
  onAnalyze: (file: File, mode: AnalysisMode, password?: string) => void;
  loading: boolean;
  error: string | null;
  /** Set once the backend has told us this specific PDF is locked - the
   * password field only appears at that point, not up front for every
   * upload (most statements aren't password-protected). */
  passwordRequired: boolean;
  dark: boolean;
  onToggleTheme: () => void;
}

const CAPABILITIES = ["Reconciliation", "Fraud detection", "Credit scoring"];

const MODES: { value: AnalysisMode; label: string; description: string }[] = [
  { value: "deep", label: "Deep analysis", description: "Full ledger, fraud signals, red flags & credit score" },
  { value: "quick", label: "Quick analysis", description: "Average balance, best due date & monthly cash flow" },
];

/**
 * Two-column hero: big, confident, bold-weight headline + checklist + the
 * functional dropzone on the left; a stylized preview of the real dashboard
 * (not an illustration) on the right, grounded on a full-bleed dot texture.
 * Rebuilt after user feedback that the softer, illustration-led first pass
 * read as "childish" next to a real reference (credilens.baseworks.in) -
 * the fix was committing fully to one saturated accent instead of diluted
 * tints, much larger/heavier type, and showing the actual product instead
 * of an abstract diagram.
 */
export function UploadPage({ onAnalyze, loading, error, passwordRequired, dark, onToggleTheme }: UploadPageProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [mode, setMode] = useState<AnalysisMode>("deep");
  const [password, setPassword] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback((files: FileList | null) => {
    const f = files?.[0];
    if (f && f.type === "application/pdf") setFile(f);
  }, []);

  useEffect(() => {
    if (passwordRequired) passwordRef.current?.focus();
  }, [passwordRequired]);

  return (
    <div className="min-h-screen bg-paper text-ink">
      <TopNav dark={dark} onToggleTheme={onToggleTheme} />

      <div className="relative overflow-hidden">
        {/* Full-bleed dot texture behind the hero, contained to this
            section - one deliberate zone of texture, not noise everywhere. */}
        <div
          className="absolute inset-0 -z-10 opacity-[0.4]"
          aria-hidden
          style={{
            backgroundImage: "radial-gradient(rgb(var(--muted) / 0.35) 1px, transparent 1px)",
            backgroundSize: "22px 22px",
            maskImage: "radial-gradient(ellipse 80% 60% at 50% 30%, black 40%, transparent 90%)",
            WebkitMaskImage: "radial-gradient(ellipse 80% 60% at 50% 30%, black 40%, transparent 90%)",
          }}
        />
        <motion.div
          className="absolute -top-24 right-[-6%] h-[520px] w-[520px] rounded-full bg-accent/[0.10] blur-3xl -z-10"
          aria-hidden
          animate={{ scale: [1, 1.08, 1], x: [0, -18, 0], y: [0, 14, 0] }}
          transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
        />

        <motion.div
          variants={stagger}
          initial="hidden"
          animate="show"
          className="max-w-[1440px] mx-auto px-8 grid lg:grid-cols-2 gap-16 items-center pt-10 pb-28"
        >
          {/* Left: headline + checklist + functional dropzone */}
          <div>
            <motion.span
              variants={fadeUp}
              className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-ink bg-paper border border-border rounded-full px-3.5 py-1.5 mb-6 shadow-sm"
            >
              <Sparkles className="h-3.5 w-3.5 text-accent" />
              Rule-based · Explainable · No black box
            </motion.span>

            <motion.h1
              variants={fadeUp}
              className="text-[2.75rem] sm:text-[3.4rem] font-extrabold leading-[1.05] tracking-tight mb-5"
            >
              Bank statements,
              <br />
              <span className="relative inline-block">
                <span className="relative z-10">reconciled.</span>
                <span className="absolute left-0 right-0 bottom-1 h-4 bg-accent/30 -z-0" aria-hidden />
              </span>
            </motion.h1>

            <motion.p variants={fadeUp} className="text-muted text-lg leading-relaxed mb-7 max-w-md">
              Upload a statement PDF and get every transaction extracted, reconciled, and scored.
              Every number is checked against the one before it, and every signal traces back to
              the row that triggered it.
            </motion.p>

            <motion.ul variants={fadeUp} className="flex flex-wrap gap-x-6 gap-y-2 mb-8">
              {CAPABILITIES.map((c) => (
                <li key={c} className="flex items-center gap-2 text-sm font-medium">
                  <CheckCircle2 className="h-4 w-4 text-accent shrink-0" />
                  {c}
                </li>
              ))}
            </motion.ul>

            <motion.div
              variants={fadeUp}
              onDragOver={(e) => {
                e.preventDefault();
                if (!loading) setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                if (!loading) handleFiles(e.dataTransfer.files);
              }}
              onClick={() => !loading && inputRef.current?.click()}
              className={[
                "rounded-xl border-2 border-dashed p-8 flex flex-col items-center gap-3 transition-colors bg-paper",
                loading ? "cursor-not-allowed opacity-60" : "cursor-pointer",
                dragging ? "border-accent bg-accent/5" : "border-border hover:border-accent/50",
              ].join(" ")}
            >
              <input
                ref={inputRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                disabled={loading}
                onChange={(e) => handleFiles(e.target.files)}
              />
              {file ? (
                <div className="flex items-center gap-3 w-full">
                  <FileText className="h-8 w-8 text-accent shrink-0" />
                  <div className="min-w-0">
                    <div className="font-medium truncate">{file.name}</div>
                    <div className="text-xs text-muted">{(file.size / 1024).toFixed(1)} KB</div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                    disabled={loading}
                    className="ml-auto p-1.5 rounded-md hover:bg-surface text-muted disabled:opacity-40 disabled:cursor-not-allowed"
                    aria-label="Remove file"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <>
                  <UploadCloud className="h-7 w-7 text-muted" />
                  <div className="text-sm">
                    <span className="text-accent font-semibold">Click to upload</span>{" "}
                    <span className="text-muted">or drag and drop a PDF</span>
                  </div>
                </>
              )}
            </motion.div>

            <motion.div variants={fadeUp} className="mt-6">
              <div className="text-xs font-semibold uppercase tracking-wide text-muted mb-2">Analysis type</div>
              <div role="radiogroup" aria-label="Analysis type" className="inline-flex rounded-full border border-border bg-paper p-1 gap-1">
                {MODES.map((m) => (
                  <button
                    key={m.value}
                    type="button"
                    role="radio"
                    aria-checked={mode === m.value}
                    title={m.description}
                    disabled={loading}
                    onClick={() => setMode(m.value)}
                    className={[
                      "px-4 py-1.5 rounded-full text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 disabled:cursor-not-allowed",
                      mode === m.value ? "bg-accent text-ink" : "text-muted hover:text-ink",
                    ].join(" ")}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
              <p className="text-xs text-muted mt-2">{MODES.find((m) => m.value === mode)?.description}</p>
            </motion.div>

            {error && (
              <div className="mt-4 border border-critical/30 bg-critical/5 text-critical text-sm rounded-md p-3">
                {error}
              </div>
            )}

            {passwordRequired && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-4">
                <label className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted mb-2">
                  <Lock className="h-3 w-3" />
                  PDF password
                </label>
                <input
                  ref={passwordRef}
                  type="password"
                  placeholder="Enter the PDF's password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && file) onAnalyze(file, mode, password);
                  }}
                  className="w-full px-3 py-2.5 text-sm rounded-md border border-border bg-paper focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                />
              </motion.div>
            )}

            <motion.div variants={fadeUp} className="mt-4">
              <button
                onClick={() => file && onAnalyze(file, mode, password)}
                disabled={!file || loading}
                className="w-full inline-flex items-center justify-center gap-2 bg-accent text-ink font-bold text-sm rounded-full px-7 py-2.5 whitespace-nowrap disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-95 transition-[filter] shadow-[0_4px_14px_rgb(var(--accent)/0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Analyzing
                  </>
                ) : (
                  "Analyze →"
                )}
              </button>

              {loading && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-3">
                  <div className="h-1 rounded-full bg-border overflow-hidden">
                    <motion.div
                      className="h-full w-1/3 rounded-full bg-accent"
                      animate={{ x: ["-100%", "220%"] }}
                      transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
                    />
                  </div>
                  <p className="text-xs text-muted mt-2">
                    Extracting and reconciling {file?.name ?? "the statement"} - large statements can take a few seconds.
                  </p>
                </motion.div>
              )}
            </motion.div>

            <motion.p variants={fadeUp} className="text-xs text-muted mt-6">
              Processed on the server for this request only. Nothing is stored.
            </motion.p>
          </div>

          {/* Right: a stylized preview of the real dashboard - one motion
              element for the staggered entrance, a nested one for the
              continuous idle float (variants and a literal animate target
              can't share one element in framer-motion). */}
          <motion.div variants={fadeUp} className="hidden lg:flex justify-center">
            <motion.div animate={{ y: [0, -10, 0] }} transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}>
              <HeroPreview />
            </motion.div>
          </motion.div>
        </motion.div>
      </div>

      <div className="border-t border-border bg-surface/40">
        <div className="max-w-[1440px] mx-auto px-8 py-16">
          <h2 className="text-lg font-semibold mb-10 text-center">How it works</h2>
          <FeatureStrip />
        </div>
      </div>
    </div>
  );
}
