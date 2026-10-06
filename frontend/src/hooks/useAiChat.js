import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../lib/api";

const MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024; // 20 MB
const MAX_ATTACHMENT_COUNT = 5;

export function useAiChat({ defaultSessionId = null, initialContext = {} } = {}) {
  const [sessionId, setSessionId] = useState(defaultSessionId);
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeToolStatus, setActiveToolStatus] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [selectedModel, setSelectedModel] = useState("gemini-3.6-flash");
  const [engineStatus, setEngineStatus] = useState({
    mode: "gemini",
    model: "gemini-3.6-flash",
    last_error: null,
  });
  const [availableModels, setAvailableModels] = useState([]);
  const abortControllerRef = useRef(null);

  // Fetch honest AI engine status & discovered models
  useEffect(() => {
    let mounted = true;
    const fetchStatusAndModels = async () => {
      try {
        const [statusRes, modelsRes] = await Promise.all([
          api.get("/api/ai/status"),
          api.get("/api/ai/models"),
        ]);
        if (mounted) {
          if (statusRes.data) {
            setEngineStatus(statusRes.data);
            if (statusRes.data.model) setSelectedModel(statusRes.data.model);
          }
          if (modelsRes.data?.models) {
            setAvailableModels(modelsRes.data.models);
          }
        }
      } catch (err) {
        if (mounted) {
          setEngineStatus({
            mode: "offline",
            model: "Deterministic Local",
            last_error: "Backend API unreachable",
          });
        }
      }
    };
    fetchStatusAndModels();
    return () => {
      mounted = false;
    };
  }, []);

  // Load existing session messages if sessionId is set
  useEffect(() => {
    if (!sessionId) return;
    let mounted = true;
    const loadSession = async () => {
      try {
        const res = await api.get(`/api/ai/sessions/${sessionId}`);
        if (mounted && res.data?.messages) {
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
      } catch (e) {
        console.warn("Could not load session messages:", e);
      }
    };
    loadSession();
    return () => {
      mounted = false;
    };
  }, [sessionId]);

  const addAttachment = useCallback(async (file) => {
    if (!file) return { error: "No file selected" };
    if (attachments.length >= MAX_ATTACHMENT_COUNT) {
      return { error: `Maximum ${MAX_ATTACHMENT_COUNT} attachments permitted per message.` };
    }
    if (file.size > MAX_ATTACHMENT_SIZE) {
      return { error: `File exceeds the maximum limit of 20 MB.` };
    }

    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const base64Data = e.target.result;
        const newAtt = {
          id: `${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
          name: file.name,
          size: file.size,
          type: file.type || "application/octet-stream",
          data: base64Data,
        };
        setAttachments((prev) => [...prev, newAtt]);
        resolve({ success: true, attachment: newAtt });
      };
      reader.onerror = () => resolve({ error: "Failed to read file." });
      reader.readAsDataURL(file);
    });
  }, [attachments]);

  const removeAttachment = useCallback((id) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const clearAttachments = useCallback(() => {
    setAttachments([]);
  }, []);

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setActiveToolStatus("");
  }, []);

  const sendMessage = useCallback(
    async (text, pageContext = {}) => {
      const trimmed = (text || "").trim();
      if (!trimmed && attachments.length === 0) return;
      if (isStreaming) return;

      // Abort any lingering requests
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      const userMsgId = `user_${Date.now()}`;
      const assistantMsgId = `asst_${Date.now()}`;

      const outgoingAttachments = [...attachments];
      clearAttachments();

      const userMessage = {
        id: userMsgId,
        role: "user",
        content: trimmed || (outgoingAttachments.length > 0 ? `[Attached ${outgoingAttachments.length} file(s)]` : ""),
        attachments: outgoingAttachments.map((a) => ({ name: a.name, type: a.type, size: a.size })),
        timestamp: new Date().toISOString(),
      };

      const initialAssistantMessage = {
        id: assistantMsgId,
        role: "assistant",
        content: "",
        source: engineStatus.mode === "offline" ? "local" : "gemini",
        model: selectedModel,
        toolStatus: "",
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage, initialAssistantMessage]);
      setIsStreaming(true);
      setActiveToolStatus("");

      // Combine page context
      const fullContext = { ...initialContext, ...pageContext };

      // Prepare payload
      const historyPayload = messages.slice(-12).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const payload = {
        query: trimmed,
        content: trimmed,
        history: historyPayload,
        model: selectedModel,
        context: fullContext,
        attachments: outgoingAttachments.map((a) => ({
          name: a.name,
          data: a.data,
        })),
      };

      const token = localStorage.getItem("token") || "";
      const authHeader = token ? `Bearer ${token}` : "";

      try {
        const baseURL = api.defaults.baseURL ?? "";
        const streamUrl = baseURL ? `${baseURL}/api/ai/chat/stream` : "/api/ai/chat/stream";
        const response = await fetch(streamUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(authHeader ? { Authorization: authHeader } : {}),
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Server returned HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let accumulatedText = "";
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let currentEvent = "message";
          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine) continue;

            if (trimmedLine.startsWith("event:")) {
              currentEvent = trimmedLine.replace("event:", "").trim();
            } else if (trimmedLine.startsWith("data:")) {
              const rawData = trimmedLine.replace("data:", "").trim();
              try {
                const parsed = JSON.parse(rawData);
                if (currentEvent === "tool_status") {
                  setActiveToolStatus(parsed.status || "Analyzing data...");
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsgId ? { ...m, toolStatus: parsed.status } : m
                    )
                  );
                } else if (currentEvent === "token") {
                  accumulatedText += parsed.text || "";
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsgId
                        ? { ...m, content: accumulatedText, toolStatus: "" }
                        : m
                    )
                  );
                } else if (currentEvent === "done") {
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsgId
                        ? {
                            ...m,
                            content: accumulatedText,
                            source: parsed.source || m.source,
                            model: parsed.model || m.model,
                            toolStatus: "",
                          }
                        : m
                    )
                  );
                  setActiveToolStatus("");
                } else if (currentEvent === "error") {
                  accumulatedText += `\n\n*(Error: ${parsed.message || "An error occurred."})*`;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsgId ? { ...m, content: accumulatedText, toolStatus: "" } : m
                    )
                  );
                }
              } catch (e) {
                // Non-JSON chunk, append directly if token
                if (currentEvent === "token") {
                  accumulatedText += rawData;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantMsgId ? { ...m, content: accumulatedText } : m
                    )
                  );
                }
              }
            }
          }
        }
      } catch (err) {
        if (err.name === "AbortError") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId ? { ...m, toolStatus: "", content: m.content + " *(Stopped)*" } : m
            )
          );
        } else {
          // Fallback to stateless POST endpoint if SSE stream fails
          try {
            const fallbackRes = await api.post("/api/ai/chat", payload);
            const respText = fallbackRes.data?.content || fallbackRes.data?.response || "No response.";
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      content: respText,
                      source: fallbackRes.data?.source || "local",
                      model: fallbackRes.data?.model || "offline",
                      toolStatus: "",
                    }
                  : m
              )
            );
          } catch (fallbackErr) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? {
                      ...m,
                      content: `Sorry, I encountered an error connecting to the AI service: ${err.message}. Please check your connection or switch to Offline mode.`,
                      source: "offline",
                      toolStatus: "",
                    }
                  : m
              )
            );
          }
        }
      } finally {
        setIsStreaming(false);
        setActiveToolStatus("");
        abortControllerRef.current = null;
      }
    },
    [attachments, clearAttachments, engineStatus.mode, initialContext, isStreaming, messages, selectedModel]
  );

  return {
    sessionId,
    setSessionId,
    messages,
    setMessages,
    isStreaming,
    activeToolStatus,
    selectedModel,
    setSelectedModel,
    engineStatus,
    availableModels,
    attachments,
    addAttachment,
    removeAttachment,
    clearAttachments,
    sendMessage,
    stopStreaming,
  };
}
