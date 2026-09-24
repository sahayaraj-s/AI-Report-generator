import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  UploadCloud,
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Sparkles,
  ShieldCheck,
  Hospital,
  Layers,
  FileText,
  Image as ImageIcon,
  Cpu,
  Zap,
  Download,
  BarChart3,
  Trophy,
  User,
} from "lucide-react";
import { Layout } from "../components/Layout";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { api } from "../lib/api";

const MODES = [
  {
    key: "live",
    title: "Live Preview Only",
    desc: "Generate instant suitability report for this session without saving to database.",
    icon: Zap,
    accent: "brand-pink",
  },
  {
    key: "save",
    title: "Save & Analyze Batch",
    desc: "Persist student scores, run AI evaluation, match Kauvery Hospital roles, and save batch history.",
    icon: BarChart3,
    accent: "brand-maroon",
  },
  {
    key: "update",
    title: "Update Existing Batch",
    desc: "Match by roll number / email / name. Update student scores and recalculate placement readiness.",
    icon: CheckCircle2,
    accent: "brand-purple",
  },
];

const AI_MODELS = [
  { id: "gemini-1.5-flash", label: "Flash (Fast)", desc: "Best speed, low latency" },
  { id: "gemini-1.5-pro", label: "Pro (Quality)", desc: "Deeper analysis, richer insights" },
  { id: "gemini-2.0-flash", label: "Flash 2.0 (Latest)", desc: "Newest model, best balance" },
];

const EFFORT_LEVELS = [
  { id: "quick", label: "Quick", desc: "Summary overview only" },
  { id: "detailed", label: "Detailed", desc: "Full skill breakdown & recommendations" },
  { id: "comprehensive", label: "Comprehensive", desc: "Complete report with AI narratives" },
];

const CCDP_BATCH_PRESETS = ["CCDP 1", "CCDP 2", "CCDP 3", "CCDP 4", "CCDP 5", "CCDP 6"];

export default function UploadStudentData() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState(null);
  const [previewError, setPreviewError] = useState("");
  const [mode, setMode] = useState("live");
  const [overwrite, setOverwrite] = useState(false);
  const [courseName, setCourseName] = useState("CCDP (Career & Competency Development Program)");
  const [batchName, setBatchName] = useState("CCDP 1");
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [liveStudents, setLiveStudents] = useState(null);

  // Instant report generator state
  const [reportModel, setReportModel] = useState("gemini-1.5-flash");
  const [reportEffort, setReportEffort] = useState("detailed");
  const [reportFormat, setReportFormat] = useState("pdf");
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState("");

  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const handleFile = useCallback(async (f) => {
    if (!f) return;
    setFile(f);
    setPreview(null);
    setPreviewError("");
    setResult(null);
    setLiveStudents(null);
    setReportError("");

    const form = new FormData();
    form.append("file", f);
    try {
      const res = await api.post("/api/upload/preview", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setPreview(res.data);
      if (res.data.detected_batch) {
        setBatchName(res.data.detected_batch);
      }
      if (res.data.detected_course) {
        setCourseName(res.data.detected_course);
      }
    } catch (err) {
      setPreviewError(err.response?.data?.detail || "Could not read this file.");
    }
  }, []);

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    handleFile(f);
  };

  const runAnalysis = async () => {
    if (!file) return;
    setProcessing(true);
    setResult(null);
    setLiveStudents(null);
    setReportError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("mode", mode);
      form.append("course_name", courseName.trim() || "CCDP (Career & Competency Development Program)");
      form.append("batch_name", batchName.trim() || "CCDP 1");
      form.append("overwrite", overwrite);
      const res = await api.post("/api/upload/process", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
      if (mode === "live") {
        setLiveStudents(res.data.students);
      } else {
        queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
        queryClient.invalidateQueries({ queryKey: ["students"] });
        queryClient.invalidateQueries({ queryKey: ["job-roles"] });
      }
    } catch (err) {
      setResult({ error: err.response?.data?.detail || "Processing failed." });
    } finally {
      setProcessing(false);
    }
  };

  const generateInstantReport = async () => {
    if (!liveStudents || liveStudents.length === 0) return;
    setGeneratingReport(true);
    setReportError("");
    try {
      const endpoint = reportFormat === "pdf" ? "/api/reports/live/pdf" : "/api/reports/live/image";
      const res = await api.post(
        endpoint,
        { students: liveStudents, batch_name: batchName, course_name: courseName, effort: reportEffort, model: reportModel },
        { responseType: "blob" }
      );
      const contentType = reportFormat === "pdf" ? "application/pdf" : "image/png";
      const blob = new Blob([res.data], { type: contentType });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      const ext = reportFormat === "pdf" ? "pdf" : "png";
      link.download = `CCDP_Live_Report_${batchName.replace(/\s+/g, "_")}.${ext}`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      setReportError("Report generation failed. Please try again.");
    } finally {
      setGeneratingReport(false);
    }
  };

  const tierBadge = (s) => {
    if (s.overall_score >= 80) return "success";
    if (s.overall_score >= 60) return "brand";
    if (s.overall_score >= 40) return "warning";
    return "neutral";
  };

  return (
    <Layout
      title="Upload CCDP Student Sheet"
      subtitle="Ingest Excel/CSV scores for the 50-day Career & Competency Development Program."
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-5">
          {/* Dropzone */}
          <Card
            className={`p-10 border-dashed flex flex-col items-center justify-center text-center transition-colors ${
              dragging ? "border-brand-maroon bg-brand-maroon/5" : ""
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <UploadCloud size={36} className="text-brand-pink mb-3" />
            <p className="text-sm text-ink font-semibold">Drag & drop CCDP student score sheet (.xlsx, .xls, or .csv)</p>
            <p className="text-xs text-ink-faint mt-1">
              Supports Communication, MS Office, Soft Skills, Attendance & demographic sheets.
            </p>
            <label className="mt-4">
              <span className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold bg-surface-high border border-surface-border text-ink hover:bg-surface-container cursor-pointer shadow-sm">
                Browse Excel Files
              </span>
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0])}
              />
            </label>
          </Card>

          {previewError && (
            <Card className="p-4 border-danger/30 bg-danger/5 flex items-start gap-2 text-sm text-danger">
              <AlertTriangle size={16} className="mt-0.5 shrink-0" />
              {previewError}
            </Card>
          )}

          {/* Preview Card */}
          {preview && (
            <Card className="p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-surface-border">
                <div className="flex items-center gap-2.5">
                  <FileSpreadsheet size={20} className="text-brand-pink" />
                  <div>
                    <h3 className="font-display font-semibold text-sm text-ink">{preview.filename}</h3>
                    <p className="text-[11px] text-ink-faint">{preview.file_size_kb} KB · {preview.student_count} student rows detected</p>
                  </div>
                </div>
                <Badge tone="brand">CCDP 50-Day Intake</Badge>
              </div>

              {/* Detected Skills vs Cleaned Data */}
              <div>
                <p className="text-xs font-semibold text-ink mb-2 flex items-center gap-1.5">
                  <Sparkles size={13} className="text-brand-maroon" />
                  Detected CCDP Skill Competencies ({preview.detected_skills.length})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {preview.detected_skills.map((s) => (
                    <Badge key={s} tone="brand">
                      {s}
                    </Badge>
                  ))}
                  {preview.detected_skills.length === 0 && (
                    <span className="text-xs text-ink-faint">No skill scores detected in sheet.</span>
                  )}
                </div>
              </div>

              {/* Excluded Non-Skill Data Hygiene Badges */}
              {preview.excluded_columns?.length > 0 && (
                <div className="p-3 rounded-xl bg-surface-container border border-surface-border">
                  <p className="text-xs font-semibold text-ink-muted mb-1.5 flex items-center gap-1.5">
                    <ShieldCheck size={14} className="text-success" />
                    Data Hygiene: Personal & Identifier Columns Excluded ({preview.excluded_columns.length})
                  </p>
                  <p className="text-[11px] text-ink-faint mb-2">
                    These non-skill columns will NOT pollute strengths, weaknesses, or skill radar scores:
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {preview.excluded_columns.map((c) => (
                      <span
                        key={c}
                        className="text-[10px] px-2 py-0.5 rounded-md bg-surface-high border border-surface-border text-ink-muted"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Batch Assignment Selector in Preview — only for save/update modes */}
              {mode !== "live" && (
                <div className="p-4 rounded-xl bg-brand-maroon/5 border border-brand-maroon/20 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-brand-maroon flex items-center gap-1.5">
                      <Calendar size={14} />
                      Assign to CCDP 50-Day Batch
                    </span>
                    {preview.detected_batch && (
                      <Badge tone="success">Detected from Sheet</Badge>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {CCDP_BATCH_PRESETS.map((b) => (
                      <button
                        key={b}
                        type="button"
                        onClick={() => setBatchName(b)}
                        className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                          batchName === b
                            ? "bg-brand-maroon text-white"
                            : "bg-surface-dim border border-surface-border text-ink hover:bg-surface-high"
                        }`}
                      >
                        {b}
                      </button>
                    ))}
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    <span className="text-[11px] text-ink-faint">Or custom batch:</span>
                    <input
                      type="text"
                      value={batchName}
                      onChange={(e) => setBatchName(e.target.value)}
                      placeholder="e.g. CCDP 1"
                      className="flex-1 max-w-[200px] bg-surface-dim border border-surface-border rounded-lg px-2.5 py-1 text-xs text-ink focus:outline-none focus:ring-1 focus:ring-brand-maroon"
                    />
                  </div>
                </div>
              )}

              {/* Warnings */}
              {preview.warnings?.length > 0 && (
                <div className="space-y-1 pt-1">
                  {preview.warnings.map((w, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-brand-yellow">
                      <AlertTriangle size={13} className="mt-0.5 shrink-0" />
                      <span>{w}</span>
                    </div>
                  ))}
                </div>
              )}

              <Button onClick={runAnalysis} disabled={processing} className="w-full">
                {processing
                  ? (mode === "live" ? "Generating Live Preview…" : "Processing CCDP Batch Evaluation…")
                  : (mode === "live" ? "Generate Live Preview Report" : "Process & Evaluate Batch")}
              </Button>
            </Card>
          )}

          {/* Results Card */}
          {result && !result.error && mode !== "live" && (
            <Card className="p-5 border-success/30 bg-success/5 space-y-3">
              <div className="flex items-center gap-2 text-success font-semibold text-sm">
                <CheckCircle2 size={18} />
                <span>CCDP Batch Evaluation Complete</span>
              </div>
              <p className="text-sm text-ink-muted">
                {`Successfully saved ${result.saved} student records for batch '${result.batch}' (${result.skipped} skipped).`}
              </p>
              <div className="flex gap-2.5 pt-2">
                <Button onClick={() => navigate("/students")}>View Students Directory</Button>
                <Button variant="secondary" onClick={() => navigate("/")}>
                  View Dashboard Analytics
                </Button>
              </div>
            </Card>
          )}

          {result?.error && (
            <Card className="p-4 border-danger/30 bg-danger/5 text-sm text-danger">{result.error}</Card>
          )}

          {/* Live Preview Results */}
          {liveStudents && (
            <div className="space-y-4">
              {/* Summary Header */}
              <Card className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="font-display font-semibold text-ink">
                      Live Preview — {liveStudents.length} Candidates Analysed
                    </h3>
                    <p className="text-xs text-ink-faint mt-0.5">Session-only · Not saved to database</p>
                  </div>
                  <Badge tone="brand">Live Session</Badge>
                </div>

                {/* Summary stats */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                  {[
                    {
                      label: "Ready for Placement",
                      value: liveStudents.filter(s => s.placement_ready).length,
                      tone: "text-success",
                    },
                    {
                      label: "Avg. Score",
                      value: `${(liveStudents.reduce((a, s) => a + (s.overall_score || 0), 0) / liveStudents.length).toFixed(1)}/100`,
                      tone: "text-brand-maroon",
                    },
                    {
                      label: "Need Prep",
                      value: liveStudents.filter(s => !s.placement_ready).length,
                      tone: "text-brand-yellow",
                    },
                  ].map(({ label, value, tone }) => (
                    <div key={label} className="text-center p-3 rounded-xl bg-surface-container border border-surface-border">
                      <div className={`text-xl font-bold ${tone}`}>{value}</div>
                      <div className="text-[11px] text-ink-faint mt-0.5">{label}</div>
                    </div>
                  ))}
                </div>

                <div className="divide-y divide-surface-border max-h-64 overflow-y-auto">
                  {liveStudents.map((s, i) => (
                    <div key={i} className="py-2.5 flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2.5">
                        <div className="h-7 w-7 rounded-lg bg-brand-maroon/10 flex items-center justify-center shrink-0">
                          <User size={13} className="text-brand-maroon" />
                        </div>
                        <div>
                          <div className="font-medium text-ink text-xs">{s.name}</div>
                          <div className="text-[11px] text-ink-faint">
                            {s.overall_score}/100 · {s.recommended_roles?.[0]?.role || "—"}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold ${s.overall_score >= 80 ? "text-success" : s.overall_score >= 60 ? "text-brand-maroon" : "text-brand-yellow"}`}>
                          {s.overall_score}%
                        </span>
                        <Badge tone={s.placement_ready ? "success" : "warning"}>
                          {s.placement_ready ? "Ready" : "Needs Prep"}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Instant Report Generator */}
              <Card className="p-5 space-y-4 border-brand-maroon/20 bg-gradient-to-br from-brand-maroon/5 via-surface-dim to-brand-purple/5">
                <div className="flex items-center gap-3 pb-3 border-b border-surface-border">
                  <div className="p-2 rounded-xl bg-brand-maroon/10">
                    <Sparkles size={18} className="text-brand-maroon" />
                  </div>
                  <div>
                    <h3 className="font-display font-semibold text-sm text-ink">Instant Report Generator</h3>
                    <p className="text-[11px] text-ink-faint">Generate a professional placement report from this live analysis</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* AI Model */}
                  <div>
                    <label className="text-xs font-semibold text-ink-muted mb-2 block flex items-center gap-1.5">
                      <Cpu size={12} className="text-brand-maroon" />
                      AI Model
                    </label>
                    <div className="space-y-1.5">
                      {AI_MODELS.map(m => (
                        <label
                          key={m.id}
                          className={`flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer transition-colors ${
                            reportModel === m.id
                              ? "border-brand-maroon bg-brand-maroon/10"
                              : "border-surface-border hover:bg-surface-high"
                          }`}
                        >
                          <input
                            type="radio"
                            name="reportModel"
                            checked={reportModel === m.id}
                            onChange={() => setReportModel(m.id)}
                            className="accent-brand-maroon"
                          />
                          <div>
                            <div className="text-xs font-semibold text-ink">{m.label}</div>
                            <div className="text-[10px] text-ink-faint">{m.desc}</div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Effort + Format */}
                  <div className="space-y-4">
                    <div>
                      <label className="text-xs font-semibold text-ink-muted mb-2 block flex items-center gap-1.5">
                        <Zap size={12} className="text-brand-maroon" />
                        Analysis Effort
                      </label>
                      <div className="space-y-1.5">
                        {EFFORT_LEVELS.map(e => (
                          <label
                            key={e.id}
                            className={`flex items-center gap-2.5 p-2.5 rounded-xl border cursor-pointer transition-colors ${
                              reportEffort === e.id
                                ? "border-brand-maroon bg-brand-maroon/10"
                                : "border-surface-border hover:bg-surface-high"
                            }`}
                          >
                            <input
                              type="radio"
                              name="reportEffort"
                              checked={reportEffort === e.id}
                              onChange={() => setReportEffort(e.id)}
                              className="accent-brand-maroon"
                            />
                            <div>
                              <div className="text-xs font-semibold text-ink">{e.label}</div>
                              <div className="text-[10px] text-ink-faint">{e.desc}</div>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-ink-muted mb-2 block">Export Format</label>
                      <div className="flex gap-2">
                        {[
                          { id: "pdf", label: "PDF", icon: FileText },
                          { id: "image", label: "Image (PNG)", icon: ImageIcon },
                        ].map(({ id, label, icon: Icon }) => (
                          <button
                            key={id}
                            onClick={() => setReportFormat(id)}
                            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl border text-xs font-semibold transition-colors ${
                              reportFormat === id
                                ? "border-brand-maroon bg-brand-maroon text-white"
                                : "border-surface-border text-ink-muted hover:text-ink hover:bg-surface-high"
                            }`}
                          >
                            <Icon size={13} />
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {reportError && (
                  <div className="flex items-center gap-2 text-danger text-xs p-3 rounded-xl bg-danger/10 border border-danger/20">
                    <AlertTriangle size={14} />
                    {reportError}
                  </div>
                )}

                <Button
                  onClick={generateInstantReport}
                  disabled={generatingReport}
                  className="w-full flex items-center justify-center gap-2"
                >
                  {generatingReport ? (
                    <>
                      <Sparkles size={15} className="animate-spin" />
                      Generating Report…
                    </>
                  ) : (
                    <>
                      <Download size={15} />
                      Generate & Download {reportFormat === "pdf" ? "PDF" : "Image"} Report
                    </>
                  )}
                </Button>
              </Card>
            </div>
          )}
        </div>

        {/* Right Sidebar: Settings & Defaults */}
        <div className="space-y-4">
          <Card className="p-5 space-y-3">
            <h3 className="font-display font-semibold text-sm text-ink">Analysis Mode</h3>
            <div className="space-y-2">
              {MODES.map((m) => {
                const Icon = m.icon;
                return (
                  <label
                    key={m.key}
                    className={`block rounded-xl border p-3 cursor-pointer transition-colors ${
                      mode === m.key
                        ? "border-brand-maroon bg-brand-maroon/10"
                        : "border-surface-border hover:bg-surface-high"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="mode"
                        checked={mode === m.key}
                        onChange={() => setMode(m.key)}
                        className="accent-brand-maroon"
                      />
                      <Icon size={14} className={mode === m.key ? "text-brand-maroon" : "text-ink-faint"} />
                      <span className="text-sm font-medium text-ink">{m.title}</span>
                    </div>
                    <p className="text-xs text-ink-faint mt-1 ml-6">{m.desc}</p>
                  </label>
                );
              })}
            </div>

            {mode === "update" && (
              <label className="flex items-center gap-2 text-xs text-ink-muted mt-3">
                <input
                  type="checkbox"
                  checked={overwrite}
                  onChange={(e) => setOverwrite(e.target.checked)}
                  className="accent-brand-maroon"
                />
                Overwrite existing records on match
              </label>
            )}
          </Card>

          {mode === "live" && (
            <Card className="p-4 border-brand-pink/20 bg-brand-pink/5 space-y-2">
              <div className="flex items-center gap-2 text-brand-pink font-semibold text-xs">
                <Zap size={14} />
                Live Preview Mode
              </div>
              <p className="text-[11px] text-ink-muted leading-relaxed">
                Analysis runs in-session only. No data is saved to the database. Use this to quickly preview results and generate instant reports before committing.
              </p>
            </Card>
          )}

          <Card className="p-5 space-y-3">
            <div className="flex items-center gap-2 text-brand-maroon font-semibold text-sm">
              <Hospital size={16} />
              <span>Skill Bay Academy — Kauvery</span>
            </div>
            <p className="text-xs text-ink-muted leading-relaxed">
              Every student evaluated through the 50-day CCDP course is scored across Communication, MS Office & Soft Skills,
              then matched with priority openings across Kauvery Hospital's 12 facilities.
            </p>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
