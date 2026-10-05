import React, { useRef, useEffect } from "react";
import { Send, Square, Paperclip, X, Image as ImageIcon, FileText, FileSpreadsheet } from "lucide-react";

export function ChatComposer({
  input,
  setInput,
  onSend,
  onStop,
  isStreaming,
  attachments = [],
  onAddAttachment,
  onRemoveAttachment,
  placeholder = "Ask SkillBay AI about students, placement readiness, skills, or batch data...",
  disabled = false,
  compact = false,
}) {
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, compact ? 120 : 160)}px`;
    }
  }, [input, compact]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isStreaming && (input.trim() || attachments.length > 0)) {
        onSend();
      }
    }
  };

  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files || []);
    for (const f of files) {
      await onAddAttachment(f);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handlePaste = async (e) => {
    const items = Array.from(e.clipboardData?.items || []);
    for (const item of items) {
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) {
          e.preventDefault();
          await onAddAttachment(file);
        }
      }
    }
  };

  const getFileIcon = (type, name) => {
    if (type?.startsWith("image/")) return <ImageIcon size={12} className="text-brand-pink shrink-0" />;
    if (name?.endsWith(".xlsx") || name?.endsWith(".csv") || name?.endsWith(".xls")) {
      return <FileSpreadsheet size={12} className="text-success shrink-0" />;
    }
    return <FileText size={12} className="text-brand-purple shrink-0" />;
  };

  return (
    <div className="w-full space-y-2">
      {/* Attachment Preview Chips */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 px-1">
          {attachments.map((att) => (
            <div
              key={att.id}
              className="inline-flex items-center gap-1.5 bg-surface-container border border-surface-border rounded-xl px-2.5 py-1 text-xs text-ink font-medium shadow-xs"
            >
              {getFileIcon(att.type, att.name)}
              <span className="truncate max-w-[140px] text-[11px]">{att.name}</span>
              <button
                type="button"
                onClick={() => onRemoveAttachment(att.id)}
                className="text-ink-faint hover:text-danger p-0.5 rounded transition-colors"
                title="Remove attachment"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input Box with Buttons */}
      <div className="relative flex items-end gap-2 bg-surface-container border border-surface-border rounded-2xl p-2 shadow-xs focus-within:border-brand-maroon focus-within:ring-2 focus-within:ring-brand-maroon/20 transition-all">
        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,.pdf,.xlsx,.xls,.csv"
          onChange={handleFileChange}
          className="hidden"
        />

        {/* Paperclip Attach Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || isStreaming}
          className="p-2 text-ink-muted hover:text-brand-maroon hover:bg-surface-high rounded-xl transition-colors disabled:opacity-40 shrink-0"
          title="Attach image, PDF, or spreadsheet"
        >
          <Paperclip size={18} />
        </button>

        {/* Auto-growing Text Area */}
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={placeholder}
          disabled={disabled}
          className="w-full bg-transparent resize-none outline-none text-xs sm:text-sm text-ink placeholder:text-ink-faint py-1.5 max-h-[160px] overflow-y-auto"
        />

        {/* Action Button: Send or Stop */}
        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            className="p-2 bg-danger text-white rounded-xl hover:bg-danger-dark transition-all shrink-0 shadow-sm animate-pulse"
            title="Stop generation"
          >
            <Square size={16} />
          </button>
        ) : (
          <button
            type="button"
            onClick={onSend}
            disabled={disabled || (!input.trim() && attachments.length === 0)}
            className="p-2 bg-brand-maroon text-white rounded-xl hover:bg-brand-dark transition-all disabled:opacity-40 disabled:hover:bg-brand-maroon shrink-0 shadow-sm"
            title="Send message (Enter)"
          >
            <Send size={16} />
          </button>
        )}
      </div>
      <div className="flex items-center justify-between px-2 text-[10px] text-ink-faint">
        <span>Enter to send · Shift+Enter for new line · Supports Images & PDFs</span>
      </div>
    </div>
  );
}
