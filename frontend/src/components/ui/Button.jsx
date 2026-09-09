const VARIANTS = {
  primary: "bg-brand-maroon text-white hover:bg-[#7A1A4B] shadow-sm",
  secondary: "bg-surface-high text-ink hover:bg-surface-border border border-surface-border",
  ghost: "text-ink-muted hover:text-ink hover:bg-surface-high",
  danger: "bg-danger/10 text-danger hover:bg-danger/20 border border-danger/30",
};

export function Button({ variant = "primary", className = "", children, ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
