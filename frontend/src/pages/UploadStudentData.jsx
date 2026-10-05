import React, { useCallback, useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
  ChevronDown,
  ChevronUp,
  Search,
  Check,
  X,
  Clock,
  Eye,
  ArrowRight,
  ShieldAlert,
  SlidersHorizontal,
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
    desc: "Session-only analysis without saving any records to database (0 DB writes).",
    icon: Zap,
    accent: "brand-pink",
  },
  {
    key: "save",
    title: "Save & Analyze Batch",
    desc: "Idempotently persist consolidated students, scores, and Kauvery role matches.",
    icon: BarChart3,
    accent: "brand-maroon",
  },
  {
    key: "update",
    title: "Update Existing Batch",
    desc: "Match by roll number / email / name. Update scores and recalculate placement readiness.",
    icon: CheckCircle2,
    accent: "brand-purple",
  },
];

const EFFORT_LEVELS = [
  { id: "quick", label: "Quick", desc: "Executive KPI overview & top roles" },
  { id: "detailed", label: "Detailed", desc: "Full skill breakdown & gap remediation" },
  { id: "comprehensive", label: "Comprehensive", desc: "Deep narrative & personalized plans" },
];

const CCDP_BATCH_PRESETS = ["CCDP 1", "CCDP 2", "CCDP 3", "CCDP 4", "CCDP 5", "CCDP 6"];

export default function UploadStudentData() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [mode, setMode] = useState("live");
  const [overwrite, setOverwrite] = useState(false);
  const [courseName, setCourseName] = useState("CCDP (Career & Competency Development Program)");
  const [batchName, setBatchName] = useState("CCDP 2");
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);

  // Column classification overrides { columnName: "skill" | "metric" | "compliance" | "excluded" }
  const [columnOverrides, setColumnOverrides] = useState({});
  const [expandedExcluded, setExpandedExcluded] = useState(false);
  const [expandedNotes, setExpandedNotes] = useState(true);
  const [expandedSheets, setExpandedSheets] = useState(false);

  // Search & Filter in Live Preview Table
  const [searchQuery, setSearchQuery] = useState("");
  const [tierFilter, setTierFilter] = useState("all");

  // Instant Report Generator state
  const [reportModel, setReportModel] = useState("gemini-3.6-flash");
  const [reportEffort, setReportEffort] = useState("detailed");
  const [reportStep, setReportStep] = useState(0); // 0: Idle, 1: Analysing, 2: Writing narrative, 3: Rendering, 4: Ready
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState("");
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Fetch active models dynamically from /api/ai/models
  const { data: modelsData } = useQuery({
    queryKey: ["ai-models"],
    queryFn: async () => (await api.get("/api/ai/models")).data,
    staleTime: 60000,
  });

  const availableModels = useMemo(() => {
    if (modelsData?.models && modelsData.models.length > 0) {
      return modelsData.models;
    }
    return [
      { id: "gemini-3.6-flash", label: "Gemini 3.6 Flash (Fast & Capable)" },
      { id: "gemini-3.5-flash", label: "Gemini 3.5 Flash" },
      { id: "gemini-3.5-flash-lite", label: "Gemini 3.5 Flash Lite" },
    ];
  }, [modelsData]);

  useEffect(() => {
    if (availableModels.length > 0 && !reportModel) {
      setReportModel(availableModels[0].id);
    }
  }, [availableModels, reportModel]);

  const handleFile = useCallback(async (f) => {
    if (!f) return;
    setFile(f);
    setPreview(null);
    setPreviewError("");
    setResult(null);
    setColumnOverrides({});
    setReportError("");
    setReportStep(0);

    if (f.size > 25 * 1024 * 1024) {
      setPreviewError("File exceeds the maximum upload limit of 25 MB.");
      return;
    }

    const ext = f.name.toLowerCase();
    if (!ext.endsWith(".xlsx") && !ext.endsWith(".xls") && !ext.endsWith(".csv")) {
      setPreviewError("Please upload an Excel workbook (.xlsx, .xls) or CSV (.csv).");
      return;
    }

    setPreviewLoading(true);
    const formData = new FormData();
    formData.append("file", f);
    formData.append("course_name", courseName);
    formData.append("batch_name", batchName);

    try {
      const res = await api.post("/api/upload/preview", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setPreview(res.data);
      if (res.data.detected_batch) {
        setBatchName(res.data.detected_batch);
      }
    } catch (err) {
      setPreviewError(err.response?.data?.detail || "Failed to parse workbook preview.");
    } finally {
      setPreviewLoading(false);
    }
  }, [batchName, courseName]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) handleFile(droppedFile);
  }, [handleFile]);

  // Group columns taking user overrides into account
  const groupedColumns = useMemo(() => {
    if (!preview) return { skills: [], metrics: [], compliance: [], excluded: [] };

    const baseByClass = preview.columns_by_class || {};
    const skills = new Set(baseByClass.skill || preview.detected_skills || []);
    const metrics = new Set(baseByClass.metric || preview.metric_columns || []);
    const compliance = new Set(baseByClass.compliance || preview.compliance_columns || []);
    const excluded = new Set([
      ...(baseByClass.derived || preview.derived_columns || []),
      ...(baseByClass["administrative/PII"] || preview.excluded_columns || []),
    ]);

    // Apply manual overrides
    Object.entries(columnOverrides).forEach(([col, targetClass]) => {
      skills.delete(col);
      metrics.delete(col);
      compliance.delete(col);
      excluded.delete(col);
      if (targetClass === "skill") skills.add(col);
      else if (targetClass === "metric") metrics.add(col);
      else if (targetClass === "compliance") compliance.add(col);
      else if (targetClass === "excluded") excluded.add(col);
    });

    return {
      skills: Array.from(skills).sort(),
      metrics: Array.from(metrics).sort(),
      compliance: Array.from(compliance).sort(),
      excluded: Array.from(excluded).sort(),
    };
  }, [preview, columnOverrides]);

  const cycleColumnClass = (colName, currentClass) => {
    const cycleMap = {
      skill: "metric",
      metric: "compliance",
      compliance: "excluded",
      excluded: "skill",
    };
    const nextClass = cycleMap[currentClass] || "skill";
    setColumnOverrides((prev) => ({ ...prev, [colName]: nextClass }));
  };

  // Filter students in Live Preview table
  const filteredStudents = useMemo(() => {
    if (!preview?.students) return [];
    return preview.students.filter((s) => {
      const matchesSearch =
        !searchQuery ||
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (s.roll_number && s.roll_number.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (s.best_role && s.best_role.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesTier =
        tierFilter === "all" ||
        s.tier_code === tierFilter ||
        (tierFilter === "ready" && s.placement_ready) ||
        (tierFilter === "placed" && s.is_placed);

      return matchesSearch && matchesTier;
    });
  }, [preview, searchQuery, tierFilter]);

  // Execute Save / Update
  const executeProcess = async () => {
    if (!file) return;
    setProcessing(true);
    setShowConfirmModal(false);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", mode);
    formData.append("course_name", courseName);
    formData.append("batch_name", batchName);
    formData.append("overwrite", String(overwrite));

    try {
      const res = await api.post("/api/upload/process", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(res.data);
      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      queryClient.invalidateQueries({ queryKey: ["students"] });
    } catch (err) {
      setResult({ error: err.response?.data?.detail || "Processing failed." });
    } finally {
      setProcessing(false);
    }
  };

  // Instant Report Generation
  const handleGenerateReport = async (format = "pdf") => {
    if (!preview?.students || preview.students.length === 0) return;
    setGeneratingReport(true);
    setReportError("");
    setReportStep(1); // Analysing

    const stepTimer1 = setTimeout(() => setReportStep(2), 1200); // Writing narrative
    const stepTimer2 = setTimeout(() => setReportStep(3), 3200); // Rendering

    const endpoint = format === "png" ? "/api/reports/live/image" : "/api/reports/live/pdf";

    try {
      const response = await api.post(
        endpoint,
        {
          students: preview.students,
          batch_name: batchName,
          course_name: courseName,
          effort: reportEffort,
          model: reportModel,
        },
        { responseType: "blob", timeout: 90000 }
      );

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setReportStep(4); // Ready

      // Trigger browser download
      const blob = new Blob([response.data], {
        type: format === "png" ? "image/png" : "application/pdf",
      });
      const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      const safeBatch = batchName.replace(/\s+/g, "_").replace(/\//g, "-");
      const filename = `CCDP_Live_Report_${safeBatch}_${dateStr}.${format}`;

      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setReportError("Report generation timed out or failed. Returning local summary.");
      setReportStep(0);
    } finally {
      setGeneratingReport(false);
    }
  };

  return (
    <Layout
      title="Upload CCDP Student Sheet"
      subtitle="Ingest Excel/CSV multi-sheet workbooks for the Career & Competency Development Program."
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Main Upload & Review Column */}
        <div className="lg:col-span-2 space-y-5">
          {/* Dropzone Card */}
          <Card
            className={`p-8 border-dashed flex flex-col items-center justify-center text-center transition-all ${
              dragging ? "border-brand-maroon bg-brand-maroon/5 scale-[1.01]" : ""
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <div className="w-14 h-14 rounded-2xl bg-brand-maroon/10 border border-brand-maroon/20 flex items-center justify-center text-brand-maroon mb-3 shadow-xs">
              <UploadCloud size={30} />
            </div>
            <p className="text-sm text-ink font-semibold">
              Drag & drop CCDP workbook (.xlsx, .xls, or .csv)
            </p>
            <p className="text-xs text-ink-faint mt-1 max-w-md">
              Automatically consolidates multi-sheet files (Profile, Assessment, Skill Matrix, Attendance, Placement, Uniform) into single verified student rows.
            </p>

            <label className="mt-4">
              <span className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold bg-brand-maroon text-white hover:bg-brand-dark cursor-pointer shadow-sm transition-all hover:scale-105">
                Browse Files
              </span>
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0])}
              />
            </label>
          </Card>

          {previewLoading && (
            <Card className="p-6 flex items-center justify-center gap-3 text-sm text-ink-muted">
              <div className="w-5 h-5 border-2 border-brand-maroon border-t-transparent rounded-full animate-spin" />
              <span>Consolidating student roster & classifying columns...</span>
            </Card>
          )}

          {previewError && (
            <Card className="p-4 border-danger/30 bg-danger/5 flex items-start gap-2 text-sm text-danger">
              <AlertTriangle size={16} className="mt-0.5 shrink-0" />
              <span>{previewError}</span>
            </Card>
          )}

          {/* Consolidation Summary & Column Review */}
          {preview && (
            <Card className="p-5 space-y-5">
              {/* Header Info Banner */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-brand-maroon/10 text-brand-maroon">
                    <FileSpreadsheet size={22} />
                  </div>
                  <div>
                    <h3 className="font-display font-bold text-sm text-ink">{preview.filename}</h3>
                    <p className="text-xs text-ink-faint">
                      {preview.file_size_kb} KB · <span className="font-bold text-ink">{preview.student_count} consolidated students</span> identified
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone="success">
                    {preview.student_count} Students Consolidated
                  </Badge>
                  <Badge tone="neutral">
                    {preview.sheets_summary?.length || 1} Sheets
                  </Badge>
                </div>
              </div>

              {/* Consolidation Report Card */}
              <div className="p-4 rounded-xl bg-surface-container border border-surface-border space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-ink flex items-center gap-2">
                    <Layers size={14} className="text-brand-maroon" />
                    Consolidation Architecture Report
                  </span>
                  <button
                    onClick={() => setExpandedSheets((prev) => !prev)}
                    className="text-xs text-brand-maroon hover:underline flex items-center gap-1 font-semibold"
                  >
                    <span>{expandedSheets ? "Hide Sheets" : "View Sheet Breakdown"}</span>
                    {expandedSheets ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                  </button>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
                  <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                    <div className="font-bold text-ink text-base">{preview.student_count}</div>
                    <div className="text-[10px] text-ink-faint">Unique Roster</div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                    <div className="font-bold text-success text-base">
                      {preview.consolidation_report?.ambiguous_matches?.length || 0}
                    </div>
                    <div className="text-[10px] text-ink-faint">Fuzzy Matched</div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                    <div className="font-bold text-brand-maroon text-base">
                      {groupedColumns.skills.length}
                    </div>
                    <div className="text-[10px] text-ink-faint">Scored Skills</div>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface border border-surface-border">
                    <div className="font-bold text-brand-purple text-base">
                      {groupedColumns.compliance.length}
                    </div>
                    <div className="text-[10px] text-ink-faint">Compliance Items</div>
                  </div>
                </div>

                {expandedSheets && preview.sheets_summary && (
                  <div className="overflow-x-auto pt-2 border-t border-surface-border">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-surface-border text-ink-faint font-semibold">
                          <th className="pb-1.5">Sheet Name</th>
                          <th className="pb-1.5">Detected Type</th>
                          <th className="pb-1.5 text-center">Total Rows</th>
                          <th className="pb-1.5 text-center">Matched</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-border">
                        {preview.sheets_summary.map((sh, idx) => (
                          <tr key={idx} className="hover:bg-surface-high/40">
                            <td className="py-1.5 font-medium text-ink">{sh.name}</td>
                            <td className="py-1.5 text-ink-muted capitalize">{sh.category}</td>
                            <td className="py-1.5 text-center tabular-nums text-ink">{sh.total_rows}</td>
                            <td className="py-1.5 text-center tabular-nums text-success font-semibold">
                              {sh.matched_rows}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Data Quality Notes (Collapsible) */}
              {preview.data_quality_notes?.length > 0 && (
                <div className="p-4 rounded-xl bg-brand-yellow/5 border border-brand-yellow/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-ink flex items-center gap-1.5">
                      <ShieldAlert size={14} className="text-brand-yellow" />
                      Data Quality Notes ({preview.data_quality_notes.length})
                    </span>
                    <button
                      onClick={() => setExpandedNotes((prev) => !prev)}
                      className="text-xs text-ink-muted hover:text-ink flex items-center gap-1"
                    >
                      {expandedNotes ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    </button>
                  </div>

                  {expandedNotes && (
                    <div className="space-y-1.5 pt-1">
                      {preview.data_quality_notes.map((n, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs">
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-bold uppercase shrink-0 mt-0.5 ${
                              n.severity === "warning"
                                ? "bg-warning/15 text-warning"
                                : n.severity === "danger"
                                ? "bg-danger/15 text-danger"
                                : "bg-brand/10 text-brand"
                            }`}
                          >
                            {n.severity}
                          </span>
                          <div>
                            <span className="font-semibold text-ink">{n.title}: </span>
                            <span className="text-ink-muted">{n.detail}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Column Classification Review Step */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-ink flex items-center gap-1.5">
                    <SlidersHorizontal size={14} className="text-brand-pink" />
                    Column Classification Review (Click chip to cycle classification)
                  </span>
                  <span className="text-[10px] text-ink-faint">
                    Skill → Metric → Compliance → Excluded
                  </span>
                </div>

                {/* 1. Scored Skills */}
                <div className="p-3 rounded-xl bg-surface-container border border-surface-border space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-semibold text-ink">
                    <span>Scored Skills ({groupedColumns.skills.length})</span>
                    <span className="text-[10px] text-brand-maroon">Normalized 0–100</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {groupedColumns.skills.map((c) => (
                      <button
                        key={c}
                        onClick={() => cycleColumnClass(c, "skill")}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-brand-maroon/10 text-brand-maroon border border-brand-maroon/30 hover:bg-brand-maroon hover:text-white transition-all"
                        title="Click to change classification"
                      >
                        {c} ✕
                      </button>
                    ))}
                    {groupedColumns.skills.length === 0 && (
                      <span className="text-xs text-ink-faint">No skill columns designated.</span>
                    )}
                  </div>
                </div>

                {/* 2. Metric (Typing Speed) & Compliance (Uniform) */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-surface-container border border-surface-border space-y-1.5">
                    <span className="text-xs font-semibold text-ink block">
                      Performance Metrics ({groupedColumns.metrics.length})
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {groupedColumns.metrics.map((c) => (
                        <button
                          key={c}
                          onClick={() => cycleColumnClass(c, "metric")}
                          className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-success/10 text-success border border-success/30 hover:bg-success hover:text-white transition-all"
                        >
                          {c} (WPM)
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-surface-container border border-surface-border space-y-1.5">
                    <span className="text-xs font-semibold text-ink block">
                      Professional Compliance ({groupedColumns.compliance.length})
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {groupedColumns.compliance.map((c) => (
                        <button
                          key={c}
                          onClick={() => cycleColumnClass(c, "compliance")}
                          className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-brand-purple/10 text-brand-purple border border-brand-purple/30 hover:bg-brand-purple hover:text-white transition-all"
                        >
                          {c}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* 3. Collapsed Excluded Columns */}
                <div className="p-3 rounded-xl bg-surface-container/60 border border-surface-border">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-ink-muted font-medium">
                      {groupedColumns.excluded.length} columns excluded from scoring (dates, roll numbers, Total, IDs, PII)
                    </span>
                    <button
                      onClick={() => setExpandedExcluded((prev) => !prev)}
                      className="text-brand-maroon hover:underline font-semibold flex items-center gap-1"
                    >
                      <span>{expandedExcluded ? "Collapse" : "Expand"}</span>
                      {expandedExcluded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    </button>
                  </div>
                  {expandedExcluded && (
                    <div className="flex flex-wrap gap-1 pt-2 border-t border-surface-border/60 mt-2">
                      {groupedColumns.excluded.map((c) => (
                        <span
                          key={c}
                          onClick={() => cycleColumnClass(c, "excluded")}
                          className="px-2 py-0.5 rounded-md text-[10px] bg-surface-high border border-surface-border text-ink-faint hover:text-ink cursor-pointer"
                          title="Click to restore to scoring"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2">
                {mode === "live" ? (
                  <div className="p-3 rounded-xl bg-brand-pink/5 border border-brand-pink/20 text-xs text-brand-pink font-medium flex items-center justify-between">
                    <span>Session-only mode active: Live calculations are ready below without touching the database.</span>
                    <Badge tone="brand">0 DB Writes</Badge>
                  </div>
                ) : (
                  <Button
                    onClick={() => setShowConfirmModal(true)}
                    disabled={processing}
                    className="w-full"
                  >
                    {processing ? "Processing Ingestion..." : `Confirm & ${mode === "save" ? "Save Batch" : "Update Batch"}`}
                  </Button>
                )}
              </div>
            </Card>
          )}

          {/* Results Message after Save / Update */}
          {result && !result.error && (
            <Card className="p-5 border-success/30 bg-success/5 space-y-3">
              <div className="flex items-center gap-2 text-success font-semibold text-sm">
                <CheckCircle2 size={18} />
                <span>CCDP Batch Successfully Ingested</span>
              </div>
              <p className="text-sm text-ink-muted">
                {`Successfully persisted ${result.saved} student records for batch '${result.batch}' (${result.skipped} skipped).`}
              </p>
              <div className="flex gap-2.5 pt-2">
                <Button onClick={() => navigate("/students")}>View Students Directory</Button>
                <Button variant="secondary" onClick={() => navigate("/")}>
                  View Dashboard Analytics
                </Button>
              </div>
            </Card>
          )}

          {/* Live Preview Student Table & Stats */}
          {preview?.students && (
            <Card className="p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
                <div>
                  <h3 className="font-display font-bold text-base text-ink">
                    Live Session Roster — {preview.student_count} Candidates
                  </h3>
                  <p className="text-xs text-ink-faint">
                    Verified single source of truth analytics matching dashboard rules
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search size={14} className="absolute left-2.5 top-2.5 text-ink-faint" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search candidate or role..."
                      className="bg-surface-container border border-surface-border rounded-xl pl-8 pr-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand-maroon/30"
                    />
                  </div>

                  <select
                    value={tierFilter}
                    onChange={(e) => setTierFilter(e.target.value)}
                    className="bg-surface-container border border-surface-border rounded-xl px-2.5 py-1.5 text-xs text-ink font-medium focus:outline-none"
                  >
                    <option value="all">All Candidates</option>
                    <option value="ready">Placement Ready Only</option>
                    <option value="placed">Placed Only</option>
                    <option value="tier_1">Tier 1 Only</option>
                    <option value="tier_4">Critical Remediation</option>
                  </select>
                </div>
              </div>

              {/* Exact Matching KPI Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="text-center p-3 rounded-xl bg-surface-container border border-surface-border">
                  <div className="text-2xl font-display font-extrabold text-brand-maroon">
                    {preview.kpis?.average_score ?? 0}%
                  </div>
                  <div className="text-[11px] text-ink-faint mt-0.5">Class Average</div>
                </div>

                <div className="text-center p-3 rounded-xl bg-surface-container border border-surface-border">
                  <div className="text-2xl font-display font-extrabold text-success">
                    {preview.kpis?.placement_ready_count ?? 0}
                  </div>
                  <div className="text-[11px] text-ink-faint mt-0.5">
                    Ready ({preview.kpis?.placement_ready_pct ?? 0}%)
                  </div>
                </div>

                <div className="text-center p-3 rounded-xl bg-surface-container border border-surface-border">
                  <div className="text-2xl font-display font-extrabold text-brand-purple">
                    {preview.kpis?.placed_count ?? 0}
                  </div>
                  <div className="text-[11px] text-ink-faint mt-0.5">
                    Placed ({preview.kpis?.placed_pct ?? 0}%)
                  </div>
                </div>

                <div className="text-center p-3 rounded-xl bg-surface-container border border-surface-border">
                  <div className="text-2xl font-display font-extrabold text-brand-yellow">
                    {preview.kpis?.average_attendance !== null ? `${preview.kpis.average_attendance}%` : "N/A"}
                  </div>
                  <div className="text-[11px] text-ink-faint mt-0.5">Avg Attendance</div>
                </div>
              </div>

              {/* Virtualized/Scrollable Student Table */}
              <div className="overflow-x-auto max-h-80 overflow-y-auto divide-y divide-surface-border">
                <table className="w-full text-left text-xs">
                  <thead className="bg-surface-container sticky top-0 z-10">
                    <tr className="border-b border-surface-border text-ink-faint font-semibold uppercase tracking-wider">
                      <th className="py-2 px-3 text-center">Rank</th>
                      <th className="py-2 px-3">Student Name</th>
                      <th className="py-2 px-3 text-center">Overall</th>
                      <th className="py-2 px-3 text-center">Attendance</th>
                      <th className="py-2 px-3 text-center">Readiness</th>
                      <th className="py-2 px-3">Top Role Match</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {filteredStudents.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-6 text-center text-ink-faint">
                          No candidates found matching the search.
                        </td>
                      </tr>
                    ) : (
                      filteredStudents.map((s, idx) => (
                        <tr key={s.id || idx} className="hover:bg-surface-high/50 transition-colors">
                          <td className="py-2.5 px-3 text-center font-bold tabular-nums text-ink">
                            #{s.rank || idx + 1}
                          </td>
                          <td className="py-2.5 px-3 font-semibold text-ink">
                            <div>{s.name}</div>
                            {s.roll_number && (
                              <div className="text-[10px] text-ink-faint font-normal">
                                {s.roll_number}
                              </div>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-center font-bold tabular-nums text-ink">
                            {s.overall_score}%
                          </td>
                          <td className="py-2.5 px-3 text-center text-ink-muted">
                            {s.attendance_pct !== null ? `${s.attendance_pct}%` : "N/A"}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <Badge tone={s.placement_ready ? "success" : "warning"}>
                              {s.placement_ready ? "Ready" : "Needs Prep"}
                            </Badge>
                          </td>
                          <td className="py-2.5 px-3">
                            <div className="font-medium text-ink truncate max-w-[180px]">
                              {s.best_role || "Healthcare Operations"}
                            </div>
                            <span className="text-[10px] text-brand-maroon font-semibold">
                              {s.fit_tier || "Fit"}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Instant Report Generator Card */}
          {preview?.students && (
            <Card className="p-5 space-y-4 border-brand-maroon/20 bg-gradient-to-br from-brand-maroon/5 via-surface-container to-brand-purple/5">
              <div className="flex items-center gap-3 pb-3 border-b border-surface-border">
                <div className="p-2.5 rounded-xl bg-brand-maroon text-white shadow-xs">
                  <Sparkles size={18} />
                </div>
                <div>
                  <h3 className="font-display font-bold text-sm text-ink">
                    Instant AI Career & Placement Report Generator
                  </h3>
                  <p className="text-[11px] text-ink-faint">
                    Generate an executive PDF or image audit directly from this session
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* AI Model Selector */}
                <div>
                  <label className="text-xs font-semibold text-ink-muted mb-2 block flex items-center gap-1.5">
                    <Cpu size={13} className="text-brand-maroon" />
                    AI Model (models.list dynamic discovery)
                  </label>
                  <select
                    value={reportModel}
                    onChange={(e) => setReportModel(e.target.value)}
                    className="w-full bg-surface border border-surface-border rounded-xl px-3 py-2 text-xs text-ink font-semibold focus:outline-none focus:ring-2 focus:ring-brand-maroon/30"
                  >
                    {availableModels.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.label || m.id}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Effort Selection */}
                <div>
                  <label className="text-xs font-semibold text-ink-muted mb-2 block flex items-center gap-1.5">
                    <Zap size={13} className="text-brand-pink" />
                    Analysis Effort
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {EFFORT_LEVELS.map((e) => (
                      <button
                        key={e.id}
                        type="button"
                        onClick={() => setReportEffort(e.id)}
                        className={`py-1.5 px-2 rounded-xl text-xs font-semibold border transition-all text-center ${
                          reportEffort === e.id
                            ? "bg-brand-maroon text-white border-brand-maroon shadow-xs"
                            : "bg-surface border-surface-border text-ink hover:bg-surface-high"
                        }`}
                      >
                        {e.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Progress Stepper while generating */}
              {generatingReport && (
                <div className="p-3 rounded-xl bg-surface border border-surface-border space-y-2">
                  <div className="flex items-center justify-between text-xs font-semibold text-ink">
                    <span>Generation Progress</span>
                    <span className="text-brand-maroon font-bold">
                      {reportStep === 1
                        ? "Analysing Cohort..."
                        : reportStep === 2
                        ? "Writing AI Narrative..."
                        : reportStep === 3
                        ? "Rendering Server ReportLab PDF..."
                        : "Ready!"}
                    </span>
                  </div>
                  <div className="w-full h-1.5 rounded-full bg-surface-high overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-brand-maroon to-brand-pink transition-all duration-500 rounded-full"
                      style={{ width: `${reportStep * 25}%` }}
                    />
                  </div>
                </div>
              )}

              {reportError && (
                <div className="p-3 rounded-xl bg-danger/10 text-danger text-xs flex items-center gap-2">
                  <AlertTriangle size={14} className="shrink-0" />
                  <span>{reportError}</span>
                </div>
              )}

              {/* Export Buttons */}
              <div className="flex items-center gap-3 pt-2">
                <Button
                  onClick={() => handleGenerateReport("pdf")}
                  disabled={generatingReport}
                  className="flex-1 flex items-center justify-center gap-2"
                >
                  <FileText size={15} />
                  <span>{generatingReport ? "Rendering..." : "Export Live Report (PDF)"}</span>
                </Button>

                <Button
                  variant="secondary"
                  onClick={() => handleGenerateReport("png")}
                  disabled={generatingReport}
                  className="flex items-center gap-2"
                >
                  <ImageIcon size={15} />
                  <span>Export PNG</span>
                </Button>
              </div>
            </Card>
          )}
        </div>

        {/* Right Configuration & Mode Column */}
        <div className="space-y-5">
          {/* Ingestion Mode Selector Card */}
          <Card className="p-5 space-y-4">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-faint block">
              1. Ingestion Mode
            </span>
            <div className="space-y-2.5">
              {MODES.map((m) => {
                const Icon = m.icon;
                const isSelected = mode === m.key;
                return (
                  <div
                    key={m.key}
                    onClick={() => setMode(m.key)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? "border-brand-maroon bg-brand-maroon/10 shadow-sm"
                        : "border-surface-border bg-surface-container hover:bg-surface-high"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 mb-1">
                      <div
                        className={`p-1.5 rounded-lg ${
                          isSelected ? "bg-brand-maroon text-white" : "bg-surface text-ink-muted"
                        }`}
                      >
                        <Icon size={14} />
                      </div>
                      <span className="font-bold text-xs text-ink">{m.title}</span>
                    </div>
                    <p className="text-[11px] text-ink-faint leading-relaxed">{m.desc}</p>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Batch & Program Metadata Card */}
          <Card className="p-5 space-y-3.5">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-faint block">
              2. Target Programme & Batch
            </span>

            <div>
              <label className="text-[11px] font-semibold text-ink-muted block mb-1">
                Programme Track:
              </label>
              <input
                type="text"
                value={courseName}
                onChange={(e) => setCourseName(e.target.value)}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/30"
              />
            </div>

            <div>
              <label className="text-[11px] font-semibold text-ink-muted block mb-1">
                Batch Name:
              </label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {CCDP_BATCH_PRESETS.map((b) => (
                  <button
                    key={b}
                    type="button"
                    onClick={() => setBatchName(b)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                      batchName === b
                        ? "bg-brand-maroon text-white shadow-xs"
                        : "bg-surface-container border border-surface-border text-ink hover:bg-surface-high"
                    }`}
                  >
                    {b}
                  </button>
                ))}
              </div>
              <input
                type="text"
                value={batchName}
                onChange={(e) => setBatchName(e.target.value)}
                placeholder="Custom batch name..."
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/30"
              />
            </div>

            {mode === "update" && (
              <div className="pt-2 border-t border-surface-border">
                <label className="flex items-center gap-2 text-xs text-ink cursor-pointer">
                  <input
                    type="checkbox"
                    checked={overwrite}
                    onChange={(e) => setOverwrite(e.target.checked)}
                    className="accent-brand-maroon rounded"
                  />
                  <span>Overwrite existing scores and recalculate tiers</span>
                </label>
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Confirmation Modal for Save / Update */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4">
          <Card className="max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-brand-maroon text-white">
                <BarChart3 size={20} />
              </div>
              <div>
                <h3 className="font-display font-bold text-base text-ink">
                  Confirm Batch Ingestion
                </h3>
                <p className="text-xs text-ink-faint">
                  Batch: <span className="font-semibold text-ink">{batchName}</span>
                </p>
              </div>
            </div>

            <p className="text-xs text-ink-muted leading-relaxed">
              You are about to save <strong className="text-ink">{preview?.student_count} consolidated candidates</strong> into the database.
              Scores will be normalized, compliance items recorded, and Kauvery hospital matches recalculated.
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-surface-border">
              <Button variant="secondary" onClick={() => setShowConfirmModal(false)}>
                Cancel
              </Button>
              <Button onClick={executeProcess} disabled={processing}>
                {processing ? "Saving..." : "Confirm & Ingest"}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </Layout>
  );
}
