import { useState, useRef, useEffect } from "react";
import { MessageCircle, X, Send, Sparkles, Loader2, ChevronDown, Paperclip, Image as ImageIcon, FileText } from "lucide-react";
import { api } from "../lib/api";


const QUICK_PROMPTS = [
  "Total students & readiness?",
  "Active job roles & openings?",
  "Top performing students?",
  "Skill gaps overview?",
  "Which batch performs best?",
];

function MarkdownText({ text }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const bold = line.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
        if (line.startsWith("- ") || line.startsWith("• ")) {
          return <div key={i} className="flex gap-1.5"><span className="text-brand-pink mt-0.5">•</span><span dangerouslySetInnerHTML={{ __html: bold.slice(2) }} /></div>;
        }
        return <p key={i} dangerouslySetInnerHTML={{ __html: bold }} className={line.startsWith("#") ? "font-semibold" : ""} />;
      })}
    </div>
  );
}

function AttachChip({ file, onRemove }) {
  const isImage = file.type?.startsWith("image/");
  return (
    <div className="flex items-center gap-1.5 bg-brand-maroon/10 border border-brand-maroon/30 rounded-lg px-2 py-1 text-[11px] text-brand-maroon font-medium max-w-full">
      {isImage ? <ImageIcon size={11} className="shrink-0" /> : <FileText size={11} className="shrink-0" />}
      <span className="truncate max-w-[160px]">{file.name}</span>
      <button onClick={onRemove} className="shrink-0 ml-0.5 hover:text-danger transition-colors">
        <X size={10} />
      </button>
    </div>
  );
}

export default function MiniChatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi! I'm SkillBay AI 👋\nAsk me anything about your placement data, students, job roles, or batch performance." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [attachedFile, setAttachedFile] = useState(null);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
      inputRef.current?.focus();
    }
  }, [open, messages]);

  const ensureSession = async () => {
    if (sessionId) return sessionId;
    const res = await api.post("/api/ai/sessions", { title: "Mini Chat" });
    const id = res.data.id;
    setSessionId(id);
    return id;
  };

  const sendMessage = async (query) => {
    let q = (query || input).trim();
    if (!q && !attachedFile) return;
    if (loading) return;

    // Append file context to query
    if (attachedFile) {
      q = q ? `${q}\n\n[Attached file: ${attachedFile.name}]` : `[Attached file: ${attachedFile.name}] Please analyze or reference this file in your response.`;
    }

    setInput("");
    setAttachedFile(null);

    const newMessages = [...messages, { role: "user", content: q }];
    setMessages(newMessages);
    setLoading(true);

    try {
      const sid = await ensureSession();
      const res = await api.post(`/api/ai/sessions/${sid}/messages`, { content: q });
      setMessages(prev => [...prev, { role: "assistant", content: res.data.content }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I couldn't connect to the AI service right now. Please make sure the backend is running." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleFileSelect = (e) => {
    const f = e.target.files?.[0];
    if (f) setAttachedFile(f);
    e.target.value = "";
  };

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={() => setOpen(o => !o)}
        id="mini-chatbot-trigger"
        className={`fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full shadow-lg flex items-center justify-center transition-all duration-300 ${
          open
            ? "bg-ink text-white rotate-90 scale-90"
            : "bg-gradient-to-br from-brand-maroon to-brand-purple text-white hover:scale-110"
        }`}
      >
        {open ? <X size={20} /> : <MessageCircle size={22} />}
      </button>

      {/* Chat window */}
      <div className={`fixed bottom-24 right-6 z-50 w-[370px] max-h-[540px] rounded-2xl shadow-2xl border border-surface-border bg-surface-dim flex flex-col overflow-hidden transition-all duration-300 ${
        open ? "opacity-100 translate-y-0 pointer-events-auto" : "opacity-0 translate-y-4 pointer-events-none"
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-brand-maroon to-brand-purple">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-white" />
            <span className="text-white font-semibold text-sm">SkillBay AI</span>
            <span className="text-xs bg-white/20 text-white px-2 py-0.5 rounded-full">Beta</span>
          </div>
          <button onClick={() => setOpen(false)} className="text-white/70 hover:text-white">
            <ChevronDown size={18} />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                m.role === "user"
                  ? "bg-brand-maroon text-white rounded-br-none"
                  : "bg-surface-high text-ink rounded-bl-none"
              }`}>
                {m.role === "assistant" ? <MarkdownText text={m.content} /> : m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-surface-high rounded-xl px-3 py-2 flex items-center gap-1.5">
                <Loader2 size={12} className="animate-spin text-brand-maroon" />
                <span className="text-xs text-ink-muted">Thinking…</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Quick Prompts */}
        {messages.length <= 1 && (
          <div className="px-3 pb-2 flex flex-wrap gap-1.5">
            {QUICK_PROMPTS.map(p => (
              <button
                key={p}
                onClick={() => sendMessage(p)}
                className="text-[11px] bg-surface-high border border-surface-border text-ink-muted hover:text-ink hover:bg-brand-maroon/10 hover:border-brand-maroon/30 rounded-lg px-2.5 py-1 transition-colors"
              >
                {p}
              </button>
            ))}
          </div>
        )}

        {/* Attachment chip */}
        {attachedFile && (
          <div className="px-3 pb-1">
            <AttachChip file={attachedFile} onRemove={() => setAttachedFile(null)} />
          </div>
        )}

        {/* Input */}
        <div className="px-3 pb-3">
          <div className="flex items-center gap-2 bg-surface-container border border-surface-border rounded-xl px-3 py-2 focus-within:border-brand-maroon/50 transition-colors">
            {/* Attach button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="text-ink-faint hover:text-brand-maroon transition-colors shrink-0"
              title="Attach file or image"
            >
              <Paperclip size={14} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,.pdf,.xlsx,.xls,.csv,.docx,.txt"
              className="hidden"
              onChange={handleFileSelect}
            />
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask anything about placement data…"
              className="flex-1 bg-transparent text-xs text-ink placeholder:text-ink-faint outline-none"
            />
            <button
              onClick={() => sendMessage()}
              disabled={(!input.trim() && !attachedFile) || loading}
              className="h-7 w-7 flex items-center justify-center rounded-lg bg-brand-maroon text-white disabled:opacity-40 hover:bg-brand-purple transition-colors shrink-0"
            >
              <Send size={13} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
