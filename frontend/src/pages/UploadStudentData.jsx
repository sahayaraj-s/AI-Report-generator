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
} from "lucide-react";
import { Layout } from "../components/Layout";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { api } from "../lib/api";

const MODES = [
  {
    key: "save",
    title: "Save & Analyze Batch",
    desc: "Persist student scores, run AI evaluation, match Kauvery Hospital roles, and save batch history.",
  },
  {
    key: "live",
    title: "Live Preview Only",
    desc: "Generate instant suitability report for this session without saving to database.",
  },
  {
    key: "update",
    title: "Update Existing Batch",
    desc: "Match by roll number / email / name. Update student scores and recalculate placement readiness.",
  },
];

const CCDP_BATCH_PRESETS = ["CCDP 1", "CCDP 2", "CCDP 3", "CCDP 4", "CCDP 5", "CCDP 6"];

export default function UploadStudentData() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState(null);
  const [previewError, setPreviewError] = useState("");
  const [mode, setMode] = useState("save");
  const [overwrite, setOverwrite] = useState(false);
  const [courseName, setCourseName] = useState("CCDP (Career & Competency Development Program)");
  const [batchName, setBatchName] = useState("CCDP 1");
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [liveStudents, setLiveStudents] = useState(null);

  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const handleFile = useCallback(async (f) => {
    if (!f) return;
    setFile(f);
    setPreview(null);
    setPreviewError("");
    setResult(null);
    setLiveStudents(null);

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

              {/* Batch Assignment Selector in Preview */}
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
                {processing ? "Processing CCDP Batch Evaluation…" : "Process & Evaluate Batch"}
              </Button>
            </Card>
          )}

          {/* Results Card */}
          {result && !result.error && (
            <Card className="p-5 border-success/30 bg-success/5 space-y-3">
              <div className="flex items-center gap-2 text-success font-semibold text-sm">
                <CheckCircle2 size={18} />
                <span>CCDP Batch Evaluation Complete</span>
              </div>
              <p className="text-sm text-ink-muted">
                {result.mode === "live"
                  ? `Analyzed ${result.student_count} candidates for this session.`
                  : `Successfully saved ${result.saved} student records for batch '${result.batch}' (${result.skipped} skipped).`}
              </p>
              {result.mode !== "live" && (
                <div className="flex gap-2.5 pt-2">
                  <Button onClick={() => navigate("/students")}>View Students Directory</Button>
                  <Button variant="secondary" onClick={() => navigate("/")}>
                    View Dashboard Analytics
                  </Button>
                </div>
              )}
            </Card>
          )}

          {result?.error && (
            <Card className="p-4 border-danger/30 bg-danger/5 text-sm text-danger">{result.error}</Card>
          )}

          {/* Live Session Results */}
          {liveStudents && (
            <Card className="p-5 space-y-3">
              <h3 className="font-display font-semibold text-sm text-ink">
                Live Evaluated Candidates ({liveStudents.length})
              </h3>
              <div className="divide-y divide-surface-border">
                {liveStudents.map((s, i) => (
                  <div key={i} className="py-2.5 flex items-center justify-between text-sm">
                    <div>
                      <div className="font-medium text-ink">{s.name}</div>
                      <div className="text-xs text-ink-faint">
                        Score: {s.overall_score}/100 · Best Fit: {s.recommended_roles[0]?.role || "—"} ({s.recommended_roles[0]?.kauvery_unit || "Kauvery Hospital"})
                      </div>
                    </div>
                    <Badge tone={s.placement_ready ? "success" : "warning"}>
                      {s.placement_ready ? "Ready" : "Needs Prep"}
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Right Sidebar: Settings & Defaults */}
        <div className="space-y-4">
          <Card className="p-5 space-y-3">
            <h3 className="font-display font-semibold text-sm text-ink">Analysis Mode</h3>
            <div className="space-y-2">
              {MODES.map((m) => (
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
                    <span className="text-sm font-medium text-ink">{m.title}</span>
                  </div>
                  <p className="text-xs text-ink-faint mt-1 ml-6">{m.desc}</p>
                </label>
              ))}
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
