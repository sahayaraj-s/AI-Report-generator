import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles, Send, Loader2, Plus, Trash2, Copy, Check, Database,
  MessageSquare, BookOpen, Zap, Users, Briefcase, Paperclip, X,
  Image as ImageIcon, FileText, ChevronDown, Cpu, Settings2
} from "lucide-react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";

const PROMPT_ICONS = {
  batch_audit: BookOpen,
  top_candidates: Users,
  skill_gap: Zap,
  role_match: Briefcase,
  interview_prep: MessageSquare,
  batch_compare: Database,
  low_performers: Users,
  openings_match: Briefcase,
};

const MODELS = [
  { id: "gemini-1.5-flash", label: "Flash", desc: "Fast · Low latency" },
  { id: "gemini-1.5-pro", label: "Pro", desc: "High quality · Detailed" },
  { id: "gemini-2.0-flash", label: "Flash 2.0", desc: "Latest · Best speed" },
];

function MarkdownContent({ text }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1.5 text-sm leading-relaxed">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1" />;
        const bold = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        const code = bold.replace(/`(.*?)`/g, '<code class="bg-surface-high px-1 rounded text-brand-pink text-xs">$1</code>');
        if (line.startsWith("### ")) {
          return <h3 key={i} className="font-bold text-ink mt-2" dangerouslySetInnerHTML={{ __html: code.slice(4) }} />;
        }
        if (line.startsWith("## ")) {
          return <h2 key={i} className="font-bold text-ink text-base mt-3" dangerouslySetInnerHTML={{ __html: code.slice(3) }} />;
        }
        if (line.startsWith("# ")) {
          return <h1 key={i} className="font-bold text-ink text-lg mt-3" dangerouslySetInnerHTML={{ __html: code.slice(2) }} />;
        }
        if (line.startsWith("- ") || line.startsWith("* ")) {
          return (
            <div key={i} className="flex gap-2">
              <span className="text-brand-pink mt-1 shrink-0">•</span>
              <span dangerouslySetInnerHTML={{ __html: code.slice(2) }} />
            </div>
          );
        }
        if (/^\d+\.\s/.test(line)) {
          const num = line.match(/^(\d+)\./)[1];
          return (
            <div key={i} className="flex gap-2">
              <span className="text-brand-maroon font-semibold w-5 shrink-0 text-xs mt-0.5">{num}.</span>
              <span dangerouslySetInnerHTML={{ __html: code.replace(/^\d+\.\s/, "") }} />
            </div>
          );
        }
        return <p key={i} dangerouslySetInnerHTML={{ __html: code }} />;
      })}
    </div>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="p-1 rounded-lg hover:bg-surface-high text-ink-faint hover:text-ink transition-colors"
      title="Copy"
    >
      {copied ? <Check size={13} className="text-success" /> : <Copy size={13} />}
    </button>
  );
}

function AttachChip({ file, onRemove }) {
  const isImage = file.type?.startsWith("image/");
  return (
    <div className="inline-flex items-center gap-1.5 bg-brand-maroon/10 border border-brand-maroon/30 rounded-lg px-2.5 py-1.5 text-xs text-brand-maroon font-medium">
      {isImage ? <ImageIcon size={12} className="shrink-0" /> : <FileText size={12} className="shrink-0" />}
      <span className="truncate max-w-[200px]">{file.name}</span>
      <button onClick={onRemove} className="shrink-0 hover:text-danger transition-colors ml-0.5">
        <X size={11} />
      </button>
    </div>
  );
}

function ModelSelector({ selected, onChange }) {
  const [open, setOpen] = useState(false);
  const curr = MODELS.find(m => m.id === selected) || MODELS[0];
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-surface-high border border-surface-border text-xs font-medium text-ink hover:border-brand-maroon/40 transition-all"
      >
        <Cpu size={12} className="text-brand-maroon" />
        <span>{curr.label}</span>
        <ChevronDown size={11} className={`text-ink-faint transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div className="absolute top-full mt-1 right-0 z-50 w-52 bg-surface-dim border border-surface-border rounded-xl shadow-xl overflow-hidden">
          {MODELS.map(m => (
            <button
              key={m.id}
              onClick={() => { onChange(m.id); setOpen(false); }}
              className={`w-full text-left px-3 py-2.5 text-xs flex items-start gap-2 transition-colors ${
                selected === m.id ? "bg-brand-maroon/10 text-ink" : "hover:bg-surface-high text-ink-muted"
              }`}
            >
              <Cpu size={12} className={`mt-0.5 shrink-0 ${selected === m.id ? "text-brand-maroon" : "text-ink-faint"}`} />
              <div>
                <div className="font-semibold">{m.label}</div>
                <div className="text-ink-faint text-[10px]">{m.desc}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SkillBayAI() {
  const queryClient = useQueryClient();
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [selectedModel, setSelectedModel] = useState("gemini-1.5-flash");
  const [showInfo, setShowInfo] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  const { data: sessionsData } = useQuery({
    queryKey: ["ai-sessions"],
    queryFn: async () => (await api.get("/api/ai/sessions")).data,
    refetchInterval: 30000,
  });

  const { data: templatesData } = useQuery({
    queryKey: ["ai-templates"],
    queryFn: async () => (await api.get("/api/ai/templates")).data,
  });

  const { data: settingsData } = useQuery({
    queryKey: ["admin-settings"],
    queryFn: async () => (await api.get("/api/admin/settings")).data,
    staleTime: 60000,
  });

  const deleteMutation = useMutation({
    mutationFn: async (id) => (await api.delete(`/api/ai/sessions/${id}`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-sessions"] });
      if (currentSessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  const loadSession = async (sessionId) => {
    try {
      const res = await api.get(`/api/ai/sessions/${sessionId}`);
      setCurrentSessionId(sessionId);
      setMessages(res.data.messages.map(m => ({ role: m.role, content: m.content })));
    } catch {
      setMessages([]);
    }
  };

  const sendMessage = async (query) => {
    let q = (query || input).trim();
    if (!q && !attachedFile) return;
    if (loading) return;

    // Append file context
    if (attachedFile) {
      q = q
        ? `${q}\n\n[Attached: ${attachedFile.name}]`
        : `[Attached file: ${attachedFile.name}] Please analyze or reference this attachment.`;
    }

    setInput("");
    setAttachedFile(null);

    const userMsg = { role: "user", content: q };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await api.post("/api/ai/sessions", {
        query: q,
        session_id: currentSessionId,
        model: selectedModel,
      });
      setCurrentSessionId(res.data.session_id);
      setMessages(prev => [...prev, { role: "assistant", content: res.data.response }]);
      queryClient.invalidateQueries({ queryKey: ["ai-sessions"] });
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, couldn't connect to the AI service." }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const newChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setInput("");
    setAttachedFile(null);
    inputRef.current?.focus();
  };

  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (f) setAttachedFile(f);
    e.target.value = "";
  };

  const isWelcome = messages.length === 0;
  const apiActive = settingsData?.gemini_api_key_configured;

  return (
    <div className="flex h-screen bg-surface overflow-hidden">
      {/* ── Sidebar ─────────────────────────────────────── */}
      <div className="w-64 shrink-0 border-r border-surface-border bg-surface-dim flex flex-col">
        {/* Logo */}
        <div className="px-4 py-4 border-b border-surface-border">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-brand-maroon to-brand-purple flex items-center justify-center">
              <Sparkles size={16} className="text-white" />
            </div>
            <div>
              <div className="font-display font-bold text-sm text-ink">SkillBay AI</div>
              <div className="text-[10px] text-ink-faint">Placement Intelligence</div>
            </div>
          </div>
        </div>

        {/* New Chat */}
        <div className="px-3 pt-3 pb-2">
          <button
            onClick={newChat}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl bg-brand-maroon text-white text-sm font-medium hover:bg-brand-purple transition-colors"
          >
            <Plus size={16} />
            New Chat
          </button>
        </div>

        {/* DB Status + Model Info */}
        <div className="px-3 pb-2 space-y-1.5">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success/10 border border-success/20">
            <Database size={11} className="text-success" />
            <span className="text-[11px] text-success font-medium">Connected to SkillBay DB</span>
          </div>

          {/* Gemini Info Card */}
          <button
            onClick={() => setShowInfo(o => !o)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-brand-maroon/8 border border-brand-maroon/20 hover:bg-brand-maroon/15 transition-colors"
          >
            <div className="flex items-center gap-1.5">
              <Cpu size={11} className="text-brand-maroon" />
              <span className="text-[11px] text-brand-maroon font-semibold">Gemini AI</span>
            </div>
            <div className={`w-1.5 h-1.5 rounded-full ${apiActive ? "bg-success" : "bg-brand-yellow"}`} />
          </button>

          {showInfo && (
            <div className="mx-0 p-3 rounded-xl bg-surface-container border border-surface-border text-[11px] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-ink-faint">API Status</span>
                <span className={`font-semibold ${apiActive ? "text-success" : "text-brand-yellow"}`}>
                  {apiActive ? "Active" : "Local Fallback"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ink-faint">Model</span>
                <span className="font-semibold text-ink">{settingsData?.gemini_model || selectedModel}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ink-faint">Mode</span>
                <span className="font-semibold text-ink">Chat + Analytics</span>
              </div>
              {!apiActive && (
                <p className="text-ink-faint leading-relaxed border-t border-surface-border pt-2">
                  Add a Gemini API key in your backend <code className="bg-surface-high px-1 rounded">.env</code> file to enable live AI responses.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Sessions */}
        <div className="flex-1 overflow-y-auto px-3 space-y-0.5">
          <p className="text-[10px] text-ink-faint uppercase tracking-wider px-1 py-2 font-medium">Recent Chats</p>
          {sessionsData?.sessions?.map(s => (
            <button
              key={s.id}
              onClick={() => loadSession(s.id)}
              className={`w-full text-left px-3 py-2 rounded-xl text-xs transition-colors group flex items-center gap-2 ${
                currentSessionId === s.id
                  ? "bg-brand-maroon/15 text-ink"
                  : "text-ink-muted hover:bg-surface-high hover:text-ink"
              }`}
            >
              <MessageSquare size={12} className="shrink-0 text-ink-faint" />
              <span className="flex-1 truncate">{s.title}</span>
              <button
                onClick={e => { e.stopPropagation(); deleteMutation.mutate(s.id); }}
                className="opacity-0 group-hover:opacity-100 text-ink-faint hover:text-danger transition-all"
              >
                <Trash2 size={11} />
              </button>
            </button>
          ))}
          {(!sessionsData?.sessions || sessionsData.sessions.length === 0) && (
            <p className="text-xs text-ink-faint px-2 py-4 text-center">No chats yet</p>
          )}
        </div>
      </div>

      {/* ── Main Chat Area ───────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-6 py-3.5 border-b border-surface-border flex items-center justify-between">
          <div>
            <h1 className="font-display font-bold text-ink text-lg">SkillBay AI</h1>
            <p className="text-xs text-ink-faint">Your intelligent placement analytics assistant</p>
          </div>
          <div className="flex items-center gap-2">
            <ModelSelector selected={selectedModel} onChange={setSelectedModel} />
            <span className="text-xs bg-brand-maroon/10 text-brand-maroon px-2.5 py-1 rounded-full font-medium border border-brand-maroon/20">
              Placement Mode
            </span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {isWelcome ? (
            <div className="max-w-2xl mx-auto text-center space-y-8 pt-8">
              {/* Welcome hero */}
              <div>
                <div className="h-20 w-20 rounded-3xl bg-gradient-to-br from-brand-maroon to-brand-purple flex items-center justify-center mx-auto mb-4 shadow-lg">
                  <Sparkles size={36} className="text-white" />
                </div>
                <h2 className="font-display font-bold text-2xl text-ink mb-2">Welcome to SkillBay AI</h2>
                <p className="text-ink-muted text-sm max-w-md mx-auto">
                  Your AI-powered placement intelligence assistant. Connected to live student data, job roles, and batch analytics.
                </p>
              </div>

              {/* Capabilities row */}
              <div className="flex items-center justify-center gap-4 flex-wrap">
                {[
                  { icon: Database, label: "Live DB" },
                  { icon: Cpu, label: "Gemini AI" },
                  { icon: Paperclip, label: "File Attach" },
                  { icon: Settings2, label: "Model Select" },
                ].map(({ icon: Icon, label }) => (
                  <div key={label} className="flex items-center gap-1.5 text-[11px] text-ink-faint bg-surface-dim border border-surface-border rounded-full px-3 py-1">
                    <Icon size={11} className="text-brand-maroon" />
                    {label}
                  </div>
                ))}
              </div>

              {/* Prompt templates */}
              <div>
                <p className="text-xs text-ink-faint uppercase tracking-wider mb-4 font-medium">Try a prompt</p>
                <div className="grid grid-cols-2 gap-3 text-left">
                  {templatesData?.templates?.map(t => {
                    const Icon = PROMPT_ICONS[t.id] || Sparkles;
                    return (
                      <button
                        key={t.id}
                        onClick={() => sendMessage(t.prompt)}
                        className="flex items-start gap-3 p-4 rounded-2xl border border-surface-border bg-surface-dim hover:bg-surface-high hover:border-brand-maroon/30 transition-all text-left group"
                      >
                        <div className="h-8 w-8 rounded-xl bg-brand-maroon/10 flex items-center justify-center shrink-0 group-hover:bg-brand-maroon/20 transition-colors">
                          <Icon size={15} className="text-brand-maroon" />
                        </div>
                        <div>
                          <div className="text-xs font-semibold text-ink mb-0.5">{t.label}</div>
                          <div className="text-[11px] text-ink-faint leading-relaxed line-clamp-2">{t.prompt}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((m, i) => (
                <div key={i} className={`flex gap-3 ${m.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                  {/* Avatar */}
                  <div className={`h-8 w-8 rounded-xl shrink-0 flex items-center justify-center text-white text-xs font-bold ${
                    m.role === "user"
                      ? "bg-surface-high border border-surface-border text-ink-muted"
                      : "bg-gradient-to-br from-brand-maroon to-brand-purple"
                  }`}>
                    {m.role === "user" ? "You" : <Sparkles size={14} />}
                  </div>

                  {/* Bubble */}
                  <div className={`flex-1 max-w-[85%] ${m.role === "user" ? "items-end flex flex-col" : ""}`}>
                    <div className={`rounded-2xl px-4 py-3 ${
                      m.role === "user"
                        ? "bg-brand-maroon text-white text-sm rounded-tr-none"
                        : "bg-surface-dim border border-surface-border text-ink rounded-tl-none"
                    }`}>
                      {m.role === "assistant"
                        ? <MarkdownContent text={m.content} />
                        : <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                      }
                    </div>
                    {m.role === "assistant" && (
                      <div className="flex items-center gap-1 mt-1 px-1">
                        <CopyButton text={m.content} />
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex gap-3">
                  <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-brand-maroon to-brand-purple flex items-center justify-center shrink-0">
                    <Sparkles size={14} className="text-white" />
                  </div>
                  <div className="bg-surface-dim border border-surface-border rounded-2xl rounded-tl-none px-4 py-3 flex items-center gap-2">
                    <Loader2 size={14} className="animate-spin text-brand-maroon" />
                    <span className="text-sm text-ink-muted">Analyzing placement data…</span>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="px-6 pb-6 pt-3 border-t border-surface-border">
          <div className="max-w-3xl mx-auto space-y-2">
            {/* Attachment chip */}
            {attachedFile && (
              <div className="flex items-center gap-2 px-1">
                <AttachChip file={attachedFile} onRemove={() => setAttachedFile(null)} />
              </div>
            )}
            <div className="flex items-end gap-3 bg-surface-dim border border-surface-border rounded-2xl px-4 py-3 focus-within:border-brand-maroon/50 focus-within:ring-2 focus-within:ring-brand-maroon/20 transition-all">
              {/* Attach button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="shrink-0 text-ink-faint hover:text-brand-maroon transition-colors pb-0.5"
                title="Attach file or image"
              >
                <Paperclip size={16} />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,.pdf,.xlsx,.xls,.csv,.docx,.txt"
                className="hidden"
                onChange={handleFileSelect}
              />
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask anything about students, batches, job roles, placement analytics… (or attach a file)"
                rows={1}
                className="flex-1 bg-transparent text-sm text-ink placeholder:text-ink-faint outline-none resize-none leading-relaxed"
              />
              <button
                onClick={() => sendMessage()}
                disabled={(!input.trim() && !attachedFile) || loading}
                className="h-9 w-9 flex items-center justify-center rounded-xl bg-gradient-to-br from-brand-maroon to-brand-purple text-white disabled:opacity-30 hover:opacity-90 transition-all shrink-0"
              >
                {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
              </button>
            </div>
            <p className="text-[11px] text-ink-faint text-center">
              Press Enter to send · Shift+Enter for new line · Attach files/images · Connected to live placement database
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
