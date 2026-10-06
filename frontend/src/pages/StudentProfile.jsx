import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Download, Sparkles, Trash2, AlertTriangle } from "lucide-react";
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from "recharts";
import { Layout } from "../components/Layout";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { api } from "../lib/api";
import { useTheme } from "../context/ThemeContext";

/* ─── Delete Confirmation Modal ──────────────────────────────────────────── */
function DeleteProfileModal({ isOpen, studentName, onConfirm, onCancel, isDeleting, errorMessage }) {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-surface-elevated border border-danger/30 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-danger/10 text-danger flex items-center justify-center shrink-0">
            <Trash2 size={20} />
          </div>
          <div>
            <h3 className="font-display font-semibold text-ink text-base">Delete Student</h3>
            <p className="text-xs text-ink-muted">Permanent removal from system</p>
          </div>
        </div>

        <p className="text-sm text-ink-muted leading-relaxed">
          Are you sure you want to permanently delete <strong className="text-ink font-semibold">{studentName}</strong>?
          All associated skill assessments and AI placement reports will be wiped.
        </p>

        {errorMessage && (
          <div className="p-3 rounded-xl bg-danger/10 border border-danger/30 text-xs text-danger flex items-center gap-2">
            <AlertTriangle size={14} className="shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <div className="flex items-center justify-end gap-2.5 pt-2">
          <Button variant="secondary" onClick={onCancel} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            className="bg-danger hover:bg-danger/90 text-white font-medium"
            onClick={onConfirm}
            disabled={isDeleting}
          >
            {isDeleting ? "Deleting…" : "Yes, Delete Student"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function StudentProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { theme } = useTheme();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const gridStroke = theme === "dark" ? "#34323A" : "#E2E8F0";
  const axisStroke = theme === "dark" ? "#A6A1AC" : "#475569";
  const radiusStroke = theme === "dark" ? "#716C7A" : "#94A3B8";

  const { data, isLoading, error } = useQuery({
    queryKey: ["student", id],
    queryFn: async () => (await api.get(`/api/students/${id}`)).data,
  });

  const handleDeleteStudent = async () => {
    setIsDeleting(true);
    setDeleteError("");
    try {
      await api.delete(`/api/students/${id}`);
      await queryClient.invalidateQueries({ queryKey: ["students"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      await queryClient.invalidateQueries({ queryKey: ["batches"] });
      navigate("/students");
    } catch (err) {
      console.error("Delete failed:", err);
      setDeleteError(err.response?.data?.detail || err.message || "Failed to delete student.");
      setIsDeleting(false);
    }
  };

  return (
    <Layout title="Student Profile" subtitle="Full performance breakdown and AI-generated guidance.">
      <Link to="/students" className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-ink mb-4">
        <ArrowLeft size={15} />
        Back to Students
      </Link>

      {isLoading && <p className="text-ink-muted text-sm">Loading…</p>}
      {error && <p className="text-danger text-sm">Couldn't load this student.</p>}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <Card className="p-6 lg:col-span-1 h-fit">
            <div className="flex flex-col items-center text-center">
              <div className="h-20 w-20 rounded-full bg-brand-maroon flex items-center justify-center text-white text-2xl font-semibold mb-3">
                {data.student.name.charAt(0)}
              </div>
              <h2 className="font-display font-semibold text-lg text-ink">{data.student.name}</h2>
              <p className="text-xs text-ink-faint">{data.student.roll_number || "—"}</p>
              <Badge tone={data.student.placement_ready ? "success" : "warning"} className="mt-3">
                {data.student.placement_ready ? "Placement Ready" : "Needs Training"}
              </Badge>
            </div>

            <dl className="mt-6 space-y-3 text-sm">
              <Row label="Course" value={data.student.course || "—"} />
              <Row label="Batch" value={data.student.batch || "—"} />
              <Row label="Email" value={data.student.email || "—"} />
              <Row label="Attendance" value={`${data.student.attendance_pct}%`} />
              <Row label="Overall Score" value={`${data.student.overall_score}/100`} />
            </dl>

            <a
              href={`${api.defaults.baseURL || ""}/api/reports/student/${data.student.id}/pdf`}
              target="_blank"
              rel="noreferrer"
              className="mt-6 block"
            >
              <Button className="w-full">
                <Download size={15} />
                Download PDF Report
              </Button>
            </a>

            <button
              type="button"
              onClick={() => setShowDeleteModal(true)}
              className="mt-3 w-full py-2.5 px-4 rounded-xl border border-danger/30 text-danger hover:bg-danger/10 text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              <Trash2 size={14} />
              Delete Student
            </button>
          </Card>

          <div className="lg:col-span-2 space-y-5">
            <Card className="p-5">
              <h3 className="font-display font-semibold text-sm text-ink mb-4">Skill Radar</h3>
              {data.skill_scores.length === 0 ? (
                <p className="text-xs text-ink-faint py-8 text-center">No skill data yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <RadarChart data={data.skill_scores.map((s) => ({ skill: s.skill, score: s.score }))}>
                    <PolarGrid stroke={gridStroke} />
                    <PolarAngleAxis dataKey="skill" stroke={axisStroke} fontSize={11} />
                    <PolarRadiusAxis domain={[0, 100]} stroke={radiusStroke} fontSize={9} />
                    <Radar dataKey="score" stroke="#DE4F73" fill="#DE4F73" fillOpacity={0.3} />
                  </RadarChart>
                </ResponsiveContainer>
              )}
            </Card>

            {data.latest_analysis ? (
              <>
                <Card className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles size={16} className="text-brand-pink" />
                    <h3 className="font-display font-semibold text-sm text-ink">AI Summary</h3>
                    <Badge tone={data.latest_analysis.ai_source === "gemini" ? "brand" : "neutral"}>
                      {data.latest_analysis.ai_source === "gemini" ? "Gemini" : "Local AI"}
                    </Badge>
                  </div>
                  <p className="text-sm text-ink-muted leading-relaxed">{data.latest_analysis.ai_summary}</p>
                </Card>

                <div className="grid grid-cols-2 gap-5">
                  <Card className="p-5">
                    <h3 className="font-display font-semibold text-sm text-success mb-3">Strengths</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {data.latest_analysis.strengths.map((s) => (
                        <Badge key={s} tone="success">
                          {s}
                        </Badge>
                      ))}
                      {data.latest_analysis.strengths.length === 0 && (
                        <span className="text-xs text-ink-faint">None yet</span>
                      )}
                    </div>
                  </Card>
                  <Card className="p-5">
                    <h3 className="font-display font-semibold text-sm text-warning mb-3">Weaknesses</h3>
                    <div className="flex flex-wrap gap-1.5">
                      {data.latest_analysis.weaknesses.map((w) => (
                        <Badge key={w} tone="warning">
                          {w}
                        </Badge>
                      ))}
                      {data.latest_analysis.weaknesses.length === 0 && (
                        <span className="text-xs text-ink-faint">None yet</span>
                      )}
                    </div>
                  </Card>
                </div>

                <Card className="p-5">
                  <h3 className="font-display font-semibold text-sm text-ink mb-3">Recommended Job Roles (Kauvery & Corporate)</h3>
                  <div className="space-y-3">
                    {data.latest_analysis.recommended_roles.map((r) => (
                      <div key={r.role} className="p-2.5 rounded-xl bg-surface-container border border-surface-border">
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="min-w-0 pr-2">
                            <span className="text-sm font-semibold text-ink truncate block">{r.role}</span>
                            <span className="text-[11px] text-brand-maroon font-medium truncate block">
                              {r.kauvery_unit || r.company_name || "Kauvery Hospital"}
                            </span>
                          </div>
                          {r.fit_tier && (
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-brand-maroon/10 text-brand-maroon shrink-0">
                              {r.fit_tier}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 rounded-full bg-surface-high overflow-hidden">
                            <div className="h-full rounded-full bg-gradient-to-r from-brand-maroon to-brand-pink" style={{ width: `${r.confidence}%` }} />
                          </div>
                          <span className="text-xs text-ink-faint font-semibold w-9 text-right">{r.confidence}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>

                <div className="grid grid-cols-2 gap-5">
                  <Card className="p-5">
                    <h3 className="font-display font-semibold text-sm text-ink mb-2">Salary Prediction</h3>
                    <p className="text-2xl font-display font-semibold text-brand-pink">
                      {data.latest_analysis.salary_range}
                    </p>
                  </Card>
                  <Card className="p-5">
                    <h3 className="font-display font-semibold text-sm text-ink mb-2">Interview Readiness</h3>
                    <p className="text-sm text-ink-muted">{data.latest_analysis.interview_readiness}</p>
                  </Card>
                </div>

                <Card className="p-5">
                  <h3 className="font-display font-semibold text-sm text-ink mb-3">Learning Roadmap</h3>
                  <div className="text-sm text-ink-muted whitespace-pre-line leading-relaxed">
                    {data.latest_analysis.learning_roadmap}
                  </div>
                </Card>

                <Card className="p-5">
                  <h3 className="font-display font-semibold text-sm text-ink mb-3">30-Day Plan</h3>
                  <div className="text-sm text-ink-muted whitespace-pre-line leading-relaxed">
                    {data.latest_analysis.thirty_day_plan}
                  </div>
                </Card>

                <Card className="p-5">
                  <h3 className="font-display font-semibold text-sm text-ink mb-3">Recommended Certifications</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {data.latest_analysis.recommended_certifications.map((c) => (
                      <Badge key={c} tone="brand">
                        {c}
                      </Badge>
                    ))}
                  </div>
                </Card>
              </>
            ) : (
              <Card className="p-8 text-center text-sm text-ink-faint">
                No AI analysis yet for this student.
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      <DeleteProfileModal
        isOpen={showDeleteModal}
        studentName={data?.student?.name}
        onConfirm={handleDeleteStudent}
        onCancel={() => { setShowDeleteModal(false); setDeleteError(""); }}
        isDeleting={isDeleting}
        errorMessage={deleteError}
      />
    </Layout>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-ink-faint">{label}</dt>
      <dd className="text-ink font-medium truncate max-w-[60%] text-right">{value}</dd>
    </div>
  );
}
