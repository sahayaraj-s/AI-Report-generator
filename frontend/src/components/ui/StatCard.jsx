import { Card } from "./Card";

export function StatCard({ icon: Icon, label, value, sublabel, accent = "text-brand-pink" }) {
  return (
    <Card className="p-5 flex flex-col gap-3 min-w-0">
      <div className="flex items-center justify-between">
        <div className={`h-9 w-9 rounded-xl bg-surface-high flex items-center justify-center ${accent}`}>
          {Icon && <Icon size={18} />}
        </div>
      </div>
      <div>
        <div className="text-2xl font-display font-semibold text-ink tabular-nums truncate">{value}</div>
        <div className="text-sm text-ink-muted mt-0.5">{label}</div>
        {sublabel && <div className="text-xs text-ink-faint mt-1">{sublabel}</div>}
      </div>
    </Card>
  );
}
