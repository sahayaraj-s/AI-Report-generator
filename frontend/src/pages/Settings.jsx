import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Settings as SettingsIcon,
  Building2,
  GraduationCap,
  Sparkles,
  Sliders,
  Database,
  Check,
  AlertCircle,
  RefreshCw,
  Trash2,
  Hospital,
  ShieldCheck,
  Zap,
  CheckCircle2,
  Calendar,
  Plus,
  Pencil,
  X,
  Save,
} from "lucide-react";
import { Layout } from "../components/Layout";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { api } from "../lib/api";

/* ─── Editable List Component ────────────────────────────────────────────── */
function EditableList({ items, onSave, accentColor = "text-brand-maroon", label }) {
  const [editing, setEditing] = useState(false);
  const [list, setList] = useState(items || []);
  const [newItem, setNewItem] = useState("");
  const [editIdx, setEditIdx] = useState(null);
  const [editVal, setEditVal] = useState("");

  useEffect(() => {
    setList(items || []);
  }, [items]);

  const startEdit = (idx) => {
    setEditIdx(idx);
    setEditVal(list[idx]);
  };

  const commitEdit = () => {
    if (editVal.trim()) {
      const next = [...list];
      next[editIdx] = editVal.trim();
      setList(next);
    }
    setEditIdx(null);
    setEditVal("");
  };

  const deleteItem = (idx) => {
    setList(list.filter((_, i) => i !== idx));
  };

  const addItem = () => {
    const val = newItem.trim();
    if (val && !list.includes(val)) {
      setList([...list, val]);
      setNewItem("");
    }
  };

  const handleSave = () => {
    onSave(list);
    setEditing(false);
  };

  if (!editing) {
    return (
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-ink-faint font-semibold uppercase tracking-wider">{label}</span>
          <button
            onClick={() => setEditing(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-high border border-surface-border text-xs font-semibold text-ink-muted hover:text-ink hover:border-brand-maroon/40 transition-all"
          >
            <Pencil size={12} />
            Edit
          </button>
        </div>
        <div className="space-y-2">
          {list.map((item, idx) => (
            <div key={idx} className="flex items-center gap-2.5 p-2.5 rounded-xl border border-surface-border bg-surface-container">
              <span className={`h-5 w-5 rounded-md text-[10px] font-bold flex items-center justify-center shrink-0 bg-brand-maroon/10 ${accentColor}`}>
                {idx + 1}
              </span>
              <span className="text-sm text-ink truncate">{item}</span>
            </div>
          ))}
          {list.length === 0 && (
            <p className="text-xs text-ink-faint italic text-center py-4">No items. Click Edit to add some.</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-ink-faint font-semibold uppercase tracking-wider">{label}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setEditing(false); setList(items || []); setEditIdx(null); }}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink border border-surface-border bg-surface-container transition-colors"
          >
            <X size={12} /> Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-brand-maroon hover:bg-brand-maroon/90 transition-colors"
          >
            <Save size={12} /> Save Changes
          </button>
        </div>
      </div>

      <div className="space-y-2 mb-3">
        {list.map((item, idx) => (
          <div key={idx} className="flex items-center gap-2">
            {editIdx === idx ? (
              <input
                autoFocus
                value={editVal}
                onChange={(e) => setEditVal(e.target.value)}
                onBlur={commitEdit}
                onKeyDown={(e) => { if (e.key === "Enter") commitEdit(); if (e.key === "Escape") setEditIdx(null); }}
                className="flex-1 bg-surface-container border border-brand-maroon/50 rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
              />
            ) : (
              <div className="flex-1 flex items-center gap-2.5 p-2.5 rounded-xl border border-surface-border bg-surface-container group">
                <span className={`h-5 w-5 rounded-md text-[10px] font-bold flex items-center justify-center shrink-0 bg-brand-maroon/10 ${accentColor}`}>
                  {idx + 1}
                </span>
                <span className="text-sm text-ink flex-1 truncate">{item}</span>
              </div>
            )}
            <button
              onClick={() => startEdit(idx)}
              className="h-8 w-8 rounded-lg flex items-center justify-center text-ink-faint hover:text-brand-maroon hover:bg-brand-maroon/10 transition-colors"
              title="Edit"
            >
              <Pencil size={13} />
            </button>
            <button
              onClick={() => deleteItem(idx)}
              className="h-8 w-8 rounded-lg flex items-center justify-center text-ink-faint hover:text-danger hover:bg-danger/10 transition-colors"
              title="Delete"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
      </div>

      {/* Add new */}
      <div className="flex items-center gap-2 pt-2 border-t border-surface-border">
        <input
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") addItem(); }}
          placeholder={`Add new ${label.toLowerCase().replace(/s$/, "")}…`}
          className="flex-1 bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
        />
        <button
          onClick={addItem}
          disabled={!newItem.trim()}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-brand-maroon text-white text-xs font-semibold disabled:opacity-40 hover:bg-brand-maroon/90 transition-colors"
        >
          <Plus size={13} /> Add
        </button>
      </div>
    </div>
  );
}

/* ─── Main Settings Component ────────────────────────────────────────────── */
export default function Settings() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("general");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [cleanMessage, setCleanMessage] = useState("");
  const [confirmClear, setConfirmClear] = useState(false);

  // General form states
  const [instituteName, setInstituteName] = useState("Skill Bay Academy");
  const [tagline, setTagline] = useState("Enabling Life Skills");
  const [parentOrg, setParentOrg] = useState("Kauvery Hospital");
  const [programName, setProgramName] = useState("Career & Competency Development Program (CCDP)");
  const [programDuration, setProgramDuration] = useState("50 Days");

  // AI weights
  const [skillWeight, setSkillWeight] = useState(75);
  const [attWeight, setAttWeight] = useState(25);
  const [weightError, setWeightError] = useState("");
  const [weightSaved, setWeightSaved] = useState(false);

  const { data: settingsData, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-settings"],
    queryFn: async () => (await api.get("/api/admin/settings")).data,
    retry: 2,
    staleTime: 30000,
  });

  useEffect(() => {
    if (settingsData) {
      setInstituteName(settingsData.institute_name || "Skill Bay Academy");
      setTagline(settingsData.tagline || "Enabling Life Skills");
      setParentOrg(settingsData.parent_org || "Kauvery Hospital");
      setProgramName(settingsData.program_name || "Career & Competency Development Program (CCDP)");
      setProgramDuration(settingsData.program_duration || "50 Days");
      setSkillWeight(settingsData.skill_weight_pct ?? 75);
      setAttWeight(settingsData.attendance_weight_pct ?? 25);
    }
  }, [settingsData]);

  const updateMutation = useMutation({
    mutationFn: async (payload) => (await api.post("/api/admin/settings", payload)).data,
    onSuccess: () => {
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3500);
      queryClient.invalidateQueries({ queryKey: ["admin-settings"] });
    },
  });

  const cleanSkillsMutation = useMutation({
    mutationFn: async () => (await api.post("/api/admin/clean-legacy-skills")).data,
    onSuccess: (res) => {
      setCleanMessage(res.message);
      queryClient.invalidateQueries();
      setTimeout(() => setCleanMessage(""), 5000);
    },
  });

  const seedRolesMutation = useMutation({
    mutationFn: async () => (await api.post("/api/admin/seed-kauvery-roles")).data,
    onSuccess: (res) => {
      setCleanMessage(res.message);
      queryClient.invalidateQueries({ queryKey: ["job-roles"] });
      setTimeout(() => setCleanMessage(""), 5000);
    },
  });

  const clearDataMutation = useMutation({
    mutationFn: async () => (await api.post("/api/admin/clear-data")).data,
    onSuccess: () => {
      setConfirmClear(false);
      setCleanMessage("All student records, batches, and uploads cleared.");
      queryClient.invalidateQueries();
      setTimeout(() => setCleanMessage(""), 5000);
    },
  });

  const handleSaveGeneral = (e) => {
    e.preventDefault();
    updateMutation.mutate({
      institute_name: instituteName,
      tagline,
      parent_org: parentOrg,
      program_name: programName,
      program_duration: programDuration,
    });
  };

  const handleSaveWeights = () => {
    const sw = parseFloat(skillWeight);
    const aw = parseFloat(attWeight);
    if (isNaN(sw) || isNaN(aw) || sw < 0 || sw > 100 || aw < 0 || aw > 100) {
      setWeightError("Each weight must be between 0 and 100.");
      return;
    }
    setWeightError("");
    updateMutation.mutate(
      { skill_weight_pct: sw, attendance_weight_pct: aw },
      {
        onSuccess: () => {
          setWeightSaved(true);
          setTimeout(() => setWeightSaved(false), 3000);
        },
      }
    );
  };

  const handleSkillWeightChange = (val) => {
    const sw = Math.max(0, Math.min(100, parseFloat(val) || 0));
    setSkillWeight(sw);
    setWeightError("");
  };

  const handleAttWeightChange = (val) => {
    const aw = Math.max(0, Math.min(100, parseFloat(val) || 0));
    setAttWeight(aw);
    setWeightError("");
  };

  const handleSaveUnits = (units) => {
    updateMutation.mutate({ kauvery_units: units });
  };

  const handleSaveDepts = (depts) => {
    updateMutation.mutate({ departments: depts });
  };

  const TABS = [
    { id: "general", label: "Academy & Program", icon: GraduationCap },
    { id: "kauvery", label: "Kauvery 12 Units", icon: Hospital },
    { id: "ai", label: "AI & Evaluation", icon: Sparkles },
    { id: "data", label: "Data & Maintenance", icon: Database },
  ];

  return (
    <Layout
      title="Settings & Configuration"
      subtitle="Manage Skill Bay Academy parameters, Kauvery Hospital placement units, and system maintenance."
    >
      <div className="space-y-6">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-surface-border pb-3 overflow-x-auto">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${
                activeTab === id
                  ? "bg-brand-maroon text-white shadow-md shadow-brand-maroon/20"
                  : "bg-surface-container text-ink-muted hover:text-ink hover:bg-surface-high"
              }`}
            >
              <Icon size={16} />
              <span>{label}</span>
            </button>
          ))}
        </div>

        {/* Error / loading banner */}
        {isLoading && (
          <div className="p-4 rounded-xl bg-surface-container border border-surface-border text-ink-faint text-sm flex items-center gap-2.5">
            <RefreshCw size={16} className="animate-spin" />
            <span>Loading settings…</span>
          </div>
        )}
        {isError && (
          <div className="p-4 rounded-xl bg-danger/10 border border-danger/30 text-danger text-sm flex items-center justify-between gap-2.5">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} />
              <span>Could not reach backend — make sure the server is running on port 8000.</span>
            </div>
            <button
              onClick={() => refetch()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-danger text-white text-xs font-semibold hover:bg-danger/90 transition-colors shrink-0"
            >
              <RefreshCw size={12} /> Retry
            </button>
          </div>
        )}
        {saveSuccess && (
          <div className="p-4 rounded-xl bg-success/10 border border-success/30 text-success text-sm flex items-center gap-2.5">
            <CheckCircle2 size={18} />
            <span>Settings saved successfully!</span>
          </div>
        )}
        {cleanMessage && (
          <div className="p-4 rounded-xl bg-brand-maroon/10 border border-brand-maroon/30 text-brand-maroon text-sm flex items-center gap-2.5">
            <CheckCircle2 size={18} />
            <span>{cleanMessage}</span>
          </div>
        )}

        {/* ── Tab 1: General & CCDP Program ───────────────────────────────── */}
        {activeTab === "general" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="p-6 lg:col-span-2 space-y-5">
              <div className="flex items-center gap-3 pb-3 border-b border-surface-border">
                <div className="p-2.5 rounded-xl bg-brand-maroon/10 text-brand-maroon">
                  <GraduationCap size={20} />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-ink">Institute & CCDP Course Profile</h3>
                  <p className="text-xs text-ink-faint">Core identity and career program configuration</p>
                </div>
              </div>

              <form onSubmit={handleSaveGeneral} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-ink-muted mb-1 block font-medium">Academy Name</label>
                    <input
                      type="text"
                      value={instituteName}
                      onChange={(e) => setInstituteName(e.target.value)}
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-ink-muted mb-1 block font-medium">Parent Health System</label>
                    <input
                      type="text"
                      value={parentOrg}
                      onChange={(e) => setParentOrg(e.target.value)}
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-ink-muted mb-1 block font-medium">Flagship Course / Program</label>
                    <input
                      type="text"
                      value={programName}
                      onChange={(e) => setProgramName(e.target.value)}
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-ink-muted mb-1 block font-medium">Program Duration</label>
                    <input
                      type="text"
                      value={programDuration}
                      onChange={(e) => setProgramDuration(e.target.value)}
                      className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-ink-muted mb-1 block font-medium">Tagline / Mission</label>
                  <input
                    type="text"
                    value={tagline}
                    onChange={(e) => setTagline(e.target.value)}
                    className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                  />
                </div>

                <div className="pt-3">
                  <Button type="submit" disabled={updateMutation.isPending}>
                    {updateMutation.isPending ? "Saving…" : "Save Program Settings"}
                  </Button>
                </div>
              </form>
            </Card>

            <Card className="p-6 space-y-4 h-fit">
              <div className="flex items-center gap-2 text-brand-maroon font-semibold text-sm">
                <Calendar size={18} />
                <span>CCDP 50-Day Batch Cycle</span>
              </div>
              <p className="text-xs text-ink-muted leading-relaxed">
                The <strong>Career & Competency Development Program (CCDP)</strong> is structured as a 50-day intensive cycle.
              </p>
              <div className="space-y-2 pt-2 border-t border-surface-border text-xs text-ink-faint">
                <div className="flex justify-between py-1 border-b border-surface-border">
                  <span>Batch Naming Scheme</span>
                  <span className="font-semibold text-ink">CCDP 1, CCDP 2, CCDP 3…</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surface-border">
                  <span>Primary Evaluation</span>
                  <span className="font-semibold text-ink">Skills ({skillWeight}%) + Attendance ({attWeight}%)</span>
                </div>
                <div className="flex justify-between py-1">
                  <span>Placement Priority</span>
                  <span className="font-semibold text-success">Kauvery Hospital (1st Pref)</span>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* ── Tab 2: Kauvery Units & Departments ───────────────────────────── */}
        {activeTab === "kauvery" && (
          <div className="space-y-5">
            <Card className="p-6">
              <div className="flex items-center justify-between mb-5 pb-3 border-b border-surface-border">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-brand-maroon/10 text-brand-maroon">
                    <Hospital size={22} />
                  </div>
                  <div>
                    <h3 className="font-display font-semibold text-ink">Kauvery Hospital Units Directory</h3>
                    <p className="text-xs text-ink-faint">
                      Manage active hospital units — add, rename, or remove placement centers
                    </p>
                  </div>
                </div>
                <Badge tone="success">Editable</Badge>
              </div>

              {isLoading ? (
                <p className="text-sm text-ink-faint text-center py-6">Loading units…</p>
              ) : (
                <EditableList
                  items={settingsData?.kauvery_units || []}
                  onSave={handleSaveUnits}
                  label="Hospital Units"
                  accentColor="text-brand-maroon"
                />
              )}
            </Card>

            <Card className="p-6">
              <div className="flex items-center gap-3 mb-5 pb-3 border-b border-surface-border">
                <div className="p-2.5 rounded-xl bg-brand-purple/10 text-brand-purple">
                  <Building2 size={20} />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-ink">Placement Operational Departments</h3>
                  <p className="text-xs text-ink-faint">Manage placement departments for job role matching</p>
                </div>
              </div>

              {isLoading ? (
                <p className="text-sm text-ink-faint text-center py-6">Loading departments…</p>
              ) : (
                <EditableList
                  items={settingsData?.departments || []}
                  onSave={handleSaveDepts}
                  label="Departments"
                  accentColor="text-brand-purple"
                />
              )}
            </Card>
          </div>
        )}

        {/* ── Tab 3: AI & Evaluation ────────────────────────────────────────── */}
        {activeTab === "ai" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="p-6 lg:col-span-2 space-y-6">
              <div className="flex items-center gap-3 pb-3 border-b border-surface-border">
                <div className="p-2.5 rounded-xl bg-brand-purple/10 text-brand-purple">
                  <Sparkles size={20} />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-ink">AI Assistant & Scoring Engine</h3>
                  <p className="text-xs text-ink-faint">Gemini AI model and placement readiness weighting</p>
                </div>
              </div>

              <div className="space-y-4 text-sm">
                <div>
                  <label className="text-xs text-ink-muted mb-1 block font-medium">Active Gemini Model</label>
                  <input
                    type="text"
                    value={settingsData?.gemini_model || "gemini-1.5-flash"}
                    disabled
                    className="w-full bg-surface-high border border-surface-border rounded-xl px-3 py-2 text-ink text-sm cursor-not-allowed"
                  />
                  <span className="text-[11px] text-ink-faint mt-1 block">
                    Fast, low-latency reasoning for student profile analysis & SkillBay AI chat.
                  </span>
                </div>

                <div>
                  <label className="text-xs text-ink-muted mb-1 block font-medium">Gemini API Status</label>
                  <div className="flex items-center gap-2">
                    <Badge tone={settingsData?.gemini_api_key_configured ? "success" : "neutral"}>
                      {settingsData?.gemini_api_key_configured ? "API Key Active" : "Local AI Fallback Mode"}
                    </Badge>
                    <span className="text-xs text-ink-faint">
                      {settingsData?.gemini_api_key_configured
                        ? "Live neural generation enabled."
                        : "Deterministic template engine active (zero external dependencies)."}
                    </span>
                  </div>
                </div>
              </div>

              {/* Editable Scoring Weights */}
              <div className="pt-4 border-t border-surface-border space-y-4">
                <div className="flex items-center gap-2 mb-1">
                  <Sliders size={16} className="text-brand-maroon" />
                  <h4 className="font-semibold text-sm text-ink">Scoring Weight Configuration</h4>
                </div>
                <p className="text-xs text-ink-faint">
                  Adjust how skill scores and attendance independently contribute to the overall CCDP score.
                  Each weight is configurable from 0 to 100 — they are independent of each other.
                </p>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-ink-muted mb-1.5 block font-medium">
                      Skill Score Weight (%)
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        min={0}
                        max={100}
                        step={1}
                        value={skillWeight}
                        onChange={(e) => handleSkillWeightChange(e.target.value)}
                        className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2.5 text-lg font-bold text-brand-maroon focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint text-sm">%</span>
                    </div>
                    <span className="text-[11px] text-ink-faint mt-1 block">Communication, IT, Soft Skills, Aptitude</span>
                  </div>
                  <div>
                    <label className="text-xs text-ink-muted mb-1.5 block font-medium">
                      Attendance Weight (%)
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        min={0}
                        max={100}
                        step={1}
                        value={attWeight}
                        onChange={(e) => handleAttWeightChange(e.target.value)}
                        className="w-full bg-surface-container border border-surface-border rounded-xl px-3 py-2.5 text-lg font-bold text-brand-purple focus:outline-none focus:ring-2 focus:ring-brand-maroon/40"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-faint text-sm">%</span>
                    </div>
                    <span className="text-[11px] text-ink-faint mt-1 block">50-day course engagement metric</span>
                  </div>
                </div>

                {/* Visual weight bars — independent */}
                <div className="space-y-2">
                  <p className="text-xs text-ink-faint font-medium">Weight Indicators (each 0–100, independent)</p>
                  <div className="space-y-1.5">
                    <div>
                      <div className="flex items-center justify-between text-[11px] text-ink-faint mb-1">
                        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-brand-maroon inline-block" /> Skills</span>
                        <span className="font-semibold text-brand-maroon">{skillWeight}%</span>
                      </div>
                      <div className="w-full h-2.5 rounded-full overflow-hidden bg-surface-high">
                        <div
                          className="h-full bg-brand-maroon transition-all duration-300 rounded-full"
                          style={{ width: `${Math.min(100, Math.max(0, skillWeight))}%` }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-[11px] text-ink-faint mb-1">
                        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-brand-purple inline-block" /> Attendance</span>
                        <span className="font-semibold text-brand-purple">{attWeight}%</span>
                      </div>
                      <div className="w-full h-2.5 rounded-full overflow-hidden bg-surface-high">
                        <div
                          className="h-full bg-brand-purple transition-all duration-300 rounded-full"
                          style={{ width: `${Math.min(100, Math.max(0, attWeight))}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {weightError && (
                  <div className="flex items-center gap-2 text-danger text-xs p-3 rounded-xl bg-danger/10 border border-danger/20">
                    <AlertCircle size={14} />
                    {weightError}
                  </div>
                )}

                {weightSaved && (
                  <div className="flex items-center gap-2 text-success text-xs p-3 rounded-xl bg-success/10 border border-success/20">
                    <CheckCircle2 size={14} />
                    Scoring weights saved! New uploads will use these weights.
                  </div>
                )}

                <Button
                  onClick={handleSaveWeights}
                  disabled={updateMutation.isPending || skillWeight < 0 || skillWeight > 100 || attWeight < 0 || attWeight > 100}
                  className="w-full"
                >
                  <Zap size={14} className="mr-1.5" />
                  {updateMutation.isPending ? "Saving…" : "Save Scoring Weights"}
                </Button>
              </div>
            </Card>

            <Card className="p-6 space-y-4 h-fit">
              <div className="flex items-center gap-2 text-brand-purple font-semibold text-sm">
                <ShieldCheck size={18} />
                <span>Evaluation Safeguards</span>
              </div>
              <p className="text-xs text-ink-muted leading-relaxed">
                The scoring engine automatically isolates personal identifiers (phone numbers, ages, registration IDs)
                and normalizes all skill inputs onto an objective <strong>0–100 scale</strong>.
              </p>
              <div className="pt-3 border-t border-surface-border space-y-2 text-xs text-ink-faint">
                <div className="flex justify-between py-1 border-b border-surface-border/60">
                  <span>Skill Weight (independent)</span>
                  <span className="font-bold text-brand-maroon">{skillWeight}%</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surface-border/60">
                  <span>Attendance Weight (independent)</span>
                  <span className="font-bold text-brand-purple">{attWeight}%</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surface-border/60">
                  <span>Weight Mode</span>
                  <span className="font-bold text-success">Independent (0–100 each)</span>
                </div>
                <div className="flex justify-between py-1">
                  <span>Readiness Threshold</span>
                  <span className="font-bold text-ink">≥ 55%</span>
                </div>
              </div>
            </Card>

          </div>
        )}

        {/* ── Tab 4: Data & Maintenance ─────────────────────────────────────── */}
        {activeTab === "data" && (
          <div className="space-y-6">
            <Card className="p-6 space-y-5">
              <div className="flex items-center gap-3 pb-3 border-b border-surface-border">
                <div className="p-2.5 rounded-xl bg-brand-pink/10 text-brand-pink">
                  <Database size={20} />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-ink">Database Health & Hygiene</h3>
                  <p className="text-xs text-ink-faint">
                    Clean corrupted columns, seed Kauvery roles, and manage student records
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Clean Legacy Skills */}
                <div className="p-4 rounded-xl border border-surface-border bg-surface-container space-y-3">
                  <div className="flex items-center gap-2 font-medium text-ink text-sm">
                    <RefreshCw size={16} className="text-brand-pink" />
                    <span>Clean Non-Skill Columns</span>
                  </div>
                  <p className="text-xs text-ink-muted">
                    Purges any misclassified columns (Parents No., Personal No., Contact No., Age) from previous
                    uploads and recalculates clean CCDP student profiles.
                  </p>
                  <Button
                    variant="secondary"
                    className="w-full text-xs"
                    onClick={() => cleanSkillsMutation.mutate()}
                    disabled={cleanSkillsMutation.isPending}
                  >
                    {cleanSkillsMutation.isPending ? "Sanitizing…" : "Run Data Hygiene Cleanup"}
                  </Button>
                </div>

                {/* Seed Kauvery Hospital Roles */}
                <div className="p-4 rounded-xl border border-surface-border bg-surface-container space-y-3">
                  <div className="flex items-center gap-2 font-medium text-ink text-sm">
                    <Hospital size={16} className="text-brand-maroon" />
                    <span>Seed Kauvery Placement Roles</span>
                  </div>
                  <p className="text-xs text-ink-muted">
                    Populates standard Kauvery Hospital roles (Patient Care Coordinator, Front Office, Billing Executive,
                    IT Support) across the 12 units.
                  </p>
                  <Button
                    variant="secondary"
                    className="w-full text-xs"
                    onClick={() => seedRolesMutation.mutate()}
                    disabled={seedRolesMutation.isPending}
                  >
                    {seedRolesMutation.isPending ? "Seeding…" : "Seed Kauvery Hospital Roles"}
                  </Button>
                </div>
              </div>
            </Card>

            {/* Danger Zone */}
            <Card className="p-6 border-danger/30 bg-danger/5 space-y-4">
              <div className="flex items-center gap-2 text-danger font-semibold text-sm">
                <Trash2 size={18} />
                <span>Danger Zone: Reset Student Data</span>
              </div>
              <p className="text-xs text-ink-muted">
                Wipes all uploaded student rows, CCDP batch records, and analysis results to start completely fresh.
                This action cannot be undone.
              </p>

              {!confirmClear ? (
                <button
                  onClick={() => setConfirmClear(true)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-danger border border-danger/40 hover:bg-danger hover:text-white transition-colors"
                >
                  Clear All Student Records
                </button>
              ) : (
                <div className="flex items-center gap-3 p-3 rounded-xl bg-danger/10 border border-danger/30">
                  <span className="text-xs text-danger font-medium">Are you sure? All student records will be deleted.</span>
                  <button
                    onClick={() => clearDataMutation.mutate()}
                    disabled={clearDataMutation.isPending}
                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-danger text-white hover:bg-danger/90"
                  >
                    {clearDataMutation.isPending ? "Wiping…" : "Yes, Delete Everything"}
                  </button>
                  <button
                    onClick={() => setConfirmClear(false)}
                    className="px-3 py-1.5 rounded-lg text-xs text-ink-muted hover:text-ink"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </Layout>
  );
}
