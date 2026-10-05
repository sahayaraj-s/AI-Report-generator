import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { Check, Copy, ExternalLink } from "lucide-react";

function CodeBlock({ children, className }) {
  const [copied, setCopied] = useState(false);
  const text = String(children).replace(/\n$/, "");

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-2 rounded-xl bg-surface-high/70 border border-surface-border overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1 bg-surface-dim/80 text-[10px] text-ink-faint font-mono border-b border-surface-border">
        <span>Code</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-ink transition-colors"
          title="Copy code"
        >
          {copied ? <Check size={11} className="text-success" /> : <Copy size={11} />}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre className="p-3 text-xs font-mono overflow-x-auto text-ink">
        <code>{children}</code>
      </pre>
    </div>
  );
}

export function MessageRenderer({ content }) {
  if (!content) return null;

  return (
    <div className="prose prose-sm max-w-none text-ink text-[14px] leading-relaxed break-words space-y-2">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-lg font-display font-bold text-ink mt-3 mb-1.5 pb-1 border-b border-surface-border">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-display font-bold text-brand-maroon mt-2.5 mb-1">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-display font-semibold text-ink mt-2 mb-1">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wider mt-1.5 mb-0.5">
              {children}
            </h4>
          ),
          p: ({ children }) => <p className="mb-2 leading-relaxed text-ink">{children}</p>,
          ul: ({ children }) => (
            <ul className="list-disc pl-5 space-y-1 mb-2 text-ink">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 space-y-1 mb-2 text-ink font-medium">{children}</ol>
          ),
          li: ({ children }) => <li className="leading-snug text-ink">{children}</li>,
          table: ({ children }) => (
            <div className="overflow-x-auto my-3 rounded-xl border border-surface-border shadow-xs">
              <table className="w-full text-left text-xs border-collapse divide-y divide-surface-border">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-surface-high/60 text-ink font-bold">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-surface-border bg-surface-container/50">
              {children}
            </tbody>
          ),
          tr: ({ children, isHeader }) => (
            <tr className="hover:bg-surface-high/40 transition-colors odd:bg-surface-container/30">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 text-[11px] font-bold text-ink tracking-wider">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 text-xs text-ink/90 whitespace-normal">
              {children}
            </td>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-brand-maroon/40 bg-brand-maroon/5 pl-3 py-1.5 my-2 rounded-r-lg text-xs italic text-ink-muted">
              {children}
            </blockquote>
          ),
          code: ({ inline, className, children }) => {
            if (inline) {
              return (
                <code className="bg-surface-high text-brand-pink font-mono text-[12px] px-1.5 py-0.5 rounded-md border border-surface-border">
                  {children}
                </code>
              );
            }
            return <CodeBlock className={className}>{children}</CodeBlock>;
          },
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-0.5 text-brand-maroon font-semibold hover:text-brand-pink underline underline-offset-2"
            >
              <span>{children}</span>
              <ExternalLink size={11} className="inline opacity-70" />
            </a>
          ),
          strong: ({ children }) => <strong className="font-bold text-ink">{children}</strong>,
          em: ({ children }) => <em className="italic text-ink-muted">{children}</em>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
