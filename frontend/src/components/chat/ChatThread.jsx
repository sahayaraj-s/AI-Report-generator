import React, { useEffect, useRef, useState } from "react";
import {
  Sparkles,
  Bot,
  User,
  Copy,
  Check,
  Download,
  ThumbsUp,
  ThumbsDown,
  RotateCw,
  FileSpreadsheet,
  FileText,
  Loader2,
} from "lucide-react";
import { MessageRenderer } from "./MessageRenderer";
import { Badge } from "../ui/Badge";

function escapeCsvCell(val) {
  if (val === null || val === undefined) return '""';
  let str = String(val);
  if (/^[=+@\-\t\r]/.test(str)) {
    str = "'" + str;
  }
  return `"${str.replace(/"/g, '""')}"`;
}

function exportAnswerAsCsv(text, title = "SkillBay_AI_Response") {
  // Try to parse markdown tables into CSV
  const lines = text.split("\n");
  const tableLines = lines.filter((l) => l.trim().startsWith("|") && l.trim().endsWith("|"));

  let csvContent = "";
  if (tableLines.length >= 2) {
    for (const tl of tableLines) {
      // Skip separator rows like |---|---|
      if (/^\|(\s*[-:]+\s*\|)+$/.test(tl.trim())) continue;
      const cells = tl
        .split("|")
        .slice(1, -1)
        .map((c) => escapeCsvCell(c.trim()));
      csvContent += cells.join(",") + "\r\n";
    }
  } else {
    // Plain text export
    csvContent = "Section,Content\r\n";
    lines.forEach((l) => {
      if (l.trim()) {
        csvContent += `${escapeCsvCell("Response")},${escapeCsvCell(l.trim())}\r\n`;
      }
    });
  }

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${title}_${Date.now()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function ChatThread({
  messages = [],
  activeToolStatus = "",
  onStarterClick,
  starterPrompts = [
    "Who are the top performers in the current batch?",
    "Which students need critical remediation?",
    "What is the cohort placement readiness vs target?",
    "Summarize attendance and typing speed stats",
  ],
  compact = false,
}) {
  const bottomRef = useRef(null);
  const [copiedId, setCopiedId] = useState(null);
  const [feedback, setFeedback] = useState({});

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeToolStatus]);

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleFeedback = (id, type) => {
    setFeedback((prev) => ({ ...prev, [id]: type }));
  };

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-12 h-12 rounded-2xl bg-brand-maroon/10 border border-brand-maroon/20 flex items-center justify-center text-brand-maroon mb-3 shadow-xs">
          <Sparkles size={24} />
        </div>
        <h3 className="font-display font-bold text-base text-ink mb-1">
          SkillBay AI Placement Intelligence
        </h3>
        <p className="text-xs text-ink-muted max-w-sm mb-6">
          Ask questions grounded in your Kauvery CCDP data. Function calling retrieves live scores, tiers, attendance, and placements.
        </p>

        {starterPrompts?.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
            {starterPrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => onStarterClick && onStarterClick(prompt)}
                className="p-3 text-left bg-surface-container hover:bg-surface-high border border-surface-border hover:border-brand-maroon/40 rounded-xl text-xs text-ink font-medium transition-all group shadow-2xs"
              >
                <div className="flex items-center justify-between">
                  <span className="group-hover:text-brand-maroon transition-colors line-clamp-2">
                    {prompt}
                  </span>
                  <span className="text-ink-faint group-hover:text-brand-maroon transition-colors text-sm ml-1">
                    →
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`flex-1 overflow-y-auto space-y-4 p-4 ${compact ? "p-3 space-y-3" : "p-6 space-y-5"}`}>
      {messages.map((m) => {
        const isUser = m.role === "user";

        if (isUser) {
          return (
            <div key={m.id} className="flex justify-end items-end gap-2">
              <div className="max-w-[85%] sm:max-w-[75%] bg-brand-maroon text-white rounded-2xl rounded-br-xs px-4 py-2.5 text-xs sm:text-sm shadow-sm space-y-1">
                <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>
                {m.attachments?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1.5 border-t border-white/20">
                    {m.attachments.map((att, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1 bg-white/20 rounded-md px-2 py-0.5 text-[10px] text-white"
                      >
                        <FileText size={10} />
                        <span className="truncate max-w-[120px]">{att.name}</span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="w-6 h-6 rounded-full bg-brand-maroon/20 text-brand-maroon flex items-center justify-center text-[10px] font-bold shrink-0 mb-1">
                <User size={12} />
              </div>
            </div>
          );
        }

        const isOffline = m.source === "local" || m.source === "offline";
        const hasContent = Boolean(m.content?.trim());

        return (
          <div key={m.id} className="flex justify-start items-start gap-2.5">
            <div className="w-7 h-7 rounded-xl bg-brand-maroon/10 text-brand-maroon border border-brand-maroon/20 flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
              <Sparkles size={14} />
            </div>

            <div className="flex-1 max-w-[90%] sm:max-w-[85%] bg-surface-container border border-surface-border rounded-2xl rounded-tl-xs p-4 shadow-xs space-y-3">
              {/* Header with Source & Model Badge */}
              <div className="flex items-center justify-between text-[11px] border-b border-surface-border pb-2">
                <div className="flex items-center gap-1.5">
                  <span className="font-semibold text-ink">SkillBay AI</span>
                  <Badge
                    tone={isOffline ? "warning" : "brand"}
                    className="text-[10px] py-0 px-1.5 font-normal"
                  >
                    {isOffline ? "Offline Mode" : m.model || "Gemini 3.6 Flash"}
                  </Badge>
                </div>
                {m.timestamp && (
                  <span className="text-[10px] text-ink-faint">
                    {new Date(m.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                )}
              </div>

              {/* Tool Execution Status Chip */}
              {(m.toolStatus || activeToolStatus) && !hasContent && (
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-brand-maroon/5 border border-brand-maroon/20 text-brand-maroon text-xs animate-pulse">
                  <Loader2 size={12} className="animate-spin" />
                  <span>{m.toolStatus || activeToolStatus}</span>
                </div>
              )}

              {/* Markdown Content */}
              {hasContent ? (
                <MessageRenderer content={m.content} />
              ) : (
                <div className="flex items-center gap-2 text-ink-muted text-xs py-2">
                  <Loader2 size={14} className="animate-spin text-brand-maroon" />
                  <span>Synthesizing placement insights...</span>
                </div>
              )}

              {/* Footer Toolbar */}
              {hasContent && (
                <div className="flex items-center justify-between pt-2 border-t border-surface-border text-ink-faint text-xs">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleCopy(m.id, m.content)}
                      className="p-1 rounded-lg hover:bg-surface-high text-ink-muted hover:text-ink transition-colors flex items-center gap-1 text-[11px]"
                      title="Copy response"
                    >
                      {copiedId === m.id ? (
                        <Check size={12} className="text-success" />
                      ) : (
                        <Copy size={12} />
                      )}
                      <span>{copiedId === m.id ? "Copied" : "Copy"}</span>
                    </button>

                    <button
                      onClick={() => exportAnswerAsCsv(m.content, `SkillBay_Answer_${m.id}`)}
                      className="p-1 rounded-lg hover:bg-surface-high text-ink-muted hover:text-ink transition-colors flex items-center gap-1 text-[11px]"
                      title="Export as CSV"
                    >
                      <FileSpreadsheet size={12} />
                      <span>Export CSV</span>
                    </button>
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleFeedback(m.id, "up")}
                      className={`p-1 rounded-lg hover:bg-surface-high transition-colors ${
                        feedback[m.id] === "up" ? "text-success font-bold" : "text-ink-muted"
                      }`}
                      title="Good response"
                    >
                      <ThumbsUp size={12} />
                    </button>
                    <button
                      onClick={() => handleFeedback(m.id, "down")}
                      className={`p-1 rounded-lg hover:bg-surface-high transition-colors ${
                        feedback[m.id] === "down" ? "text-danger font-bold" : "text-ink-muted"
                      }`}
                      title="Poor response"
                    >
                      <ThumbsDown size={12} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
