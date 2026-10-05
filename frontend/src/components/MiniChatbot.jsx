import React, { useState, useEffect, useRef, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  MessageCircle,
  X,
  Sparkles,
  Maximize2,
  RotateCcw,
  Zap,
} from "lucide-react";
import { useAiChat } from "../hooks/useAiChat";
import { ChatThread } from "./chat/ChatThread";
import { ChatComposer } from "./chat/ChatComposer";
import { Badge } from "./ui/Badge";

export default function MiniChatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [hasUnread, setHasUnread] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const panelRef = useRef(null);

  // Derive route-aware page context
  const pageContext = useMemo(() => {
    const ctx = { route: location.pathname };
    if (location.pathname.startsWith("/students/")) {
      const parts = location.pathname.split("/");
      ctx.selectedStudentId = parts[2];
    }
    return ctx;
  }, [location.pathname]);

  const {
    messages,
    isStreaming,
    activeToolStatus,
    selectedModel,
    engineStatus,
    attachments,
    addAttachment,
    removeAttachment,
    sendMessage,
    stopStreaming,
    setMessages,
  } = useAiChat({ initialContext: pageContext });

  // Escape key closes modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Set unread indicator when assistant responds and chatbot is closed
  useEffect(() => {
    if (!isOpen && messages.length > 1) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === "assistant" && lastMsg.content) {
        setHasUnread(true);
      }
    }
  }, [isOpen, messages]);

  const handleOpen = () => {
    setIsOpen(true);
    setHasUnread(false);
  };

  const handleSend = () => {
    if (!input.trim() && attachments.length === 0) return;
    const textToSend = input;
    setInput("");
    sendMessage(textToSend, pageContext);
  };

  const handleStarterClick = (prompt) => {
    sendMessage(prompt, pageContext);
  };

  const handleOpenFullPage = () => {
    setIsOpen(false);
    navigate("/ai");
  };

  const handleResetChat = () => {
    setMessages([]);
  };

  // Route-aware suggestion chips
  const routeStarters = useMemo(() => {
    if (location.pathname.startsWith("/students/")) {
      return [
        "Summarize this candidate's clinical competencies",
        "Generate a 30-day targeted preparation plan",
        "What are the top matching Kauvery roles?",
        "Explain the weak skills requiring remediation",
      ];
    }
    if (location.pathname.startsWith("/upload")) {
      return [
        "Explain the consolidation preview results",
        "What are the key data quality warnings?",
        "How many candidates are placement ready?",
        "Break down uniform compliance numbers",
      ];
    }
    return [
      "Who are the top performers in the current batch?",
      "Which students need critical remediation?",
      "What is the cohort placement readiness vs target?",
      "Summarize attendance and typing speed stats",
    ];
  }, [location.pathname]);

  return (
    <>
      {/* Floating Launcher Button */}
      {!isOpen && (
        <button
          onClick={handleOpen}
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2.5 px-4 py-3 bg-brand-maroon text-white rounded-full shadow-lg hover:bg-brand-dark transition-all duration-300 hover:scale-105 active:scale-95 group focus:outline-none focus:ring-4 focus:ring-brand-maroon/30"
          aria-label="Open SkillBay AI assistant"
        >
          <div className="relative">
            <Sparkles size={18} className="animate-spin-slow group-hover:rotate-45 transition-transform" />
            {hasUnread && (
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-brand-yellow rounded-full border-2 border-brand-maroon animate-pulse" />
            )}
          </div>
          <span className="text-xs font-semibold tracking-wide hidden sm:inline">
            Ask SkillBay AI
          </span>
        </button>
      )}

      {/* Floating Chat Modal Panel */}
      {isOpen && (
        <div
          ref={panelRef}
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 sm:inset-auto sm:bottom-5 sm:right-5 sm:w-[420px] sm:h-[620px] z-50 flex flex-col bg-surface border border-surface-border rounded-none sm:rounded-2xl shadow-2xl overflow-hidden transition-all duration-200"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-surface-container border-b border-surface-border shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-xl bg-brand-maroon text-white flex items-center justify-center shadow-xs">
                <Sparkles size={15} />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="font-display font-bold text-xs text-ink">SkillBay AI</span>
                  <Badge
                    tone={engineStatus.mode === "offline" ? "warning" : "brand"}
                    className="text-[9px] py-0 px-1 font-semibold"
                  >
                    {engineStatus.mode === "offline"
                      ? "Offline mode"
                      : engineStatus.model || "Gemini 3.6 Flash"}
                  </Badge>
                </div>
                <div className="text-[10px] text-ink-faint">
                  Kauvery CCDP Placement Assistant
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={handleResetChat}
                className="p-1.5 rounded-lg hover:bg-surface-high text-ink-muted hover:text-ink transition-colors"
                title="Clear chat history"
              >
                <RotateCcw size={14} />
              </button>
              <button
                onClick={handleOpenFullPage}
                className="p-1.5 rounded-lg hover:bg-surface-high text-ink-muted hover:text-ink transition-colors"
                title="Open in full page"
              >
                <Maximize2 size={14} />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg hover:bg-surface-high text-ink-muted hover:text-ink transition-colors"
                title="Close chat (Esc)"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Chat Messages Thread */}
          <ChatThread
            messages={messages}
            activeToolStatus={activeToolStatus}
            onStarterClick={handleStarterClick}
            starterPrompts={routeStarters}
            compact={true}
          />

          {/* Composer Footer */}
          <div className="p-3 bg-surface border-t border-surface-border shrink-0">
            <ChatComposer
              input={input}
              setInput={setInput}
              onSend={handleSend}
              onStop={stopStreaming}
              isStreaming={isStreaming}
              attachments={attachments}
              onAddAttachment={addAttachment}
              onRemoveAttachment={removeAttachment}
              placeholder="Ask a question or request role matching..."
              compact={true}
            />
          </div>
        </div>
      )}
    </>
  );
}
