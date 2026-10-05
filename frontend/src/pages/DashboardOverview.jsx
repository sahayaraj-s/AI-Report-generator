import React, { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import {
  Users,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Award,
  Building2,
  Sparkles,
  Download,
  RefreshCw,
  Layers,
  BarChart3,
  Table,
  ChevronRight,
  Eye,
  ShieldAlert,
  Hospital,
  Target,
  ArrowUpRight,
  Check,
  X,
  SlidersHorizontal,
  FileSpreadsheet,
  FileText,
  ArrowUpDown,
  Keyboard,
  CalendarCheck,
  Briefcase,
  Shirt,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  Cell,
} from "recharts";
import { Layout } from "../components/Layout";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { PowerBiKpiCard } from "../components/ui/PowerBiKpiCard";
import { PowerBiGauge } from "../components/ui/PowerBiGauge";
import { api } from "../lib/api";
import { useTheme } from "../context/ThemeContext";

const TIER_COLORS = {
  tier_1: "#22C55E",
  tier_2: "#8B1D55",
  tier_3: "#EFBC19",
  tier_4: "#EF4444",
};

const FIT_TONE = {
  "Perfect Match": "success",
  "Medium Fit": "brand",
  "Low Fit": "warning",
  Eligible: "brand",
  "Not Eligible": "neutral",
};

function escapeCsvCell(val) {
  if (val === null || val === undefined) return '""';
  let str = String(val);
  if (/^[=+@\-\t\r]/.test(str)) {
    str = "'" + str;
  }
  return `"${str.replace(/"/g, '""')}"`;
}

function useChartStyles(theme) {
  const isDark = theme === "dark";
  return {
    chartGrid: isDark ? "#34323A" : "#E2E8F0",
    chartText: isDark ? "#A6A1AC" : "#64748B",
    tooltipStyle: {
      backgroundColor: isDark ? "#1E1D22" : "#FFFFFF",
      borderColor: isDark ? "#34323A" : "#E2E8F0",
      borderRadius: "0.75rem",
      color: isDark ? "#EDE9EE" : "#0F172A",
      boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.3)",
      fontSize: "12px",
      padding: "10px 14px",
    },
  };
}

function EmptyState({ text }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Layers className="text-ink-faint mb-2" size={28} />
      <p className="text-xs text-ink-faint">{text}</p>
    </div>
  );
}

export default function DashboardOverview() {
  const { theme } = useTheme();
  const { chartGrid, chartText, tooltipStyle } = useChartStyles(theme);
  const [searchParams, setSearchParams] = useSearchParams();

  // Slicer States synced with URL query params
  const selectedBatch = searchParams.get("batch") || "";
  const selectedCourse = searchParams.get("course") || "";
  const selectedTier = searchParams.get("tier") || "";
  const selectedReadiness = searchParams.get("readiness") || "";
  const selectedPlaced = searchParams.get("placed") || "";
  const minScoreParam = searchParams.get("min_score");
  const maxScoreParam = searchParams.get("max_score");

  const [activeTab, setActiveTab] = useState("overview"); // 'overview' | 'matrix' | 'grid'
  const [gridSearch, setGridSearch] = useState("");
  const [gridSortBy, setGridSortBy] = useState("overall_score");
  const [gridSortDir, setGridSortDir] = useState("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

  const updateFilters = (newParams) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      Object.entries(newParams).forEach(([k, v]) => {
        if (v === "" || v === null || v === undefined) {
          next.delete(k);
        } else {
          next.set(k, String(v));
        }
      });
      return next;
    });
    setCurrentPage(1);
  };

  const resetFilters = () => {
    setSearchParams(new URLSearchParams());
    setGridSearch("");
    setCurrentPage(1);
  };

  // Query Dashboard Data with Slicers
  const { data, isLoading, isRefetching, error, refetch } = useQuery({
    queryKey: [
      "dashboard-stats",
      {
        batch: selectedBatch,
        course: selectedCourse,
        performance_tier: selectedTier,
        readiness: selectedReadiness,
        placed: selectedPlaced,
        min_score: minScoreParam,
        max_score: maxScoreParam,
      },
    ],
    queryFn: async () => {
      const params = {};
      if (selectedBatch) params.batch = selectedBatch;
      if (selectedCourse) params.course = selectedCourse;
      if (selectedTier) params.performance_tier = selectedTier;
      if (selectedReadiness) params.readiness = selectedReadiness;
      if (selectedPlaced) params.placed = selectedPlaced;
      if (minScoreParam) params.min_score = Number(minScoreParam);
      if (maxScoreParam) params.max_score = Number(maxScoreParam);
      return (await api.get("/api/dashboard/stats", { params })).data;
    },
    placeholderData: (prev) => prev,
  });

  const activeFilterCount = [
    selectedBatch,
    selectedCourse,
    selectedTier,
    selectedReadiness,
    selectedPlaced,
    minScoreParam,
  ].filter(Boolean).length;

  const filteredBatchList = useMemo(() => {
    if (!data?.batch_list) return [];
    return data.batch_list.filter((b) => !/^\d{4}$/.test(b.trim()));
  }, [data?.batch_list]);

  // Filtered and sorted leaderboard / grid data
  const gridStudents = useMemo(() => {
    const rawStudents = data?.students || data?.leaderboard || [];
    let list = [...rawStudents];
    if (gridSearch.trim()) {
      const q = gridSearch.toLowerCase();
      list = list.filter(
        (s) =>
          s.name?.toLowerCase().includes(q) ||
          (s.roll_number && s.roll_number.toLowerCase().includes(q)) ||
          (s.course && s.course.toLowerCase().includes(q)) ||
          (s.batch && s.batch.toLowerCase().includes(q)) ||
          (s.best_role && s.best_role.toLowerCase().includes(q)) ||
          (s.placement_company && s.placement_company.toLowerCase().includes(q))
      );
    }
    list.sort((a, b) => {
      let vA = a[gridSortBy];
      let vB = b[gridSortBy];
      if (typeof vA === "string") vA = vA.toLowerCase();
      if (typeof vB === "string") vB = vB.toLowerCase();
      if (vA < vB) return gridSortDir === "asc" ? -1 : 1;
      if (vA > vB) return gridSortDir === "asc" ? 1 : -1;
      return 0;
    });
    return list;
  }, [data?.students, data?.leaderboard, gridSearch, gridSortBy, gridSortDir]);

  const pagedStudents = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return gridStudents.slice(start, start + pageSize);
  }, [gridStudents, currentPage]);

  const totalPages = Math.ceil(gridStudents.length / pageSize) || 1;

  const toggleSort = (col) => {
    if (gridSortBy === col) {
      setGridSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setGridSortBy(col);
      setGridSortDir("desc");
    }
  };

  // CSV Export with formula injection protection
  const exportStudentsCsv = () => {
    if (!gridStudents.length) return;
    const headers = [
      "Rank",
      "Name",
      "Roll Number",
      "Course",
      "Batch",
      "Overall Score",
      "Attendance %",
      "Readiness",
      "Placed",
      "Company",
      "Designation",
      "Salary",
      "Top Role",
      "Fit Tier",
    ];

    let csv = headers.map(escapeCsvCell).join(",") + "\r\n";
    gridStudents.forEach((s) => {
      const row = [
        s.rank || "",
        s.name || "",
        s.roll_number || "",
        s.course || "",
        s.batch || "",
        s.overall_score || 0,
        s.attendance_pct !== null ? `${s.attendance_pct}%` : "N/A",
        s.placement_ready ? "Ready" : "Needs Prep",
        s.is_placed ? "Placed" : "Unplaced",
        s.placement_company || "",
        s.placement_designation || "",
        s.placement_salary || "",
        s.best_role || "",
        s.fit_tier || "",
      ];
      csv += row.map(escapeCsvCell).join(",") + "\r\n";
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `CCDP_Students_${selectedBatch || "All"}_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Layout
      title="Skill Bay Academy — Power BI Placement Intelligence"
      subtitle="Executive Career & Competency Development Program (CCDP Analytics & Kauvery Hospital Matching)."
    >
      {/* ── Top Power BI Control Bar & Header ──────────────────────────────── */}
      <div className="space-y-4 mb-6">
        {/* Executive Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 rounded-2xl bg-gradient-to-r from-brand-maroon/15 via-brand-purple/10 to-surface-dim border border-brand-maroon/20">
          <div className="flex items-center gap-3.5">
            <div className="h-11 w-11 rounded-2xl bg-gradient-to-br from-brand-maroon to-brand-purple flex items-center justify-center text-white shadow-md">
              <Hospital size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-display font-bold text-base text-ink">
                  Kauvery Hospital CCDP Placement Suite
                </h2>
                <Badge tone="success" className="text-[10px] px-2 py-0.5">
                  Live Stream
                </Badge>
              </div>
              <p className="text-xs text-ink-muted mt-0.5">
                Batch: <strong className="text-ink">{selectedBatch || data?.batch_list?.[0] || "All Batches"}</strong> · Single Source of Truth Analytics
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <Button
              variant="secondary"
              onClick={() => refetch()}
              disabled={isRefetching}
              className="text-xs flex items-center gap-1.5 py-1.5 px-3"
            >
              <RefreshCw size={13} className={isRefetching ? "animate-spin" : ""} />
              <span>{isRefetching ? "Syncing..." : "Sync BI"}</span>
            </Button>

            <Button
              variant="secondary"
              onClick={exportStudentsCsv}
              className="text-xs flex items-center gap-1.5 py-1.5 px-3"
            >
              <Download size={13} />
              <span>Export CSV</span>
            </Button>

            <Link to="/upload">
              <Button className="text-xs flex items-center gap-1.5 py-1.5 px-3">
                <FileSpreadsheet size={13} />
                <span>Upload Batch</span>
              </Button>
            </Link>
          </div>
        </div>

        {/* ── Cross-Filtering Slicers Card ────────────────────────────────────── */}
        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-ink">
              <SlidersHorizontal size={14} className="text-brand-maroon" />
              <span>Interactive Power BI Slicers & Cross-Filters</span>
              {activeFilterCount > 0 && (
                <Badge tone="brand" className="text-[10px] py-0 px-1.5">
                  {activeFilterCount} active
                </Badge>
              )}
            </div>

            {activeFilterCount > 0 && (
              <button
                onClick={resetFilters}
                className="text-xs font-semibold text-brand-pink hover:text-brand-maroon flex items-center gap-1 transition-colors"
              >
                <X size={12} />
                <span>Reset All Filters</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1 border-t border-surface-border">
            {/* Slicer 1: Batch */}
            <div>
              <label className="text-[11px] font-semibold text-ink-faint block mb-1">
                Batch Slicer:
              </label>
              <select
                value={selectedBatch}
                onChange={(e) => updateFilters({ batch: e.target.value })}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink font-medium focus:outline-none focus:ring-2 focus:ring-brand-maroon/30"
              >
                <option value="">All Batches</option>
                {filteredBatchList.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            </div>

            {/* Slicer 2: Course */}
            <div>
              <label className="text-[11px] font-semibold text-ink-faint block mb-1">
                Course Track Slicer:
              </label>
              <select
                value={selectedCourse}
                onChange={(e) => updateFilters({ course: e.target.value })}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink font-medium focus:outline-none focus:ring-2 focus:ring-brand-maroon/30"
              >
                <option value="">All Courses & Tracks</option>
                {data?.course_list?.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            {/* Slicer 3: Performance Tier */}
            <div>
              <label className="text-[11px] font-semibold text-ink-faint block mb-1">
                Performance Tier:
              </label>
              <select
                value={selectedTier}
                onChange={(e) => updateFilters({ tier: e.target.value })}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink font-medium focus:outline-none focus:ring-2 focus:ring-brand-maroon/30"
              >
                <option value="">All Performance Bands</option>
                <option value="tier_1">Tier 1: High Distinction (≥80%)</option>
                <option value="tier_2">Tier 2: Placement Ready (60-79%)</option>
                <option value="tier_3">Tier 3: Moderate Support (40-59%)</option>
                <option value="tier_4">Tier 4: Critical Remediation (&lt;40%)</option>
              </select>
            </div>

            {/* Slicer 4: Readiness & Placed Status */}
            <div>
              <label className="text-[11px] font-semibold text-ink-faint block mb-1">
                Placement & Readiness:
              </label>
              <select
                value={selectedPlaced ? `placed_${selectedPlaced}` : selectedReadiness}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val.startsWith("placed_")) {
                    updateFilters({ placed: val.replace("placed_", ""), readiness: "" });
                  } else {
                    updateFilters({ readiness: val, placed: "" });
                  }
                }}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink font-medium focus:outline-none focus:ring-2 focus:ring-brand-maroon/30"
              >
                <option value="">All Candidates</option>
                <option value="ready">Placement Ready Only</option>
                <option value="needs_training">Needs Remediation Only</option>
                <option value="placed_placed">Placed Candidates Only</option>
                <option value="placed_unplaced">Unplaced Candidates Only</option>
              </select>
            </div>
          </div>

          {/* Quick Active Filter Removable Chips */}
          {activeFilterCount > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-surface-border">
              <span className="text-[10px] font-semibold text-ink-faint">Active Filters:</span>
              {selectedBatch && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-brand-maroon/10 text-brand-maroon font-medium">
                  Batch: {selectedBatch}
                  <button onClick={() => updateFilters({ batch: "" })}>✕</button>
                </span>
              )}
              {selectedTier && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-brand-maroon/10 text-brand-maroon font-medium">
                  Tier: {selectedTier}
                  <button onClick={() => updateFilters({ tier: "" })}>✕</button>
                </span>
              )}
              {selectedReadiness && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-brand-maroon/10 text-brand-maroon font-medium">
                  Readiness: {selectedReadiness}
                  <button onClick={() => updateFilters({ readiness: "" })}>✕</button>
                </span>
              )}
              {selectedPlaced && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-brand-maroon/10 text-brand-maroon font-medium">
                  Placement: {selectedPlaced}
                  <button onClick={() => updateFilters({ placed: "" })}>✕</button>
                </span>
              )}
              {minScoreParam && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] bg-brand-maroon/10 text-brand-maroon font-medium">
                  Score: {minScoreParam}–{maxScoreParam}%
                  <button onClick={() => updateFilters({ min_score: "", max_score: "" })}>✕</button>
                </span>
              )}
            </div>
          )}
        </Card>
      </div>

      {isLoading && (
        <div className="py-12 flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-3 border-brand-maroon border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-ink-muted">Loading live placement analytics...</span>
        </div>
      )}

      {error && (
        <Card className="p-4 border-danger/30 bg-danger/5 text-sm text-danger mb-6 flex items-center justify-between">
          <span>Failed to reach placement analytics engine. Please check backend connection.</span>
          <Button variant="secondary" onClick={() => refetch()} className="text-xs">
            Retry
          </Button>
        </Card>
      )}

      {data && (
        <div className="space-y-6">
          {/* ── KPI Row: Power BI Verified Metrics ────────────────────────────── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-6 gap-4">
            {/* 1. Placement Readiness Gauge (Task 2) */}
            <div className="sm:col-span-2 xl:col-span-2">
              <PowerBiGauge
                title="Cohort Placement Readiness"
                value={data.placement_ready_pct || 0}
                target={data.target_metrics?.placement_target_pct || 80.0}
                qualifiedCount={data.placement_ready ?? 0}
                totalCount={data.total_students ?? 0}
                placedCount={data.placed_count ?? 0}
                isLoading={isLoading}
                isError={Boolean(error)}
                onRetry={refetch}
              />
            </div>

            {/* 2. Average Competency Score */}
            <PowerBiKpiCard
              icon={TrendingUp}
              title="Avg CCDP Score"
              value={data.average_score ?? 0}
              unit="/ 100"
              target={data.target_metrics?.score_target || 75.0}
              targetLabel="Benchmark"
              delta={
                data.average_score >= 75
                  ? `+${(data.average_score - 75).toFixed(1)} pts`
                  : `${(data.average_score - 75).toFixed(1)} pts`
              }
              deltaType={data.average_score >= 75 ? "positive" : "negative"}
              progressPct={data.average_score}
              accentColor="#8B1D55"
              subtext={data.top_performer ? `Top: ${data.top_performer}` : "Verified genuine skills"}
            />

            {/* 3. Remediation Required */}
            <PowerBiKpiCard
              icon={AlertTriangle}
              title="Remediation Required"
              value={data.need_training ?? 0}
              unit="candidates"
              badgeText={`Crit: ${data.need_training_critical ?? 0} | Mod: ${data.need_training_moderate ?? 0}`}
              delta={
                data.need_training_critical === 0
                  ? "0 Critical"
                  : `${data.need_training_critical} Critical`
              }
              deltaType={data.need_training_critical === 0 ? "positive" : "negative"}
              accentColor="#EFBC19"
              progressPct={
                data.total_students > 0
                  ? ((data.total_students - data.need_training) / data.total_students) * 100
                  : 100
              }
              subtext="Tailored 30-day coaching needed"
            />

            {/* 4. Placed (Actual Offers from Placement Sheet) */}
            <PowerBiKpiCard
              icon={Briefcase}
              title="Placed (Hospital Offers)"
              value={data.placed_count ?? 0}
              unit={`/ ${data.total_students ?? 0}`}
              target={`${data.placed_pct ?? 0}%`}
              targetLabel="Offer Rate"
              delta={`${data.placed_count ?? 0} Confirmed`}
              deltaType="positive"
              accentColor="#22C55E"
              progressPct={data.placed_pct ?? 0}
              subtext="Offers from Placement Sheet"
            />

            {/* 5. Typing Speed Metric */}
            <PowerBiKpiCard
              icon={Keyboard}
              title="Typing Proficiency"
              value={data.typing_stats?.avg ?? "—"}
              unit={data.typing_stats?.avg ? "WPM" : ""}
              target={`${data.target_metrics?.typing_target_wpm || 30} WPM`}
              targetLabel="Benchmark"
              delta={
                data.typing_stats?.avg
                  ? `${data.typing_stats.above_target_count || 0} Met Target`
                  : "Not tested"
              }
              deltaType={
                data.typing_stats?.avg >= (data.target_metrics?.typing_target_wpm || 30)
                  ? "positive"
                  : "negative"
              }
              accentColor="#72398C"
              progressPct={
                data.typing_stats?.avg
                  ? Math.min(100, (data.typing_stats.avg / 40) * 100)
                  : 0
              }
              subtext="Kept separate from skill mean"
            />
          </div>

          {/* ── Navigation Tabs ──────────────────────────────────────────────── */}
          <div className="flex items-center justify-between border-b border-surface-border pb-3">
            <div className="flex items-center gap-2">
              {[
                { key: "overview", label: "Executive Analytics View", icon: BarChart3 },
                { key: "matrix", label: "Kauvery Hospital Placement Matrix", icon: Hospital },
                { key: "grid", label: "Student Power BI Data Grid", icon: Table },
              ].map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                    activeTab === key
                      ? "bg-brand-maroon text-white shadow-md"
                      : "bg-surface-dim border border-surface-border text-ink-muted hover:text-ink hover:bg-surface-high"
                  }`}
                >
                  <Icon size={14} />
                  <span>{label}</span>
                </button>
              ))}
            </div>

            <div className="text-xs text-ink-faint hidden sm:block">
              Scope: <span className="font-semibold text-ink">{data.total_students}</span> candidates
            </div>
          </div>

          {/* ══════════════════════════════════════════════════════════════════════
              TAB 1: EXECUTIVE ANALYTICS VIEW
          ══════════════════════════════════════════════════════════════════════ */}
          {activeTab === "overview" && (
            <div className="space-y-6">
              {/* Row 1: Score Tier Funnel + Competency Radar */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Score Tier Distribution (Clickable Slicer) */}
                <Card className="p-5 flex flex-col">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                        <Target size={16} className="text-brand-maroon" />
                        Performance Tier Bands (Click to filter)
                      </h3>
                      <p className="text-xs text-ink-faint mt-0.5">
                        Students partitioned by central settings thresholds
                      </p>
                    </div>
                    <Badge tone="brand">Tier Slices</Badge>
                  </div>

                  {data.score_tier_distribution?.length === 0 ? (
                    <EmptyState text="No student score distribution available." />
                  ) : (
                    <div className="space-y-3 my-auto">
                      {data.score_tier_distribution?.map((t) => (
                        <div
                          key={t.code}
                          onClick={() =>
                            updateFilters({ tier: selectedTier === t.code ? "" : t.code })
                          }
                          className={`p-3 rounded-xl border transition-all cursor-pointer ${
                            selectedTier === t.code
                              ? "border-brand-maroon bg-brand-maroon/10 shadow-sm"
                              : "border-surface-border bg-surface-container hover:bg-surface-high"
                          }`}
                        >
                          <div className="flex items-center justify-between text-xs mb-1.5">
                            <span className="font-semibold text-ink flex items-center gap-2">
                              <span
                                className="w-2.5 h-2.5 rounded-full"
                                style={{ backgroundColor: t.color }}
                              />
                              {t.tier}
                            </span>
                            <span className="font-bold tabular-nums text-ink">
                              {t.count} ({t.pct}%)
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-surface-high overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{
                                width: `${Math.max(t.pct, 4)}%`,
                                backgroundColor: t.color,
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                {/* Cohort Competency Radar Chart */}
                <Card className="p-5 flex flex-col">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                        <Award size={16} className="text-brand-pink" />
                        Cohort Competency Radar vs Benchmark
                      </h3>
                      <p className="text-xs text-ink-faint mt-0.5">
                        Only genuine skills (clothing sizes & metrics excluded)
                      </p>
                    </div>
                    <Badge tone="success">
                      Benchmark: {data.target_metrics?.score_target || 75}%
                    </Badge>
                  </div>

                  {data.competency_radar?.length === 0 ? (
                    <EmptyState text="No competency radar data detected in current batch." />
                  ) : (
                    <div className="w-full h-72">
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={data.competency_radar}>
                          <PolarGrid stroke={chartGrid} />
                          <PolarAngleAxis
                            dataKey="skill"
                            stroke={chartText}
                            fontSize={11}
                            tick={{ fill: chartText }}
                          />
                          <PolarRadiusAxis
                            domain={[0, 100]}
                            stroke={chartText}
                            fontSize={9}
                            angle={30}
                          />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Radar
                            name="Cohort Score"
                            dataKey="score"
                            stroke="#8B1D55"
                            fill="#8B1D55"
                            fillOpacity={0.45}
                          />
                          <Radar
                            name="Hospital Benchmark"
                            dataKey="benchmark"
                            stroke="#22C55E"
                            fill="#22C55E"
                            fillOpacity={0.1}
                            strokeDasharray="4 4"
                          />
                          <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }} />
                        </RadarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </Card>
              </div>

              {/* Row 2: Score Distribution Histogram + Placement Funnel */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Score Distribution Histogram (Replaces single-bar course chart) */}
                <Card className="p-5 flex flex-col">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                        <BarChart3 size={16} className="text-brand-purple" />
                        Score Distribution Histogram (Click bin to filter)
                      </h3>
                      <p className="text-xs text-ink-faint mt-0.5">
                        Distribution across 5 score bands
                      </p>
                    </div>
                  </div>

                  {data.score_distribution_histogram?.length === 0 ? (
                    <EmptyState text="No score histogram data available." />
                  ) : (
                    <div className="w-full h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data.score_distribution_histogram}>
                          <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} vertical={false} />
                          <XAxis dataKey="bin" stroke={chartText} fontSize={11} />
                          <YAxis stroke={chartText} fontSize={11} allowDecimals={false} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Bar
                            dataKey="count"
                            name="Candidates"
                            fill="#8B1D55"
                            radius={[6, 6, 0, 0]}
                            onClick={(entry) => {
                              const binMap = {
                                "0–20%": [0, 20],
                                "21–40%": [21, 40],
                                "41–60%": [41, 60],
                                "61–80%": [61, 80],
                                "81–100%": [81, 100],
                              };
                              const range = binMap[entry.bin];
                              if (range) {
                                if (minScoreParam === String(range[0])) {
                                  updateFilters({ min_score: "", max_score: "" });
                                } else {
                                  updateFilters({ min_score: range[0], max_score: range[1] });
                                }
                              }
                            }}
                            cursor="pointer"
                          >
                            {data.score_distribution_histogram.map((entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={
                                  minScoreParam ===
                                  String(
                                    entry.bin === "0–20%"
                                      ? 0
                                      : entry.bin === "21–40%"
                                      ? 21
                                      : entry.bin === "41–60%"
                                      ? 41
                                      : entry.bin === "61–80%"
                                      ? 61
                                      : 81
                                  )
                                    ? "#DE4F73"
                                    : "#8B1D55"
                                }
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </Card>

                {/* Placement Funnel: Enrolled -> Placement Ready -> Placed */}
                <Card className="p-5 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                          <TrendingUp size={16} className="text-brand-pink" />
                          Placement Funnel
                        </h3>
                        <p className="text-xs text-ink-faint mt-0.5">
                          Enrolled candidates progressing to readiness and hospital offers
                        </p>
                      </div>
                    </div>

                    <div className="space-y-3.5 my-3">
                      {data.placement_funnel?.map((st) => (
                        <div
                          key={st.stage}
                          onClick={() => {
                            if (st.stage === "Placement Ready") {
                              updateFilters({ readiness: selectedReadiness === "ready" ? "" : "ready" });
                            } else if (st.stage === "Placed") {
                              updateFilters({ placed: selectedPlaced === "placed" ? "" : "placed" });
                            } else {
                              updateFilters({ readiness: "", placed: "" });
                            }
                          }}
                          className="p-3 rounded-xl bg-surface-container border border-surface-border cursor-pointer hover:bg-surface-high transition-colors"
                        >
                          <div className="flex items-center justify-between text-xs mb-1.5">
                            <span className="font-semibold text-ink">{st.stage}</span>
                            <span className="font-bold tabular-nums text-ink">
                              {st.count} ({st.pct}%)
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-surface-high overflow-hidden">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-brand-maroon to-brand-pink transition-all duration-500"
                              style={{ width: `${Math.max(st.pct, 4)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {data.company_breakdown?.length > 0 && (
                    <div className="pt-3 border-t border-surface-border">
                      <span className="text-[11px] font-semibold text-ink-muted block mb-1">
                        Placed by Employer / Facility:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {data.company_breakdown.map((c) => (
                          <span
                            key={c.company}
                            className="text-[10px] px-2 py-0.5 rounded-md bg-surface-high text-ink font-medium border border-surface-border"
                          >
                            {c.company}: <strong>{c.placed_count}</strong>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              </div>

              {/* Row 3: Priority Remediation + Professional Compliance */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                {/* Priority Remediation Matrix */}
                <Card className="p-5 lg:col-span-2 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                          <ShieldAlert size={16} className="text-brand-yellow" />
                          Priority Remediation Matrix
                        </h3>
                        <p className="text-xs text-ink-faint mt-0.5">
                          Ranked by gap vs 75% hospital benchmark with affected candidate count
                        </p>
                      </div>
                      <Link to="/ai?prompt=Generate%20a%2030-day%20remediation%20plan%20for%20at-risk%20students">
                        <Button className="text-xs py-1 px-2.5 flex items-center gap-1">
                          <Sparkles size={12} />
                          <span>Generate 30-Day Plan</span>
                        </Button>
                      </Link>
                    </div>

                    <div className="space-y-2.5 my-3">
                      {data.priority_remediation?.slice(0, 5).map((s) => (
                        <div
                          key={s.skill}
                          className="p-2.5 rounded-xl bg-surface-container border border-surface-border space-y-1"
                        >
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-ink">{s.skill}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] text-danger font-semibold bg-danger/10 px-1.5 py-0.5 rounded">
                                {s.affected_students_count} at risk
                              </span>
                              <span className="font-bold tabular-nums text-ink">
                                Gap: {s.gap} pts
                              </span>
                            </div>
                          </div>
                          <div className="flex items-center justify-between text-[11px] text-ink-faint">
                            <span>
                              Cohort Avg: <strong>{s.average_score}%</strong>
                            </span>
                            {s.at_risk_students?.length > 0 && (
                              <span className="truncate max-w-[240px]">
                                Focus: {s.at_risk_students.join(", ")}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>

                {/* Professional Compliance Card (Shirt, Trouser, Tie, Shoe size) */}
                <Card className="p-5 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                        <Shirt size={16} className="text-brand-purple" />
                        Professional Compliance
                      </h3>
                      <Badge tone="brand">Uniform</Badge>
                    </div>
                    <p className="text-xs text-ink-faint mb-3">
                      Uniform sizes & professional gear recorded (kept separate from skill scores)
                    </p>

                    <div className="space-y-2.5 my-auto">
                      {data.professional_compliance?.length === 0 ? (
                        <EmptyState text="No uniform or compliance data recorded." />
                      ) : (
                        data.professional_compliance?.map((c) => (
                          <div
                            key={c.item}
                            className="p-2.5 rounded-xl bg-surface-container border border-surface-border"
                          >
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="font-semibold text-ink">{c.item}</span>
                              <span className="font-bold tabular-nums text-ink">
                                {c.recorded_count} / {data.total_students} ({c.pct}%)
                              </span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-high overflow-hidden">
                              <div
                                className="h-full rounded-full bg-brand-purple transition-all duration-500"
                                style={{ width: `${c.pct}%` }}
                              />
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════════════
              TAB 2: KAUVERY HOSPITAL DEMAND & SUPPLY MATRIX
          ══════════════════════════════════════════════════════════════════════ */}
          {activeTab === "matrix" && (
            <Card className="p-5">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5 pb-4 border-b border-surface-border">
                <div>
                  <h3 className="font-display font-bold text-base text-ink flex items-center gap-2">
                    <Hospital size={18} className="text-brand-maroon" />
                    Kauvery Hospital Facility Placement Matrix
                  </h3>
                  <p className="text-xs text-ink-faint mt-0.5">
                    Matching vacancies across Kauvery facilities with eligible candidates in current scope
                  </p>
                </div>
                <Link to="/jobs">
                  <Button className="text-xs px-3.5 py-2 flex items-center gap-1.5">
                    <span>Manage Roles</span>
                    <ChevronRight size={14} />
                  </Button>
                </Link>
              </div>

              {data.kauvery_unit_matrix?.length === 0 ? (
                <EmptyState text="No active placement roles found." />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-surface-border text-ink-faint font-semibold uppercase tracking-wider">
                        <th className="pb-3">Role Title & Department</th>
                        <th className="pb-3">Kauvery Unit</th>
                        <th className="pb-3 text-center">Openings</th>
                        <th className="pb-3 text-center">Matched Candidates</th>
                        <th className="pb-3">Fulfillment Progress</th>
                        <th className="pb-3 text-center">Demand</th>
                        <th className="pb-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-border">
                      {data.kauvery_unit_matrix.map((r) => (
                        <tr key={r.id || r.role_name} className="hover:bg-surface-high/50 transition-colors">
                          <td className="py-3 font-semibold text-ink">
                            <div className="text-sm font-semibold text-ink">{r.role_name}</div>
                            <div className="text-[11px] text-ink-faint font-normal">{r.department}</div>
                          </td>
                          <td className="py-3 text-brand-maroon font-medium">
                            <div className="flex items-center gap-1.5">
                              <Hospital size={13} className="shrink-0" />
                              <span>{r.kauvery_unit}</span>
                            </div>
                          </td>
                          <td className="py-3 text-center font-bold tabular-nums text-ink">
                            {r.openings}
                          </td>
                          <td className="py-3 text-center font-bold tabular-nums text-brand-purple">
                            {r.matched_candidates} candidates
                          </td>
                          <td className="py-3 min-w-[140px]">
                            <div className="flex items-center justify-between text-[11px] mb-1">
                              <span className="text-ink-faint">Fulfillment</span>
                              <span className="font-bold text-ink">{r.fulfillment_rate}%</span>
                            </div>
                            <div className="w-full h-2 rounded-full bg-surface-high overflow-hidden">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-brand-maroon to-brand-pink"
                                style={{ width: `${Math.min(100, r.fulfillment_rate)}%` }}
                              />
                            </div>
                          </td>
                          <td className="py-3 text-center">
                            <Badge
                              tone={
                                r.demand_level === "High"
                                  ? "success"
                                  : r.demand_level === "Medium"
                                  ? "brand"
                                  : "warning"
                              }
                            >
                              {r.demand_level}
                            </Badge>
                          </td>
                          <td className="py-3 text-right">
                            <Link
                              to="/jobs"
                              className="inline-flex items-center gap-1 text-xs font-semibold text-brand-maroon hover:text-brand-pink"
                            >
                              <span>Candidates</span>
                              <ChevronRight size={13} />
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          )}

          {/* ══════════════════════════════════════════════════════════════════════
              TAB 3: STUDENT POWER BI DATA GRID
          ══════════════════════════════════════════════════════════════════════ */}
          {activeTab === "grid" && (
            <Card className="p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
                <div>
                  <h3 className="font-display font-bold text-base text-ink flex items-center gap-2">
                    <Table size={18} className="text-brand-maroon" />
                    Student Cohort Power BI Matrix
                  </h3>
                  <p className="text-xs text-ink-faint mt-0.5">
                    Showing {gridStudents.length} candidates in current filter
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <div className="relative min-w-[220px]">
                    <input
                      type="text"
                      value={gridSearch}
                      onChange={(e) => {
                        setGridSearch(e.target.value);
                        setCurrentPage(1);
                      }}
                      placeholder="Search candidate, roll, role, company..."
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand-maroon/30"
                    />
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-surface-border text-ink-faint font-semibold uppercase tracking-wider">
                      <th className="pb-3 text-center">Rank</th>
                      <th className="pb-3">
                        <button
                          onClick={() => toggleSort("name")}
                          className="flex items-center gap-1 hover:text-ink"
                        >
                          <span>Candidate</span>
                          <ArrowUpDown size={11} />
                        </button>
                      </th>
                      <th className="pb-3">Course / Batch</th>
                      <th className="pb-3 text-center">
                        <button
                          onClick={() => toggleSort("overall_score")}
                          className="inline-flex items-center gap-1 hover:text-ink"
                        >
                          <span>Overall Score</span>
                          <ArrowUpDown size={11} />
                        </button>
                      </th>
                      <th className="pb-3 text-center">
                        <button
                          onClick={() => toggleSort("attendance_pct")}
                          className="inline-flex items-center gap-1 hover:text-ink"
                        >
                          <span>Attendance</span>
                          <ArrowUpDown size={11} />
                        </button>
                      </th>
                      <th className="pb-3 text-center">Readiness</th>
                      <th className="pb-3 text-center">Placement</th>
                      <th className="pb-3">Best Role & Fit</th>
                      <th className="pb-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {pagedStudents.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="py-8 text-center text-ink-faint">
                          No candidates found matching the current query.
                        </td>
                      </tr>
                    ) : (
                      pagedStudents.map((s) => (
                        <tr key={s.id || s.name} className="hover:bg-surface-high/50 transition-colors">
                          <td className="py-3 text-center font-bold text-ink">
                            #{s.rank || "—"}
                          </td>
                          <td className="py-3 font-semibold text-ink">
                            <div className="font-semibold text-ink">{s.name}</div>
                            <div className="text-[10px] text-ink-faint font-normal">
                              {s.roll_number || "—"}
                            </div>
                          </td>
                          <td className="py-3 text-ink-muted">
                            <div>{s.course || "CCDP"}</div>
                            <div className="text-[10px] text-ink-faint">{s.batch || ""}</div>
                          </td>
                          <td className="py-3 text-center min-w-[120px]">
                            <div className="font-bold tabular-nums text-ink text-sm">
                              {s.overall_score}%
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-high overflow-hidden mt-1">
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${s.overall_score}%`,
                                  backgroundColor:
                                    s.overall_score >= 80
                                      ? "#22C55E"
                                      : s.overall_score >= 60
                                      ? "#8B1D55"
                                      : s.overall_score >= 40
                                      ? "#EFBC19"
                                      : "#EF4444",
                                }}
                              />
                            </div>
                          </td>
                          <td className="py-3 text-center font-semibold tabular-nums text-ink-muted">
                            {s.attendance_pct !== null && s.attendance_pct !== undefined
                              ? `${s.attendance_pct}%`
                              : "N/A"}
                          </td>
                          <td className="py-3 text-center">
                            <Badge tone={s.placement_ready ? "success" : "warning"}>
                              {s.placement_ready ? "Ready" : "Needs Prep"}
                            </Badge>
                          </td>
                          <td className="py-3 text-center">
                            <Badge tone={s.is_placed ? "success" : "neutral"}>
                              {s.is_placed ? "Placed" : "Unplaced"}
                            </Badge>
                          </td>
                          <td className="py-3">
                            <div className="font-medium text-ink truncate max-w-[150px]">
                              {s.best_role || "Healthcare Operations"}
                            </div>
                            <Badge
                              tone={FIT_TONE[s.fit_tier] || "neutral"}
                              className="text-[9px] px-1.5 py-0 mt-0.5"
                            >
                              {s.fit_tier || "Fit"}
                            </Badge>
                          </td>
                          <td className="py-3 text-right">
                            {s.id ? (
                              <Link
                                to={`/students/${s.id}`}
                                className="p-1.5 inline-flex rounded-lg bg-surface-high hover:bg-surface-container text-ink-muted hover:text-ink transition-colors"
                                title="View Profile"
                              >
                                <Eye size={14} />
                              </Link>
                            ) : (
                              <span className="text-ink-faint">—</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination Bar */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-3 border-t border-surface-border text-xs text-ink-muted">
                  <span>
                    Page {currentPage} of {totalPages} ({gridStudents.length} candidates)
                  </span>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="px-2.5 py-1 rounded-lg border border-surface-border bg-surface hover:bg-surface-high disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                      className="px-2.5 py-1 rounded-lg border border-surface-border bg-surface hover:bg-surface-high disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </Card>
          )}
        </div>
      )}
    </Layout>
  );
}
