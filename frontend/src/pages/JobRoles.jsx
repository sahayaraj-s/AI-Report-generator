import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Briefcase, Code2, Database, Palette, Cloud, Shield, Headphones, Users2,
  TrendingUp, Plus, X, Trash2, Edit2, Check, Power, ChevronDown, ChevronUp,
  Users, Building2, Target, AlertCircle, Hospital, Filter, CheckCircle2,
} from "lucide-react";
import { Layout } from "../components/Layout";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { api } from "../lib/api";

const ROLE_ICONS = {
  "Patient Care Coordinator": Users2,
  "Front Office & Helpdesk Executive": Headphones,
  "Billing & Health Insurance Executive": TrendingUp,
  "Hospital Operations Trainee": Building2,
  "Healthcare IT & Systems Assistant": Database,
  "Medical Records / Quality Assistant": Shield,
  "Customer Experience Executive": Headphones,
  "Data & Analytics Trainee": Database,
  "General Management Trainee": Users2,
};

const DEMAND_TONE = { High: "success", Medium: "brand", Selective: "warning" };

const FIT_COLORS = {
  "Perfect Match": "text-success bg-success/10 border-success/20",
  "Medium Fit": "text-brand-purple bg-brand-purple/10 border-brand-purple/20",
  "Low Fit": "text-brand-yellow bg-brand-yellow/10 border-brand-yellow/20",
  "Not Eligible": "text-ink-faint bg-surface-high border-surface-border",
};

const DEFAULT_UNITS = [
  "Kauvery Hospital - Trichy (Tennur)",
  "Kauvery Hospital - Trichy (Cantonment)",
  "Kauvery Hospital - Trichy (Heartcity)",
  "Kauvery Hospital - Chennai (Alwarpet)",
  "Kauvery Hospital - Chennai (Vadapalani)",
  "Kauvery Hospital - Chennai (Radial Road)",
  "Kauvery Hospital - Salem",
  "Kauvery Hospital - Hosur",
  "Kauvery Hospital - Tirunelveli",
  "Kauvery Hospital - Bengaluru (Electronic City)",
  "Kauvery Hospital - Bengaluru (Marathahalli)",
  "Kauvery Hospital - Karaikudi",
  "Kauvery Corporate / Central Office",
  "External Partner Organisation",
];

const DEFAULT_DEPARTMENTS = [
  "Patient Care & Customer Relations",
  "Front Office, Admissions & Helpdesk",
  "Billing, Cashless & Health Insurance",
  "Hospital Administration & Operations",
  "IT, Systems & Healthcare Informatics",
  "Medical Records (MRD) & Quality Assurance",
  "Nursing & Clinical Operations Support",
  "Diagnostic Services & Lab Support",
  "Pharmacy Operations & Supply Chain",
  "HR, Training & Development",
  "Biomedical & Facility Management",
  "Corporate & Allied Services",
];

function SkillCriteriaRow({ crit, onRemove }) {
  return (
    <div className="flex items-center gap-2 bg-surface-container border border-surface-border rounded-xl px-3 py-2">
      <span className="text-sm text-ink flex-1 font-medium">{crit.skill}</span>
      <div className="flex items-center gap-1 text-xs text-ink-faint">
        <span className="font-semibold text-brand-maroon">{crit.min_score}</span>
        <span>/</span>
        <span>{crit.max_score}</span>
        <span className="ml-1 text-[10px] bg-brand-maroon/10 text-brand-maroon px-1.5 py-0.5 rounded-full">
          {Math.round((crit.min_score / crit.max_score) * 100)}%
        </span>
      </div>
      {onRemove && (
        <button onClick={onRemove} className="text-ink-faint hover:text-danger transition-colors ml-1">
          <X size={13} />
        </button>
      )}
    </div>
  );
}

function CandidatesDrawer({ role, onClose }) {
  const { data, isLoading } = useQuery({
    queryKey: ["role-candidates", role.id],
    queryFn: async () => (await api.get(`/api/jobs/roles/${role.id}/candidates`)).data,
    enabled: !!role.id,
  });

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="w-[500px] bg-surface-dim border-l border-surface-border flex flex-col h-full overflow-hidden shadow-2xl">
        <div className="px-5 py-4 border-b border-surface-border flex items-center justify-between">
          <div className="min-w-0 pr-3">
            <h3 className="font-display font-bold text-ink truncate">{role.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-brand-maroon font-medium truncate flex items-center gap-1">
                <Hospital size={12} /> {role.kauvery_unit || "Kauvery Hospital"}
              </span>
              <span className="text-xs text-ink-faint">· {data?.total_candidates || 0} candidates</span>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-surface-high text-ink-faint shrink-0">
            <X size={16} />
          </button>
        </div>

        {/* Tier summary */}
        {data && (
          <div className="px-5 py-3 border-b border-surface-border grid grid-cols-3 gap-3">
            {[
              { label: "Perfect Match", count: data.perfect_match, color: "text-success" },
              { label: "Medium Fit", count: data.medium_fit, color: "text-brand-purple" },
              { label: "Low Fit", count: data.low_fit, color: "text-brand-yellow" },
            ].map(t => (
              <div key={t.label} className="text-center">
                <div className={`text-2xl font-bold ${t.color}`}>{t.count}</div>
                <div className="text-[10px] text-ink-faint">{t.label}</div>
              </div>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          {isLoading && <p className="text-sm text-ink-muted text-center py-8">Loading matched candidates…</p>}
          {data?.candidates?.map((c) => (
            <div key={c.student_id} className="rounded-xl border border-surface-border bg-surface-container p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-full bg-brand-maroon flex items-center justify-center text-white text-xs font-bold">
                    {c.name.charAt(0)}
                  </div>
                  <div>
                    <div className="text-sm font-medium text-ink">{c.name}</div>
                    <div className="text-[10px] text-ink-faint">{c.batch || "CCDP"} · {c.course || "CCDP"}</div>
                  </div>
                </div>
                <div className={`text-[10px] font-semibold px-2 py-1 rounded-full border ${FIT_COLORS[c.fit_tier] || ""}`}>
                  {c.fit_tier}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 rounded-full bg-surface-high overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-brand-maroon to-brand-pink"
                    style={{ width: `${c.criteria_pct}%` }}
                  />
                </div>
                <span className="text-xs font-semibold text-ink w-10 text-right">{c.criteria_pct}%</span>
              </div>
              {c.skill_gaps?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {c.skill_gaps.slice(0, 3).map(g => (
                    <span key={g.skill} className="text-[10px] bg-brand-yellow/10 text-brand-yellow border border-brand-yellow/20 rounded px-1.5 py-0.5">
                      Gap: {g.skill} ({g.achieved}/{g.required.split("/")[1]})
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {data?.candidates?.length === 0 && (
            <div className="text-center py-10">
              <AlertCircle size={28} className="text-ink-faint mx-auto mb-2" />
              <p className="text-sm text-ink-faint">No candidates matched this role yet.</p>
              <p className="text-xs text-ink-faint mt-1">Upload student data and run analysis first.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const EMPTY_FORM = {
  name: "",
  kauvery_unit: "Kauvery Hospital - Trichy (Tennur)",
  department: "Patient Care & Customer Relations",
  demand_level: "High",
  openings: 2,
  is_active: true,
  company_name: "Kauvery Hospital",
};

const EMPTY_SKILL = { skill: "", min_score: "15", max_score: "25" };

export default function JobRoles() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingRole, setEditingRole] = useState(null); // null = create mode, role obj = edit mode
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [skillCriteria, setSkillCriteria] = useState([]);
  const [newSkill, setNewSkill] = useState(EMPTY_SKILL);
  const [formError, setFormError] = useState("");
  const [filterTab, setFilterTab] = useState("all");
  const [unitFilter, setUnitFilter] = useState("all");
  const [drawerRole, setDrawerRole] = useState(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["job-roles"],
    queryFn: async () => (await api.get("/api/jobs/roles")).data,
  });

  const createMutation = useMutation({
    mutationFn: async (payload) => (await api.post("/api/jobs/roles", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job-roles"] });
      closeForm();
    },
    onError: (err) => setFormError(err.response?.data?.detail || "Failed to create role."),
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, payload }) => (await api.put(`/api/jobs/roles/${id}`, payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job-roles"] });
      closeForm();
    },
    onError: (err) => setFormError(err.response?.data?.detail || "Failed to update role."),
  });

  const toggleMutation = useMutation({
    mutationFn: async (roleId) => (await api.patch(`/api/jobs/roles/${roleId}/toggle`)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["job-roles"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (roleId) => (await api.delete(`/api/jobs/roles/${roleId}`)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["job-roles"] }),
  });

  const closeForm = () => {
    setShowForm(false);
    setEditingRole(null);
    setFormData(EMPTY_FORM);
    setSkillCriteria([]);
    setFormError("");
    setNewSkill(EMPTY_SKILL);
  };

  const openCreateForm = () => {
    setEditingRole(null);
    setFormData(EMPTY_FORM);
    setSkillCriteria([]);
    setFormError("");
    setShowForm(true);
  };

  const openEditForm = (role) => {
    setEditingRole(role);
    setFormData({
      name: role.name,
      kauvery_unit: role.kauvery_unit || "Kauvery Hospital - Trichy (Tennur)",
      department: role.department || "Patient Care & Customer Relations",
      demand_level: role.demand_level || "High",
      openings: role.openings ?? 2,
      is_active: role.is_active !== false,
      company_name: role.company_name || "Kauvery Hospital",
    });
    setSkillCriteria(
      (role.skill_criteria || []).map(sc => ({
        skill: sc.skill,
        min_score: sc.min_score,
        max_score: sc.max_score,
      }))
    );
    setFormError("");
    setShowForm(true);
  };

  const addSkill = () => {
    if (!newSkill.skill.trim()) { setFormError("Skill name is required."); return; }
    if (!newSkill.min_score || !newSkill.max_score) { setFormError("Score and total score are required."); return; }
    const sc = { skill: newSkill.skill.trim(), min_score: parseFloat(newSkill.min_score), max_score: parseFloat(newSkill.max_score) };
    if (sc.min_score > sc.max_score) { setFormError("Required score cannot be greater than total score."); return; }
    setSkillCriteria(prev => [...prev, sc]);
    setNewSkill(EMPTY_SKILL);
    setFormError("");
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setFormError("");
    if (!formData.name.trim()) { setFormError("Role name is required."); return; }
    if (skillCriteria.length === 0) { setFormError("Add at least one required skill benchmark."); return; }
    const payload = {
      name: formData.name.trim(),
      kauvery_unit: formData.kauvery_unit,
      department: formData.department,
      demand_level: formData.demand_level,
      openings: Number(formData.openings) || 0,
      is_active: formData.is_active,
      company_name: formData.company_name.trim() || "Kauvery Hospital",
      skill_criteria: skillCriteria,
    };
    if (editingRole) {
      updateMutation.mutate({ id: editingRole.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const unitsList = data?.kauvery_units || DEFAULT_UNITS;
  const departmentsList = data?.departments || DEFAULT_DEPARTMENTS;

  const filteredRoles = data?.roles?.filter(r => {
    if (filterTab === "active" && !r.is_active) return false;
    if (filterTab === "inactive" && r.is_active) return false;
    if (unitFilter !== "all" && r.kauvery_unit !== unitFilter) return false;
    return true;
  }) || [];

  return (
    <Layout
      title="Kauvery Placement & Job Roles"
      subtitle="Define roles across Kauvery Hospital 12 units & partner organizations, and match CCDP candidates."
    >
      {isLoading && <p className="text-ink-muted text-sm">Loading roles…</p>}
      {error && <p className="text-danger text-sm">Couldn't load job roles — make sure the backend is running.</p>}

      {data && (
        <div className="space-y-6">
          {/* Summary row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: "Active Roles", value: data.active_roles, color: "text-success" },
              { label: "Kauvery Units", value: unitsList.length, color: "text-brand-maroon" },
              { label: "Total Openings", value: data.total_openings, color: "text-brand-pink" },
              { label: "Candidates Evaluated", value: data.total_students, color: "text-brand-purple" },
            ].map(s => (
              <Card key={s.label} className="p-5 flex flex-col gap-1">
                <span className={`text-2xl font-display font-semibold tabular-nums ${s.color}`}>{s.value}</span>
                <span className="text-sm text-ink-muted">{s.label}</span>
              </Card>
            ))}
          </div>

          {/* Filters & Actions Bar */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center flex-wrap gap-2">
              <div className="flex items-center bg-surface-high rounded-xl p-1 gap-1">
                {["all", "active", "inactive"].map(tab => (
                  <button
                    key={tab}
                    onClick={() => setFilterTab(tab)}
                    className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-colors ${
                      filterTab === tab ? "bg-surface-dim text-ink shadow-sm" : "text-ink-muted hover:text-ink"
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              {/* Unit Dropdown Filter */}
              <div className="flex items-center gap-1.5 bg-surface-container border border-surface-border rounded-xl px-3 py-1 text-xs">
                <Hospital size={13} className="text-brand-maroon" />
                <select
                  value={unitFilter}
                  onChange={(e) => setUnitFilter(e.target.value)}
                  className="bg-transparent text-ink text-xs focus:outline-none max-w-[220px] truncate"
                >
                  <option value="all">All Kauvery Units</option>
                  {unitsList.map(u => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </select>
              </div>
            </div>

            <Button onClick={openCreateForm}>
              <Plus size={15} /> Add Role
            </Button>
          </div>

          {/* Add Role Form Modal */}
          {showForm && (
            <Card className="p-6 border-brand-maroon/30 shadow-xl">
              <div className="flex items-center justify-between mb-5 pb-3 border-b border-surface-border">
                <div className="flex items-center gap-2.5">
                  <Hospital size={20} className="text-brand-maroon" />
                  <h3 className="font-display font-semibold text-ink">
                    {editingRole ? `Edit Role: ${editingRole.name}` : "Create Placement Role"}
                  </h3>
                </div>
                <button onClick={closeForm} className="p-1 rounded-lg hover:bg-surface-high text-ink-faint">
                  <X size={16} />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Role Name */}
                  <div>
                    <label className="text-xs text-ink-muted mb-1 block font-medium">1. Role Title *</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={e => setFormData({ ...formData, name: e.target.value })}
                      placeholder="e.g. Patient Care Coordinator"
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                    />
                  </div>

                  {/* Kauvery 12 Units */}
                  <div>
                    <label className="text-xs text-ink-muted mb-1 block font-medium">2. Kauvery Unit / Facility *</label>
                    <select
                      value={formData.kauvery_unit}
                      onChange={e => setFormData({ ...formData, kauvery_unit: e.target.value })}
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                    >
                      {unitsList.map(u => (
                        <option key={u} value={u}>{u}</option>
                      ))}
                    </select>
                  </div>

                  {/* Department */}
                  <div>
                    <label className="text-xs text-ink-muted mb-1 block font-medium">3. Department *</label>
                    <select
                      value={formData.department}
                      onChange={e => setFormData({ ...formData, department: e.target.value })}
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                    >
                      {departmentsList.map(d => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                  </div>

                  {/* Organization / Company */}
                  <div>
                    <label className="text-xs text-ink-muted mb-1 block font-medium">4. Organisation Name</label>
                    <input
                      type="text"
                      value={formData.company_name}
                      onChange={e => setFormData({ ...formData, company_name: e.target.value })}
                      placeholder="Kauvery Hospital"
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                    />
                  </div>

                  {/* Number of Openings */}
                  <div>
                    <label className="text-xs text-ink-muted mb-1 block font-medium">5. Open Positions / Vacancies</label>
                    <input
                      type="number"
                      value={formData.openings}
                      onChange={e => setFormData({ ...formData, openings: e.target.value })}
                      min={0}
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                    />
                  </div>

                  {/* Demand Level & Active Status */}
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-ink-muted mb-1 block font-medium">Demand Level</label>
                      <select
                        value={formData.demand_level}
                        onChange={e => setFormData({ ...formData, demand_level: e.target.value })}
                        className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                      >
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Selective">Selective</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-xs text-ink-muted mb-1 block font-medium">Status</label>
                      <button
                        type="button"
                        onClick={() => setFormData(f => ({ ...f, is_active: !f.is_active }))}
                        className={`w-full py-2 px-3 rounded-xl border text-xs font-semibold flex items-center justify-center gap-2 transition-colors ${
                          formData.is_active
                            ? "bg-success/10 border-success/30 text-success"
                            : "bg-surface-high border-surface-border text-ink-faint"
                        }`}
                      >
                        <Power size={13} />
                        {formData.is_active ? "Active" : "Inactive"}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Skill Criteria Builder */}
                <div className="pt-2 border-t border-surface-border">
                  <label className="text-xs text-ink-muted mb-2 block font-medium">
                    Required CCDP Skill Criteria & Benchmarks *
                  </label>

                  {/* Added Skills List */}
                  {skillCriteria.length > 0 && (
                    <div className="space-y-2 mb-3">
                      {skillCriteria.map((sc, i) => (
                        <SkillCriteriaRow key={i} crit={sc} onRemove={() => setSkillCriteria(p => p.filter((_, j) => j !== i))} />
                      ))}
                    </div>
                  )}

                  {/* Add Skill Row */}
                  <div className="flex gap-2 items-end">
                    <div className="flex-1">
                      <label className="text-[10px] text-ink-faint mb-1 block">CCDP Skill Name</label>
                      <input
                        type="text"
                        value={newSkill.skill}
                        onChange={e => setNewSkill(s => ({ ...s, skill: e.target.value }))}
                        placeholder="e.g. Communication Skills, MS Office & IT"
                        className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                      />
                    </div>
                    <div className="w-24">
                      <label className="text-[10px] text-ink-faint mb-1 block">Min Score</label>
                      <input
                        type="number"
                        value={newSkill.min_score}
                        onChange={e => setNewSkill(s => ({ ...s, min_score: e.target.value }))}
                        placeholder="15"
                        className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                      />
                    </div>
                    <div className="w-24">
                      <label className="text-[10px] text-ink-faint mb-1 block">Total Scale</label>
                      <input
                        type="number"
                        value={newSkill.max_score}
                        onChange={e => setNewSkill(s => ({ ...s, max_score: e.target.value }))}
                        placeholder="25"
                        className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                      />
                    </div>
                    <Button type="button" variant="secondary" onClick={addSkill} className="shrink-0">
                      <Plus size={14} /> Add Skill
                    </Button>
                  </div>
                </div>

                {formError && <p className="text-xs text-danger">{formError}</p>}
                <div className="flex gap-3 pt-2">
                  <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                    {(createMutation.isPending || updateMutation.isPending)
                      ? (editingRole ? "Updating Role…" : "Saving Role…")
                      : (editingRole ? "Update Placement Role" : "Save Placement Role")}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={closeForm}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </Card>
          )}

          {/* Role Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredRoles.map(role => {
              const Icon = ROLE_ICONS[role.name] || Briefcase;
              const tone = DEMAND_TONE[role.demand_level] || "neutral";
              const tier = role.tier_breakdown || {};

              return (
                <Card key={role.id || role.name} className={`p-5 flex flex-col gap-3.5 group transition-all ${!role.is_active ? "opacity-60" : ""}`}>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="h-10 w-10 rounded-xl bg-brand-maroon/10 text-brand-maroon flex items-center justify-center shrink-0">
                        <Icon size={20} />
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-display font-semibold text-sm text-ink truncate">{role.name}</h3>
                        <p className="text-[11px] text-brand-maroon font-medium truncate flex items-center gap-1 mt-0.5">
                          <Hospital size={11} /> {role.kauvery_unit || "Kauvery Hospital"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Badge tone={tone}>{role.demand_level}</Badge>
                      {role.id && (
                        <button
                          onClick={() => openEditForm(role)}
                          className="p-1 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-brand-maroon/10 text-ink-faint hover:text-brand-maroon transition-all"
                          title="Edit role"
                        >
                          <Edit2 size={13} />
                        </button>
                      )}
                      {role.id && (
                        <button
                          onClick={() => toggleMutation.mutate(role.id)}
                          className={`p-1 rounded-lg transition-colors ${role.is_active ? "text-success hover:bg-success/10" : "text-ink-faint hover:bg-surface-high"}`}
                          title={role.is_active ? "Deactivate" : "Activate"}
                        >
                          <Power size={13} />
                        </button>
                      )}
                      {role.id && (
                        <button
                          onClick={() => { if (window.confirm(`Delete role "${role.name}"?`)) deleteMutation.mutate(role.id); }}
                          className="p-1 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-danger/10 text-ink-faint hover:text-danger transition-all"
                          title="Delete role"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Department & Openings */}
                  <div className="flex items-center flex-wrap gap-2">
                    <span className="text-[11px] bg-surface-high border border-surface-border text-ink-muted rounded-full px-2.5 py-0.5 font-medium truncate max-w-[200px]">
                      {role.department || "Hospital Operations"}
                    </span>
                    {role.openings > 0 && (
                      <span className="text-xs bg-brand-maroon/10 text-brand-maroon border border-brand-maroon/20 rounded-full px-2 py-0.5 font-medium flex items-center gap-1">
                        <Target size={10} /> {role.openings} Openings
                      </span>
                    )}
                  </div>

                  {/* Skill Criteria */}
                  {role.skill_criteria?.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-[10px] text-ink-faint font-semibold uppercase tracking-wider">Required CCDP Competencies</p>
                      <div className="space-y-1">
                        {role.skill_criteria.slice(0, 3).map((sc, i) => (
                          <div key={i} className="flex justify-between items-center text-xs py-0.5 px-2 rounded-lg bg-surface-container">
                            <span className="text-ink truncate font-medium">{sc.skill}</span>
                            <span className="text-ink-faint text-[10px] shrink-0">{sc.min_score}/{sc.max_score} ({Math.round((sc.min_score/sc.max_score)*100)}%)</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Fit Tier Breakdown */}
                  {(tier["Perfect Match"] > 0 || tier["Medium Fit"] > 0 || tier["Low Fit"] > 0) && (
                    <div className="flex items-center gap-2 text-xs pt-1">
                      {tier["Perfect Match"] > 0 && <span className="text-success font-medium">✓ {tier["Perfect Match"]} Perfect</span>}
                      {tier["Medium Fit"] > 0 && <span className="text-brand-purple font-medium">~ {tier["Medium Fit"]} Medium</span>}
                      {tier["Low Fit"] > 0 && <span className="text-brand-yellow font-medium">△ {tier["Low Fit"]} Low</span>}
                    </div>
                  )}

                  {/* Footer */}
                  <div className="mt-auto pt-3 border-t border-surface-border flex items-center justify-between text-xs">
                    <span className="text-ink-faint">Matched Candidates</span>
                    <div className="flex items-center gap-2">
                      <span className="text-ink font-semibold tabular-nums">{role.matched_students}</span>
                      {role.id && (
                        <button
                          onClick={() => setDrawerRole(role)}
                          className="text-brand-maroon hover:text-brand-purple font-medium flex items-center gap-1 transition-colors px-2 py-1 rounded-lg bg-brand-maroon/10 hover:bg-brand-maroon/20"
                        >
                          <Users size={12} /> Candidates
                        </button>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Candidates Drawer */}
      {drawerRole && <CandidatesDrawer role={drawerRole} onClose={() => setDrawerRole(null)} />}
    </Layout>
  );
}
