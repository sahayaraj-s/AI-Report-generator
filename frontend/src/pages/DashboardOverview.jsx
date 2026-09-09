import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Users, CheckCircle2, AlertTriangle, TrendingUp, Award, Percent,
  Building2, Sparkles, Filter, Download, RefreshCw, Layers,
  BarChart3, LayoutGrid, Table, ChevronRight, Eye, ShieldAlert,
  Hospital, Target, ArrowUpRight, Check, X, SlidersHorizontal,
  FileSpreadsheet, FileText, ArrowUpDown
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, LineChart, Line, AreaChart, Area, RadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, Radar, Legend, Cell,
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
  "Eligible": "brand",
  "Not Eligible": "neutral",
};

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

  // Power BI Multi-Slicers State
  const [selectedBatch, setSelectedBatch] = useState("");
  const [selectedCourse, setSelectedCourse] = useState("");
  const [selectedTier, setSelectedTier] = useState("");
  const [selectedReadiness, setSelectedReadiness] = useState("");
  const [activeTab, setActiveTab] = useState("overview"); // 'overview' | 'matrix' | 'grid'
  const [gridSearch, setGridSearch] = useState("");
  const [gridSortBy, setGridSortBy] = useState("overall_score");
  const [gridSortDir, setGridSortDir] = useState("desc");

  // Query Dashboard Data with Slicers
  const { data, isLoading, isRefetching, error, refetch } = useQuery({
    queryKey: [
      "dashboard-stats",
      {
        batch: selectedBatch,
        course: selectedCourse,
        performance_tier: selectedTier,
        readiness: selectedReadiness,
      },
    ],
    queryFn: async () => {
      const params = {};
      if (selectedBatch) params.batch = selectedBatch;
      if (selectedCourse) params.course = selectedCourse;
      if (selectedTier) params.performance_tier = selectedTier;
      if (selectedReadiness) params.readiness = selectedReadiness;
      return (await api.get("/api/dashboard/stats", { params })).data;
    },
  });

  // Calculate active filter count
  const activeFilterCount = [
    selectedBatch,
    selectedCourse,
    selectedTier,
    selectedReadiness,
  ].filter(Boolean).length;

  const resetFilters = () => {
    setSelectedBatch("");
    setSelectedCourse("");
    setSelectedTier("");
    setSelectedReadiness("");
  };

  // Filtered and sorted leaderboard / grid data
  const gridStudents = useMemo(() => {
    if (!data?.leaderboard) return [];
    let list = [...data.leaderboard];
    if (gridSearch.trim()) {
      const q = gridSearch.toLowerCase();
      list = list.filter(
        (s) =>
          s.name?.toLowerCase().includes(q) ||
          s.roll_number?.toLowerCase().includes(q) ||
          s.course?.toLowerCase().includes(q) ||
          s.batch?.toLowerCase().includes(q) ||
          s.best_role?.toLowerCase().includes(q)
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
  }, [data?.leaderboard, gridSearch, gridSortBy, gridSortDir]);

  const toggleSort = (col) => {
    if (gridSortBy === col) {
      setGridSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setGridSortBy(col);
      setGridSortDir("desc");
    }
  };

  return (
    <Layout
      title="Skill Bay Academy — Power BI Placement Intelligence"
      subtitle="Executive Career & Competency Development Program (CCDP 50-Day Analytics & Kauvery Hospital Matching)."
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
                  Live BI Stream
                </Badge>
              </div>
              <p className="text-xs text-ink-muted mt-0.5">
                50-Day Career & Competency Development Program · 12 Kauvery Hospital Units & Partner Network
              </p>
            </div>
          </div>

          {/* Quick Action Toolbar */}
          <div className="flex items-center flex-wrap gap-2 shrink-0">
            <button
              onClick={() => refetch()}
              disabled={isLoading || isRefetching}
              className="px-3 py-2 rounded-xl bg-surface-dim border border-surface-border text-xs font-semibold text-ink-muted hover:text-ink hover:bg-surface-high flex items-center gap-1.5 transition-colors shadow-sm"
              title="Refresh live data"
            >
              <RefreshCw size={13} className={isRefetching ? "animate-spin text-brand-pink" : ""} />
              <span>{isRefetching ? "Syncing..." : "Sync BI"}</span>
            </button>

            <a
              href={`${api.defaults.baseURL}/api/reports/institute/pdf`}
              target="_blank"
              rel="noreferrer"
            >
              <Button variant="secondary" className="text-xs px-3 py-2 flex items-center gap-1.5 shadow-sm">
                <FileText size={13} className="text-brand-maroon" />
                <span>Executive PDF</span>
              </Button>
            </a>

            <a
              href={`${api.defaults.baseURL}/api/reports/match/pdf${
                selectedBatch ? `?batch=${encodeURIComponent(selectedBatch)}` : ""
              }`}
              target="_blank"
              rel="noreferrer"
            >
              <Button variant="secondary" className="text-xs px-3 py-2 flex items-center gap-1.5 shadow-sm">
                <Target size={13} className="text-brand-purple" />
                <span>Match Matrix</span>
              </Button>
            </a>

            <a
              href={`${api.defaults.baseURL}/api/reports/batch/csv${
                selectedBatch ? `?batch=${encodeURIComponent(selectedBatch)}` : ""
              }`}
              target="_blank"
              rel="noreferrer"
            >
              <Button className="text-xs px-3.5 py-2 flex items-center gap-1.5 shadow-sm">
                <Download size={13} />
                <span>Export CSV</span>
              </Button>
            </a>
          </div>
        </div>

        {/* ── Interactive Power BI Slicers Bar ──────────────────────────────── */}
        <Card className="p-3.5 space-y-3 shadow-md">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-ink">
              <SlidersHorizontal size={15} className="text-brand-maroon" />
              <span>Interactive Power BI Slicers</span>
              {activeFilterCount > 0 && (
                <span className="px-2 py-0.5 rounded-full bg-brand-maroon text-white text-[10px] font-bold">
                  {activeFilterCount} Active
                </span>
              )}
            </div>

            {activeFilterCount > 0 && (
              <button
                onClick={resetFilters}
                className="text-xs font-medium text-brand-pink hover:text-brand-maroon flex items-center gap-1 transition-colors"
              >
                <X size={12} />
                <span>Reset All Slicers</span>
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
                onChange={(e) => setSelectedBatch(e.target.value)}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink font-medium focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
              >
                <option value="">All Batches</option>
                {data?.batch_list?.map((b) => (
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
                onChange={(e) => setSelectedCourse(e.target.value)}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink font-medium focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
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
                onChange={(e) => setSelectedTier(e.target.value)}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink font-medium focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
              >
                <option value="">All Performance Bands</option>
                <option value="tier_1">Tier 1: High Distinction (≥80%)</option>
                <option value="tier_2">Tier 2: Placement Ready (60-79%)</option>
                <option value="tier_3">Tier 3: Moderate Support (40-59%)</option>
                <option value="tier_4">Tier 4: Critical Remediation (&lt;40%)</option>
              </select>
            </div>

            {/* Slicer 4: Readiness Status */}
            <div>
              <label className="text-[11px] font-semibold text-ink-faint block mb-1">
                Readiness Filter:
              </label>
              <select
                value={selectedReadiness}
                onChange={(e) => setSelectedReadiness(e.target.value)}
                className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink font-medium focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
              >
                <option value="">All Candidates</option>
                <option value="ready">Placement Ready Only</option>
                <option value="needs_training">Needs Training / At-Risk Only</option>
              </select>
            </div>
          </div>

          {/* Quick Batch Filter Chips */}
          {data?.batch_list?.length > 0 ? (
            <div className="flex items-center gap-1.5 flex-wrap pt-2 border-t border-surface-border/60">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-ink-faint mr-1">
                Quick Chips:
              </span>
              <button
                onClick={() => setSelectedBatch("")}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                  !selectedBatch
                    ? "bg-brand-maroon text-white shadow-sm"
                    : "bg-surface-high text-ink-muted hover:text-ink"
                }`}
              >
                All
              </button>
              {data.batch_list.map((b) => (
                <button
                  key={b}
                  onClick={() => setSelectedBatch(selectedBatch === b ? "" : b)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                    selectedBatch === b
                      ? "bg-brand-maroon text-white shadow-sm"
                      : "bg-surface-high text-ink-muted hover:text-ink"
                  }`}
                >
                  {b}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2 pt-2 border-t border-surface-border/60 text-[11px] text-ink-faint">
              <span>No batches found — batches appear automatically after you</span>
              <a href="/upload" className="text-brand-maroon hover:text-brand-pink font-semibold underline underline-offset-2">upload an Excel file</a>.
            </div>
          )}
        </Card>
      </div>

      {isLoading && <p className="text-ink-muted text-sm py-8 text-center">Loading Power BI Analytics…</p>}
      {error && (
        <Card className="p-4 border-danger/30 bg-danger/5 text-sm text-danger mb-6">
          Couldn't reach the API — please ensure backend is running at http://localhost:8000.
        </Card>
      )}

      {data && (
        <div className="space-y-6">
          {/* ── Executive Power BI Metric Tiles ──────────────────────────────── */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {/* 1. Placement Readiness Gauge */}
            <PowerBiGauge
              title="Cohort Placement Readiness"
              value={data.placement_ready_pct || 0}
              target={data.target_metrics?.placement_target_pct || 80.0}
              subtitle={`${data.placement_ready} of ${data.total_students} students qualified`}
            />

            {/* 2. Average Competency Score */}
            <PowerBiKpiCard
              icon={TrendingUp}
              title="Avg CCDP Competency Score"
              value={data.average_score}
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
              subtext={
                data.top_performer
                  ? `Top Performer: ${data.top_performer}`
                  : "Comprehensive 50-day average"
              }
            />

            {/* 3. At-Risk & Remediation Required */}
            <PowerBiKpiCard
              icon={AlertTriangle}
              title="Remediation Required"
              value={data.need_training}
              unit="candidates"
              badgeText={`Critical: ${data.need_training_critical} | Mod: ${data.need_training_moderate}`}
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
              subtext="Tailored bootcamp sessions recommended"
            />

            {/* 4. Active Kauvery Openings & AI Accuracy */}
            <PowerBiKpiCard
              icon={Building2}
              title="Kauvery Placement Pipeline"
              value={data.total_openings > 0 ? data.total_openings : data.recruiters_partnered}
              unit={data.total_openings > 0 ? "openings" : "facilities"}
              target={`${data.recruiters_partnered} Units`}
              targetLabel="Hospital Scope"
              delta={`${data.ai_accuracy_pct}% AI Conf`}
              deltaType="positive"
              accentColor="#72398C"
              progressPct={data.ai_accuracy_pct}
              subtext="Priority roles mapped across 12 facilities"
            />
          </div>

          {/* ── View Mode Switcher Tabs ────────────────────────────────────────── */}
          <div className="flex items-center justify-between border-b border-surface-border pb-3">
            <div className="flex items-center gap-2">
              {[
                { key: "overview", label: "Executive Analytics View", icon: BarChart3 },
                { key: "matrix", label: "Kauvery Hospital Placement Matrix", icon: Hospital },
                { key: "grid", label: "Student BI Data Grid", icon: Table },
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
              Showing <span className="font-semibold text-ink">{data.total_students}</span> candidates
              in current scope
            </div>
          </div>

          {/* ══════════════════════════════════════════════════════════════════════
              TAB 1: EXECUTIVE ANALYTICS VIEW
          ══════════════════════════════════════════════════════════════════════ */}
          {activeTab === "overview" && (
            <div className="space-y-6">
              {/* Row 1: Score Tier Funnel + Competency Radar */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Score Tier Distribution */}
                <Card className="p-5 flex flex-col">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                        <Target size={16} className="text-brand-maroon" />
                        CCDP Score Tier Breakdown (Power BI Pyramid)
                      </h3>
                      <p className="text-xs text-ink-faint mt-0.5">
                        Performance band distribution across currently filtered students
                      </p>
                    </div>
                    <Badge tone="brand">Tier Slices</Badge>
                  </div>

                  {data.score_tier_distribution?.length === 0 ? (
                    <EmptyState text="No student score distribution available." />
                  ) : (
                    <div className="space-y-3.5 my-auto">
                      {data.score_tier_distribution?.map((t) => (
                        <div
                          key={t.code}
                          onClick={() => setSelectedTier(selectedTier === t.code ? "" : t.code)}
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
                        Skill averages against the 75% hospital placement benchmark
                      </p>
                    </div>
                    <Badge tone="success">Benchmark: 75%</Badge>
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
                            name="Hospital Benchmark (75%)"
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

              {/* Row 2: Course Comparison + 50-Day Trajectory */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Course Track Performance Comparison */}
                <Card className="p-5 flex flex-col">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                        <BarChart3 size={16} className="text-brand-purple" />
                        Course & Track Performance Comparison
                      </h3>
                      <p className="text-xs text-ink-faint mt-0.5">
                        Average score and total candidates across course tracks
                      </p>
                    </div>
                  </div>

                  {data.course_comparison?.length === 0 ? (
                    <EmptyState text="No course comparison data available." />
                  ) : (
                    <div className="w-full h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data.course_comparison}>
                          <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} vertical={false} />
                          <XAxis dataKey="course" stroke={chartText} fontSize={11} />
                          <YAxis stroke={chartText} fontSize={11} domain={[0, 100]} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Bar
                            dataKey="average_score"
                            name="Avg Score"
                            fill="#8B1D55"
                            radius={[6, 6, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </Card>

                {/* 50-Day Competency Growth Trajectory */}
                <Card className="p-5 flex flex-col">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                        <TrendingUp size={16} className="text-brand-pink" />
                        50-Day Competency Growth & Trajectory
                      </h3>
                      <p className="text-xs text-ink-faint mt-0.5">
                        Progression milestones across intake, mid-term, and final evaluation
                      </p>
                    </div>
                  </div>

                  {data.monthly_progress?.length === 0 ? (
                    <EmptyState text="No progress trajectory data available." />
                  ) : (
                    <div className="w-full h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={data.monthly_progress}>
                          <defs>
                            <linearGradient id="scoreGrowth" x1="0%" y1="0%" x2="0%" y2="100%">
                              <stop offset="0%" stopColor="#DE4F73" stopOpacity={0.6} />
                              <stop offset="100%" stopColor="#DE4F73" stopOpacity={0.05} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke={chartGrid} vertical={false} />
                          <XAxis dataKey="month" stroke={chartText} fontSize={11} />
                          <YAxis stroke={chartText} fontSize={11} domain={[0, 100]} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Area
                            type="monotone"
                            dataKey="average_score"
                            name="Avg Competency"
                            stroke="#DE4F73"
                            strokeWidth={3}
                            fill="url(#scoreGrowth)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </Card>
              </div>

              {/* Row 3: Weak Skill Remediation Heatmap + Leaderboard Spotlight */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                {/* Weak Skill Heatmap */}
                <Card className="p-5 lg:col-span-1 flex flex-col">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                      <ShieldAlert size={16} className="text-brand-yellow" />
                      Priority Remediation Matrix
                    </h3>
                  </div>
                  <p className="text-xs text-ink-faint mb-4">
                    Skills with largest gap vs 75% benchmark requiring bootcamp focus
                  </p>

                  <div className="space-y-3 my-auto">
                    {data.weak_skill_heatmap?.length === 0 && <EmptyState text="No skill gap data." />}
                    {data.weak_skill_heatmap?.map((s) => {
                      const isCritical = s.average_score < 50;
                      return (
                        <div key={s.skill} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-ink truncate max-w-[150px]">
                              {s.skill}
                            </span>
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                  isCritical
                                    ? "bg-danger/10 text-danger"
                                    : "bg-brand-yellow/10 text-brand-yellow"
                                }`}
                              >
                                {isCritical ? "High Priority" : "Moderate"}
                              </span>
                              <span className="font-bold tabular-nums text-ink text-xs">
                                {s.average_score}%
                              </span>
                            </div>
                          </div>
                          <div className="w-full h-2 rounded-full bg-surface-high overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                isCritical ? "bg-danger" : "bg-brand-yellow"
                              }`}
                              style={{ width: `${Math.max(s.average_score, 4)}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>

                {/* Top Performers Leaderboard Spotlight */}
                <Card className="p-5 lg:col-span-2 flex flex-col">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
                        <Award size={16} className="text-brand-maroon" />
                        Top Performer Spotlight & Role Matches
                      </h3>
                      <p className="text-xs text-ink-faint mt-0.5">
                        High-achieving candidates ready for immediate interview scheduling
                      </p>
                    </div>
                    <Link to="/students">
                      <Button variant="secondary" className="text-xs px-3 py-1.5 flex items-center gap-1">
                        <span>All Students</span>
                        <ChevronRight size={13} />
                      </Button>
                    </Link>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-surface-border text-ink-faint font-semibold uppercase tracking-wider">
                          <th className="pb-2">Candidate</th>
                          <th className="pb-2">Course / Batch</th>
                          <th className="pb-2 text-center">Score</th>
                          <th className="pb-2 text-center">Attendance</th>
                          <th className="pb-2">Best Role Match</th>
                          <th className="pb-2 text-right">Profile</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-border">
                        {data.leaderboard?.slice(0, 5).map((s, idx) => (
                          <tr key={s.id} className="hover:bg-surface-high/50 transition-colors">
                            <td className="py-2.5 font-semibold text-ink flex items-center gap-2">
                              <span className="w-5 h-5 rounded-full bg-brand-maroon/15 text-brand-maroon flex items-center justify-center font-bold text-[10px]">
                                {idx + 1}
                              </span>
                              <div>
                                <div>{s.name}</div>
                                <div className="text-[10px] text-ink-faint font-normal">
                                  {s.roll_number || "—"}
                                </div>
                              </div>
                            </td>
                            <td className="py-2.5 text-ink-muted">
                              <div>{s.course || "CCDP"}</div>
                              <div className="text-[10px] text-ink-faint">{s.batch || ""}</div>
                            </td>
                            <td className="py-2.5 text-center font-bold tabular-nums text-success">
                              {s.overall_score}/100
                            </td>
                            <td className="py-2.5 text-center tabular-nums text-ink-muted">
                              {s.attendance_pct}%
                            </td>
                            <td className="py-2.5">
                              <div className="font-medium text-ink truncate max-w-[160px]">
                                {s.best_role}
                              </div>
                              <Badge tone={FIT_TONE[s.fit_tier] || "neutral"} className="text-[9px] px-1.5 py-0">
                                {s.fit_tier}
                              </Badge>
                            </td>
                            <td className="py-2.5 text-right">
                              <Link
                                to={`/students/${s.id}`}
                                className="inline-flex items-center gap-1 text-brand-maroon hover:text-brand-pink font-semibold"
                              >
                                <span>View</span>
                                <ArrowUpRight size={12} />
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════════════
              TAB 2: KAUVERY HOSPITAL DEMAND & SUPPLY MATRIX
          ══════════════════════════════════════════════════════════════════════ */}
          {activeTab === "matrix" && (
            <div className="space-y-5">
              <Card className="p-5">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-5 pb-4 border-b border-surface-border">
                  <div>
                    <h3 className="font-display font-bold text-base text-ink flex items-center gap-2">
                      <Hospital size={18} className="text-brand-maroon" />
                      Kauvery Hospital Facility Placement Matrix
                    </h3>
                    <p className="text-xs text-ink-faint mt-0.5">
                      Cross-tab matching vacancies across 12 Kauvery facilities with eligible candidates in current scope
                    </p>
                  </div>
                  <Link to="/jobs">
                    <Button className="text-xs px-3.5 py-2 flex items-center gap-1.5">
                      <span>Manage Placement Roles</span>
                      <ChevronRight size={14} />
                    </Button>
                  </Link>
                </div>

                {data.kauvery_unit_matrix?.length === 0 ? (
                  <EmptyState text="No active placement roles found. Head to Job Roles to add requirements." />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-surface-border text-ink-faint font-semibold uppercase tracking-wider">
                          <th className="pb-3">Role Title & Department</th>
                          <th className="pb-3">Kauvery Facility / Unit</th>
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
            </div>
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
                    Search, sort, and inspect individual student score metrics in real-time
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <div className="relative min-w-[220px]">
                    <input
                      type="text"
                      value={gridSearch}
                      onChange={(e) => setGridSearch(e.target.value)}
                      placeholder="Search candidate, roll, role..."
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-1.5 text-xs text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                    />
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-surface-border text-ink-faint font-semibold uppercase tracking-wider">
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
                      <th className="pb-3">
                        <button
                          onClick={() => toggleSort("overall_score")}
                          className="flex items-center gap-1 hover:text-ink"
                        >
                          <span>Overall Score</span>
                          <ArrowUpDown size={11} />
                        </button>
                      </th>
                      <th className="pb-3">
                        <button
                          onClick={() => toggleSort("attendance_pct")}
                          className="flex items-center gap-1 hover:text-ink"
                        >
                          <span>Attendance</span>
                          <ArrowUpDown size={11} />
                        </button>
                      </th>
                      <th className="pb-3">Placement Status</th>
                      <th className="pb-3">Best Role & Fit</th>
                      <th className="pb-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {gridStudents.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-ink-faint">
                          No candidates found matching the current search query.
                        </td>
                      </tr>
                    ) : (
                      gridStudents.map((s) => (
                        <tr key={s.id} className="hover:bg-surface-high/50 transition-colors">
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
                          <td className="py-3 min-w-[130px]">
                            <div className="flex items-center justify-between text-xs font-bold tabular-nums text-ink mb-1">
                              <span>{s.overall_score}</span>
                              <span className="text-[10px] text-ink-faint font-normal">/ 100</span>
                            </div>
                            <div className="w-full h-1.5 rounded-full bg-surface-high overflow-hidden">
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
                          <td className="py-3 font-semibold tabular-nums text-ink-muted">
                            {s.attendance_pct}%
                          </td>
                          <td className="py-3">
                            <Badge tone={s.placement_ready ? "success" : "warning"}>
                              {s.placement_ready ? "Placement Ready" : "Needs Prep"}
                            </Badge>
                          </td>
                          <td className="py-3">
                            <div className="font-medium text-ink truncate max-w-[160px]">
                              {s.best_role}
                            </div>
                            <Badge
                              tone={FIT_TONE[s.fit_tier] || "neutral"}
                              className="text-[9px] px-1.5 py-0 mt-0.5"
                            >
                              {s.fit_tier}
                            </Badge>
                          </td>
                          <td className="py-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Link
                                to={`/students/${s.id}`}
                                className="p-1.5 rounded-lg bg-surface-high hover:bg-surface-container text-ink-muted hover:text-ink transition-colors"
                                title="View Profile"
                              >
                                <Eye size={14} />
                              </Link>
                              <a
                                href={`${api.defaults.baseURL}/api/reports/student/${s.id}/pdf`}
                                target="_blank"
                                rel="noreferrer"
                                className="p-1.5 rounded-lg bg-surface-high hover:bg-surface-container text-ink-muted hover:text-brand-maroon transition-colors"
                                title="Download PDF"
                              >
                                <Download size={14} />
                              </a>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* ── Recent Ingested Sheets / Batch History ─────────────────────── */}
          {data.recent_uploads?.length > 0 && (
            <Card className="p-5">
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-surface-border">
                <h3 className="font-display font-semibold text-xs text-ink uppercase tracking-wider flex items-center gap-2">
                  <FileSpreadsheet size={15} className="text-brand-pink" />
                  Recent Batch Ingestion History
                </h3>
                <Link to="/upload" className="text-xs text-brand-maroon hover:text-brand-pink font-semibold">
                  + Upload New Excel Batch
                </Link>
              </div>

              <div className="divide-y divide-surface-border">
                {data.recent_uploads.map((u, i) => (
                  <div key={i} className="flex items-center justify-between py-2.5 text-xs">
                    <div className="min-w-0 pr-3">
                      <div className="text-ink font-semibold truncate">{u.filename}</div>
                      <div className="text-[10px] text-ink-faint">
                        {new Date(u.created_at).toLocaleString()} · {u.student_count} records processed
                      </div>
                    </div>
                    <Badge tone={u.mode === "save" ? "success" : u.mode === "update" ? "brand" : "neutral"}>
                      {u.mode} mode
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}
    </Layout>
  );
}
