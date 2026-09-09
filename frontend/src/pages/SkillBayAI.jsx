import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles, Send, Loader2, Plus, Trash2, Copy, Check, Database,
  MessageSquare, ChevronRight, BookOpen, Zap, Users, Briefcase
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

export default function SkillBayAI() {
  const queryClient = useQueryClient();
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const textareaRef = useRef(null);

  const { data: sessionsData } = useQuery({
    queryKey: ["ai-sessions"],
    queryFn: async () => (await api.get("/api/ai/sessions")).data,
    refetchInterval: 30000,
  });

  const { data: templatesData } = useQuery({
    queryKey: ["ai-templates"],
    queryFn: async () => (await api.get("/api/ai/templates")).data,
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
    const q = (query || input).trim();
    if (!q || loading) return;
    setInput("");

    const userMsg = { role: "user", content: q };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await api.post("/api/ai/sessions", {
        query: q,
        session_id: currentSessionId,
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
    inputRef.current?.focus();
  };

  const isWelcome = messages.length === 0;

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

        {/* DB Status */}
        <div className="px-3 pb-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success/10 border border-success/20">
            <Database size={11} className="text-success" />
            <span className="text-[11px] text-success font-medium">Connected to SkillBay DB</span>
          </div>
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
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
          <div>
            <h1 className="font-display font-bold text-ink text-lg">SkillBay AI</h1>
            <p className="text-xs text-ink-faint">Your intelligent placement analytics assistant</p>
          </div>
          <div className="flex items-center gap-2">
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
                        : <p className="text-sm">{m.content}</p>
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
          <div className="max-w-3xl mx-auto">
            <div className="flex items-end gap-3 bg-surface-dim border border-surface-border rounded-2xl px-4 py-3 focus-within:border-brand-maroon/50 focus-within:ring-2 focus-within:ring-brand-maroon/20 transition-all">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask anything about students, batches, job roles, placement analytics…"
                rows={1}
                className="flex-1 bg-transparent text-sm text-ink placeholder:text-ink-faint outline-none resize-none leading-relaxed"
              />
              <button
                onClick={() => sendMessage()}
                disabled={!input.trim() || loading}
                className="h-9 w-9 flex items-center justify-center rounded-xl bg-gradient-to-br from-brand-maroon to-brand-purple text-white disabled:opacity-30 hover:opacity-90 transition-all shrink-0"
              >
                {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
              </button>
            </div>
            <p className="text-[11px] text-ink-faint text-center mt-2">
              Press Enter to send · Shift+Enter for new line · Connected to live placement database
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
