import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles,
  Plus,
  Trash2,
  Cpu,
  ChevronDown,
  MessageSquare,
  BookOpen,
  Zap,
  Users,
  Briefcase,
  Layers,
  Database,
  Info,
} from "lucide-react";
import { Layout } from "../components/Layout";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useAiChat } from "../hooks/useAiChat";
import { ChatThread } from "../components/chat/ChatThread";
import { ChatComposer } from "../components/chat/ChatComposer";
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

export default function SkillBayAI() {
  const queryClient = useQueryClient();
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [input, setInput] = useState("");
  const [showInfo, setShowInfo] = useState(false);
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);

  const {
    messages,
    isStreaming,
    activeToolStatus,
    selectedModel,
    setSelectedModel,
    engineStatus,
    availableModels,
    attachments,
    addAttachment,
    removeAttachment,
    sendMessage,
    stopStreaming,
    setMessages,
  } = useAiChat({ defaultSessionId: currentSessionId });

  // Query existing sessions list
  const { data: sessionsData } = useQuery({
    queryKey: ["ai-sessions"],
    queryFn: async () => (await api.get("/api/ai/sessions")).data,
    refetchInterval: 30000,
  });

  // Query prompt templates
  const { data: templatesData } = useQuery({
    queryKey: ["ai-templates"],
    queryFn: async () => (await api.get("/api/ai/templates")).data,
  });

  const sessions = useMemo(() => {
    if (Array.isArray(sessionsData?.sessions)) return sessionsData.sessions;
    if (Array.isArray(sessionsData)) return sessionsData;
    return [];
  }, [sessionsData]);

  const templates = useMemo(() => {
    if (Array.isArray(templatesData?.templates)) return templatesData.templates;
    if (Array.isArray(templatesData)) return templatesData;
    return [];
  }, [templatesData]);

  const deleteSessionMutation = useMutation({
    mutationFn: async (id) => (await api.delete(`/api/ai/sessions/${id}`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-sessions"] });
      if (currentSessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    },
  });

  const handleSelectSession = async (sessId) => {
    try {
      const res = await api.get(`/api/ai/sessions/${sessId}`);
      setCurrentSessionId(sessId);
      if (res.data?.messages) {
        setMessages(
          res.data.messages.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            source: m.source || "gemini",
            model: m.model || "gemini-3.6-flash",
            timestamp: m.created_at,
          }))
        );
      }
    } catch (err) {
      console.error("Failed to load session:", err);
    }
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
  };

  const handleSend = () => {
    if (!input.trim() && attachments.length === 0) return;
    const textToSend = input;
    setInput("");
    sendMessage(textToSend);
  };

  const handleTemplateClick = (prompt) => {
    sendMessage(prompt);
  };

  return (
    <Layout
      title="SkillBay AI Assistant"
      subtitle="Generative Placement Intelligence with Live Function Calling Grounding"
    >
      <div className="flex h-[calc(100vh-140px)] gap-4">
        {/* Sidebar: Sessions & Templates */}
        <div className="hidden lg:flex w-72 flex-col gap-3 shrink-0">
          {/* New Chat Button */}
          <button
            onClick={handleNewChat}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-brand-maroon text-white rounded-xl font-semibold text-xs shadow-sm hover:bg-brand-dark transition-all hover:scale-[1.01] active:scale-[0.99]"
          >
            <Plus size={16} />
            <span>New Chat Session</span>
          </button>

          {/* Model Status Card */}
          <Card className="p-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-ink flex items-center gap-1.5">
                <Cpu size={14} className="text-brand-pink" />
                Active Model
              </span>
              <Badge
                tone={engineStatus.mode === "offline" ? "warning" : "brand"}
                className="text-[10px] py-0 px-1.5"
              >
                {engineStatus.mode === "offline" ? "Offline" : "Online"}
              </Badge>
            </div>

            {/* Model Dropdown Selector */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setModelDropdownOpen((prev) => !prev)}
                className="w-full flex items-center justify-between bg-surface-container border border-surface-border rounded-lg px-2.5 py-1.5 text-xs text-ink font-medium hover:border-brand-maroon transition-colors"
              >
                <span className="truncate">{selectedModel || "gemini-3.6-flash"}</span>
                <ChevronDown size={14} className="text-ink-faint shrink-0" />
              </button>

              {modelDropdownOpen && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-surface border border-surface-border rounded-xl shadow-lg z-30 p-1.5 space-y-1">
                  {(availableModels.length > 0
                    ? availableModels
                    : [
                        { id: "gemini-3.6-flash", label: "Gemini 3.6 Flash (Fast & Capable)" },
                        { id: "gemini-3.5-flash", label: "Gemini 3.5 Flash" },
                        { id: "gemini-3.5-flash-lite", label: "Gemini 3.5 Flash Lite" },
                      ]
                  ).map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => {
                        setSelectedModel(m.id);
                        setModelDropdownOpen(false);
                      }}
                      className={`w-full text-left px-2 py-1.5 rounded-lg text-xs transition-colors flex items-center justify-between ${
                        selectedModel === m.id
                          ? "bg-brand-maroon/10 text-brand-maroon font-bold"
                          : "text-ink hover:bg-surface-high"
                      }`}
                    >
                      <span className="truncate">{m.label || m.id}</span>
                      {selectedModel === m.id && <span className="text-[10px]">✓</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {engineStatus.mode === "offline" && (
              <p className="text-[10px] text-warning bg-warning/10 p-2 rounded-lg leading-tight">
                Offline fallback active: answering using local deterministic engine.
              </p>
            )}
          </Card>

          {/* Quick Prompts Templates */}
          {templates.length > 0 && (
            <Card className="p-3 flex-1 flex flex-col min-h-0">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-faint mb-2">
                Placement Prompt Library
              </span>
              <div className="space-y-1 overflow-y-auto pr-1 flex-1">
                {templates.map((tpl) => {
                  const Icon = PROMPT_ICONS[tpl.category] || Sparkles;
                  return (
                    <button
                      key={tpl.id}
                      onClick={() => handleTemplateClick(tpl.prompt)}
                      className="w-full text-left p-2 rounded-lg hover:bg-surface-high text-xs text-ink-muted hover:text-ink transition-colors flex items-start gap-2 group"
                    >
                      <Icon size={13} className="text-brand-maroon mt-0.5 shrink-0 group-hover:scale-110 transition-transform" />
                      <div className="min-w-0">
                        <div className="font-semibold text-ink text-[11px] truncate">{tpl.title}</div>
                        <div className="text-[10px] text-ink-faint line-clamp-1">{tpl.prompt}</div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </Card>
          )}

          {/* Past Sessions List */}
          <Card className="p-3 h-48 flex flex-col shrink-0">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-faint mb-2">
              Recent Conversations
            </span>
            <div className="space-y-1 overflow-y-auto pr-1 flex-1">
              {sessions.length === 0 ? (
                <div className="text-[11px] text-ink-faint text-center py-4">
                  No saved conversations yet.
                </div>
              ) : (
                sessions.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => handleSelectSession(s.id)}
                    className={`flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition-colors ${
                      currentSessionId === s.id
                        ? "bg-brand-maroon/10 text-brand-maroon font-semibold"
                        : "text-ink-muted hover:text-ink hover:bg-surface-high"
                    }`}
                  >
                    <span className="truncate max-w-[170px] text-[11px]">{s.title || "Chat Session"}</span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSessionMutation.mutate(s.id);
                      }}
                      className="text-ink-faint hover:text-danger p-0.5 rounded transition-colors"
                      title="Delete session"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </Card>

        </div>

        {/* Main Chat Interface */}
        <div className="flex-1 flex flex-col bg-surface border border-surface-border rounded-2xl shadow-sm overflow-hidden">
          {/* Top Chat Bar */}
          <div className="flex items-center justify-between px-5 py-3 bg-surface-container border-b border-surface-border">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-brand-maroon text-white flex items-center justify-center shadow-xs">
                <Sparkles size={16} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-display font-bold text-sm text-ink">SkillBay AI</h2>
                  <Badge
                    tone={engineStatus.mode === "offline" ? "warning" : "brand"}
                    className="text-[10px] py-0 px-1.5"
                  >
                    {engineStatus.mode === "offline"
                      ? "Offline limited mode"
                      : selectedModel || "Gemini 3.6 Flash"}
                  </Badge>
                </div>
                <p className="text-[11px] text-ink-faint">
                  Function-calling grounded on CCDP analytics · No data hallucination
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowInfo((prev) => !prev)}
              className="p-1.5 rounded-lg hover:bg-surface-high text-ink-muted hover:text-ink transition-colors"
              title="Assistant capabilities & ground rules"
            >
              <Info size={16} />
            </button>
          </div>

          {/* Capabilities Info Banner (Collapsible) */}
          {showInfo && (
            <div className="bg-brand-maroon/5 border-b border-brand-maroon/20 px-5 py-2.5 text-xs text-ink flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles size={14} className="text-brand-maroon shrink-0" />
                <span>
                  Every figure and candidate rank is retrieved in real-time from the database. PII fields (phone, address, parent details) are filtered for privacy.
                </span>
              </div>
              <button
                onClick={() => setShowInfo(false)}
                className="text-ink-faint hover:text-ink font-semibold ml-2"
              >
                ✕
              </button>
            </div>
          )}

          {/* Chat Messages */}
          <ChatThread
            messages={messages}
            activeToolStatus={activeToolStatus}
            onStarterClick={handleTemplateClick}
          />

          {/* Composer Footer */}
          <div className="p-4 bg-surface border-t border-surface-border">
            <ChatComposer
              input={input}
              setInput={setInput}
              onSend={handleSend}
              onStop={stopStreaming}
              isStreaming={isStreaming}
              attachments={attachments}
              onAddAttachment={addAttachment}
              onRemoveAttachment={removeAttachment}
              placeholder="Ask about candidate suitability, class stats, or drop a spreadsheet/PDF..."
            />
          </div>
        </div>
      </div>
    </Layout>
  );
}
