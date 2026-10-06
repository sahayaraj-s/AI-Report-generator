import { useState, useMemo, useEffect } from "react";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import {
  Search, Eye, Trash2, Download, ArrowUpDown, FileText,
  FileSpreadsheet, X, CheckSquare, Square, MinusSquare,
  Filter, AlertTriangle, CheckCircle2,
} from "lucide-react";
import { Layout } from "../components/Layout";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { api } from "../lib/api";

const PAGE_SIZE = 15;

const FIT_TONE = {
  "Perfect Match": "success",
  "Medium Fit": "brand",
  "Low Fit": "warning",
  "Not Eligible": "neutral",
};

/* ─── Delete Confirmation Modal ──────────────────────────────────────────── */
function DeleteConfirmModal({ target, onConfirm, onCancel, isDeleting }) {
  if (!target) return null;
  const isBulk = Array.isArray(target);
  const count = isBulk ? target.length : 1;
  const name = isBulk ? `${count} selected students` : target.name;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-surface-elevated border border-danger/30 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-danger/10 text-danger flex items-center justify-center shrink-0">
            <Trash2 size={20} />
          </div>
          <div>
            <h3 className="font-display font-semibold text-ink text-base">
              {isBulk ? "Delete Selected Students" : "Delete Student"}
            </h3>
            <p className="text-xs text-ink-muted">Permanent removal from system</p>
          </div>
        </div>

        <p className="text-sm text-ink-muted leading-relaxed">
          Are you sure you want to permanently delete <strong className="text-ink font-semibold">{name}</strong>?
          All associated skill assessments and AI placement reports will be wiped.
        </p>

        <div className="flex items-center justify-end gap-2.5 pt-2">
          <Button variant="secondary" onClick={onCancel} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            className="bg-danger hover:bg-danger/90 text-white font-medium"
            onClick={onConfirm}
            disabled={isDeleting}
          >
            {isDeleting ? "Deleting…" : "Yes, Delete"}
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ─── Export / Report Modal ──────────────────────────────────────────────── */
function ReportModal({ onClose, selectedBatch, batches, selectedIds }) {
  const [batch, setBatch] = useState(selectedBatch || "");
  const batchParam = batch ? `?batch=${encodeURIComponent(batch)}` : "";

  const reports = [
    {
      label: "All Students CSV",
      desc: selectedIds?.length
        ? `Export ${selectedIds.length} selected students to CSV`
        : "Export all students with scores and roles to CSV",
      icon: FileSpreadsheet,
      href: `${api.defaults.baseURL || ""}/api/reports/batch/csv${batchParam}`,
    },
    {
      label: "Batch Summary PDF",
      desc: "Full batch report with student table and statistics",
      icon: FileText,
      href: `${api.defaults.baseURL || ""}/api/reports/batch/pdf${batchParam}`,
    },
    {
      label: "Role Match Report PDF",
      desc: "Role-matching matrix — who fits what and at what %",
      icon: FileText,
      href: `${api.defaults.baseURL || ""}/api/reports/match/pdf${batchParam}`,
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-surface-dim border border-surface-border rounded-2xl shadow-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-bold text-ink flex items-center gap-2">
            <Download size={16} className="text-brand-maroon" />
            Export Reports
          </h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-surface-high text-ink-faint">
            <X size={16} />
          </button>
        </div>

        {selectedIds?.length > 0 && (
          <div className="mb-4 px-3 py-2 rounded-xl bg-brand-maroon/10 border border-brand-maroon/20 text-xs text-brand-maroon font-medium">
            {selectedIds.length} student{selectedIds.length !== 1 ? "s" : ""} selected
          </div>
        )}

        <div className="mb-4">
          <label className="text-xs text-ink-muted mb-1.5 block font-medium">Filter by Batch</label>
          <select
            value={batch}
            onChange={e => setBatch(e.target.value)}
            className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
          >
            <option value="">All Batches</option>
            {batches.map(b => <option key={b} value={b}>{b}</option>)}
          </select>
        </div>

        <div className="space-y-3">
          {reports.map(r => {
            const Icon = r.icon;
            return (
              <a
                key={r.label}
                href={r.href}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-3 p-3 rounded-xl border border-surface-border hover:bg-surface-high hover:border-brand-maroon/30 transition-all group"
              >
                <div className="h-9 w-9 rounded-xl bg-brand-maroon/10 flex items-center justify-center shrink-0 group-hover:bg-brand-maroon/20 transition-colors">
                  <Icon size={16} className="text-brand-maroon" />
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-medium text-ink">{r.label}</div>
                  <div className="text-xs text-ink-faint">{r.desc}</div>
                </div>
                <Download size={14} className="ml-auto text-ink-faint group-hover:text-brand-maroon transition-colors shrink-0" />
              </a>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ─── Bulk Action Bar ────────────────────────────────────────────────────── */
function BulkBar({ count, total, onSelectAll, onClear, onExport, onDelete }) {
  return (
    <div className="flex flex-wrap items-center gap-2 px-4 py-2.5 bg-brand-maroon/10 border border-brand-maroon/20 rounded-xl text-sm">
      <CheckSquare size={15} className="text-brand-maroon shrink-0" />
      <span className="text-ink font-medium">
        <span className="text-brand-maroon font-bold">{count}</span> selected
        {count < total && (
          <button
            onClick={onSelectAll}
            className="ml-2 text-xs text-brand-maroon underline underline-offset-2 hover:text-brand-pink"
          >
            Select all {total}
          </button>
        )}
      </span>
      <button
        onClick={onClear}
        className="ml-auto text-xs text-ink-muted hover:text-ink flex items-center gap-1"
      >
        <X size={13} /> Clear
      </button>
      <button
        onClick={onExport}
        className="px-3 py-1.5 text-xs rounded-lg border border-surface-border bg-surface-dim hover:bg-surface-high text-ink flex items-center gap-1.5 transition-colors"
      >
        <Download size={13} /> Export
      </button>
      <button
        onClick={onDelete}
        className="px-3 py-1.5 text-xs rounded-lg bg-danger text-white hover:bg-red-700 flex items-center gap-1.5 transition-colors"
      >
        <Trash2 size={13} /> Delete
      </button>
    </div>
  );
}

/* ─── Sort Header ────────────────────────────────────────────────────────── */
function Th({ label, col, sortBy, sortDir, onSort }) {
  const active = sortBy === col;
  return (
    <th className="px-4 py-3 font-medium">
      <button onClick={() => onSort(col)} className={`flex items-center gap-1 hover:text-ink ${active ? "text-ink" : ""}`}>
        {label}
        <ArrowUpDown size={12} className={active ? "text-brand-pink" : "text-ink-faint"} />
      </button>
    </th>
  );
}

/* ─── Main Component ─────────────────────────────────────────────────────── */
export default function StudentsDirectory() {
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [readyFilter, setReadyFilter] = useState("all");
  const [batchFilter, setBatchFilter] = useState("");
  const [sortBy, setSortBy] = useState("name");
  const [sortDir, setSortDir] = useState("asc");
  const [page, setPage] = useState(1);
  const [showReportModal, setShowReportModal] = useState(false);
  const [selected, setSelected] = useState(new Set());
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [notification, setNotification] = useState(null);
  const queryClient = useQueryClient();

  // Sync URL search param changes (e.g. from Topbar)
  useEffect(() => {
    const q = searchParams.get("search") || "";
    setSearch(q);
    setPage(1);
  }, [searchParams]);

  const { data, isLoading } = useQuery({
    queryKey: ["students", { search, readyFilter, batchFilter, sortBy, sortDir, page }],
    queryFn: async () => {
      const params = { search, sort_by: sortBy, sort_dir: sortDir, page, page_size: PAGE_SIZE };
      if (readyFilter !== "all") params.placement_ready = readyFilter === "ready";
      if (batchFilter) params.batch = batchFilter;
      return (await api.get("/api/students", { params })).data;
    },
    placeholderData: keepPreviousData,
  });

  const { data: batchesData } = useQuery({
    queryKey: ["batches"],
    queryFn: async () => (await api.get("/api/students/batches")).data,
  });

  const batchList = batchesData?.batches?.map(b => b.name) || [];
  const currentItems = data?.items || [];
  const totalItems = data?.total || 0;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));

  /* ── Selection ─────────────────────────────────────────────────────── */
  const currentIds = useMemo(() => currentItems.map(s => s.id), [currentItems]);
  const allCurrentSelected = currentIds.length > 0 && currentIds.every(id => selected.has(id));
  const someCurrentSelected = currentIds.some(id => selected.has(id));

  const toggleAll = () => {
    const next = new Set(selected);
    if (allCurrentSelected) {
      currentIds.forEach(id => next.delete(id));
    } else {
      currentIds.forEach(id => next.add(id));
    }
    setSelected(next);
  };

  const toggleOne = (id) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  };

  const selectAllPages = () => {
    const next = new Set(selected);
    currentIds.forEach(id => next.add(id));
    setSelected(next);
  };

  const clearSelection = () => setSelected(new Set());

  /* ── Sort ──────────────────────────────────────────────────────────── */
  const toggleSort = (col) => {
    if (sortBy === col) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortBy(col); setSortDir("asc"); }
  };

  /* ── Delete Handlers ─────────────────────────────────────────────────── */
  const handleDelete = (id, name) => {
    setDeleteTarget({ id, name });
  };

  const handleBulkDelete = () => {
    if (selected.size === 0) return;
    setDeleteTarget(Array.from(selected));
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      if (Array.isArray(deleteTarget)) {
        const res = await api.post("/api/students/bulk-delete", { ids: deleteTarget });
        setNotification({
          type: "success",
          message: `Successfully deleted ${res.data?.deleted ?? deleteTarget.length} students.`
        });
        setSelected(new Set());
      } else {
        await api.delete(`/api/students/${deleteTarget.id}`);
        setNotification({
          type: "success",
          message: `Student "${deleteTarget.name}" has been deleted.`
        });
        const next = new Set(selected);
        next.delete(deleteTarget.id);
        setSelected(next);
      }
      setDeleteTarget(null);
      await queryClient.invalidateQueries({ queryKey: ["students"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      await queryClient.invalidateQueries({ queryKey: ["batches"] });
      setTimeout(() => setNotification(null), 4000);
    } catch (err) {
      console.error("Delete failed:", err);
      setNotification({
        type: "error",
        message: err.response?.data?.detail || err.message || "Failed to delete student. Please try again."
      });
      setTimeout(() => setNotification(null), 6000);
    } finally {
      setIsDeleting(false);
    }
  };

  const selectedCount = selected.size;

  return (
    <Layout title="Students" subtitle="Search, filter, select, and manage every CCDP student record.">
      {/* Notification feedback */}
      {notification && (
        <div className={`mb-4 px-4 py-3 rounded-xl border text-sm flex items-center justify-between transition-all ${
          notification.type === "success"
            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
            : "bg-danger/10 border-danger/30 text-danger"
        }`}>
          <div className="flex items-center gap-2">
            {notification.type === "success" ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-xs hover:underline ml-4">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Filters bar */}
      <Card className="p-4 mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
            <input
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(1); setSelected(new Set()); }}
              placeholder="Search by name, roll number, or email…"
              className="w-full bg-surface-container border border-surface-border rounded-xl pl-9 pr-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
            />
          </div>

          {/* Batch filter pills */}
          {batchList.length > 0 ? (
            <div className="flex items-center gap-1.5 flex-wrap">
              <Filter size={13} className="text-ink-faint shrink-0" />
              {["", ...batchList].map(b => (
                <button
                  key={b || "all"}
                  onClick={() => { setBatchFilter(b); setPage(1); setSelected(new Set()); }}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
                    batchFilter === b
                      ? "bg-brand-maroon text-white"
                      : "bg-surface-high border border-surface-border text-ink-muted hover:text-ink"
                  }`}
                >
                  {b || "All Batches"}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs text-ink-faint">
              <Filter size={13} className="shrink-0" />
              <span>No batches yet — <Link to="/upload" className="text-brand-maroon hover:text-brand-pink font-medium">upload a file</Link> to create batches</span>
            </div>
          )}

          <select
            value={readyFilter}
            onChange={e => { setReadyFilter(e.target.value); setPage(1); setSelected(new Set()); }}
            className="bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
          >
            <option value="all">All Students</option>
            <option value="ready">Placement Ready</option>
            <option value="not_ready">Needs Training</option>
          </select>

          <Button variant="secondary" onClick={() => setShowReportModal(true)} className="flex items-center gap-2 ml-auto">
            <Download size={14} /> Export Report
          </Button>
        </div>

        {selectedCount > 0 && (
          <div className="mt-3">
            <BulkBar
              count={selectedCount}
              total={totalItems}
              onSelectAll={selectAllPages}
              onClear={clearSelection}
              onExport={() => setShowReportModal(true)}
              onDelete={handleBulkDelete}
            />
          </div>
        )}
      </Card>

      {/* Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border text-left text-ink-muted text-xs uppercase tracking-wide">
                <th className="px-4 py-3 w-10">
                  <button
                    onClick={toggleAll}
                    className="text-ink-faint hover:text-ink transition-colors"
                    title={allCurrentSelected ? "Deselect page" : "Select page"}
                  >
                    {allCurrentSelected
                      ? <CheckSquare size={16} className="text-brand-maroon" />
                      : someCurrentSelected
                        ? <MinusSquare size={16} className="text-brand-maroon/60" />
                        : <Square size={16} />}
                  </button>
                </th>
                <Th label="Name" col="name" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                <th className="px-4 py-3 font-medium">Course / Batch</th>
                <Th label="Attendance" col="attendance_pct" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                <Th label="Score" col="overall_score" sortBy={sortBy} sortDir={sortDir} onSort={toggleSort} />
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Best Role / Fit</th>
                <th className="px-4 py-3 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={8} className="px-4 py-10 text-center text-ink-faint text-sm">Loading students…</td></tr>
              )}
              {data && currentItems.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-10 text-center text-ink-faint text-sm">No students match these filters.</td></tr>
              )}
              {currentItems.map(s => {
                const isSelected = selected.has(s.id);
                return (
                  <tr
                    key={s.id}
                    className={`border-b border-surface-border last:border-0 transition-colors cursor-pointer ${
                      isSelected ? "bg-brand-maroon/5" : "hover:bg-surface-high/40"
                    }`}
                  >
                    <td className="px-4 py-3 w-10" onClick={() => toggleOne(s.id)}>
                      {isSelected
                        ? <CheckSquare size={16} className="text-brand-maroon" />
                        : <Square size={16} className="text-ink-faint hover:text-brand-maroon transition-colors" />}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-ink font-medium">{s.name}</div>
                      <div className="text-xs text-ink-faint">{s.roll_number || "—"}</div>
                    </td>
                    <td className="px-4 py-3 text-ink-muted">
                      {s.course || "—"}
                      <div className="text-xs text-ink-faint">{s.batch || ""}</div>
                    </td>
                    <td className="px-4 py-3 text-ink-muted tabular-nums">{s.attendance_pct}%</td>
                    <td className="px-4 py-3 text-ink font-medium tabular-nums">{s.overall_score}</td>
                    <td className="px-4 py-3">
                      <Badge tone={s.placement_ready ? "success" : "warning"}>
                        {s.placement_ready ? "Placement Ready" : "Needs Training"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      {s.best_role ? (
                        <div>
                          <div className="text-xs text-ink truncate max-w-[140px]">{s.best_role}</div>
                          {s.fit_tier && (
                            <Badge tone={FIT_TONE[s.fit_tier] || "neutral"} className="mt-0.5 text-[10px]">
                              {s.fit_tier}
                            </Badge>
                          )}
                        </div>
                      ) : <span className="text-xs text-ink-faint">—</span>}
                    </td>
                    <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1.5">
                        <Link
                          to={`/students/${s.id}`}
                          className="h-8 w-8 rounded-lg flex items-center justify-center text-ink-muted hover:text-ink hover:bg-surface-high"
                          title="View profile"
                          onClick={e => e.stopPropagation()}
                        >
                          <Eye size={15} />
                        </Link>
                        <a
                          href={`${api.defaults.baseURL || ""}/api/reports/student/${s.id}/pdf`}
                          target="_blank"
                          rel="noreferrer"
                          className="h-8 w-8 rounded-lg flex items-center justify-center text-ink-muted hover:text-ink hover:bg-surface-high"
                          title="Download PDF report"
                          onClick={e => e.stopPropagation()}
                        >
                          <Download size={15} />
                        </a>
                        <button
                          type="button"
                          onClick={e => {
                            e.stopPropagation();
                            e.preventDefault();
                            handleDelete(s.id, s.name);
                          }}
                          className="h-8 w-8 rounded-lg flex items-center justify-center text-ink-muted hover:text-danger hover:bg-danger/10 transition-colors"
                          title="Delete student"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {data && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-surface-border text-xs text-ink-faint">
            <span>
              {totalItems} student{totalItems !== 1 ? "s" : ""}
              {selectedCount > 0 && (
                <span className="ml-2 text-brand-maroon font-medium">· {selectedCount} selected</span>
              )}
            </span>
            <div className="flex items-center gap-2">
              <Button variant="secondary" className="px-3 py-1.5" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                Previous
              </Button>
              <span>Page {page} of {totalPages}</span>
              <Button variant="secondary" className="px-3 py-1.5" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>

      {showReportModal && (
        <ReportModal
          onClose={() => setShowReportModal(false)}
          selectedBatch={batchFilter}
          batches={batchList}
          selectedIds={Array.from(selected)}
        />
      )}

      {/* Delete confirmation modal */}
      <DeleteConfirmModal
        target={deleteTarget}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
        isDeleting={isDeleting}
      />
    </Layout>
  );
}
