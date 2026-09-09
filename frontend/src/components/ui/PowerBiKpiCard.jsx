import { Card } from "./Card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export function PowerBiKpiCard({
  icon: Icon,
  title,
  value,
  target,
  targetLabel = "Target",
  unit = "",
  delta,
  deltaType = "positive", // 'positive' | 'negative' | 'neutral'
  subtext,
  accentColor = "#8B1D55", // brand maroon default
  progressPct,
  badgeText,
  onClick,
}) {
  return (
    <Card
      onClick={onClick}
      className={`p-4 relative overflow-hidden transition-all duration-200 group ${
        onClick ? "cursor-pointer hover:border-brand-maroon/50 hover:shadow-lg" : ""
      }`}
    >
      {/* Power BI Accent Top Indicator */}
      <div
        className="absolute top-0 left-0 right-0 h-1 transition-all duration-300 group-hover:h-1.5"
        style={{ backgroundColor: accentColor }}
      />

      <div className="flex items-start justify-between gap-2 pt-1">
        <div className="min-w-0 flex-1">
          <span className="text-[11px] font-semibold text-ink-faint uppercase tracking-wider block truncate">
            {title}
          </span>
          <div className="flex items-baseline gap-1.5 mt-1">
            <span className="text-2xl lg:text-3xl font-display font-bold text-ink tabular-nums tracking-tight">
              {value}
            </span>
            {unit && <span className="text-xs text-ink-muted font-medium">{unit}</span>}
          </div>
        </div>

        {Icon && (
          <div
            className="h-9 w-9 rounded-xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-105"
            style={{
              backgroundColor: `${accentColor}18`,
              color: accentColor,
            }}
          >
            <Icon size={18} />
          </div>
        )}
      </div>

      {/* Target & Delta Row */}
      {(target !== undefined || delta !== undefined || badgeText) && (
        <div className="mt-2.5 pt-2 border-t border-surface-border flex items-center justify-between text-xs gap-2">
          {target !== undefined ? (
            <div className="text-[11px] text-ink-faint">
              <span>{targetLabel}: </span>
              <span className="font-semibold text-ink-muted">{target}</span>
            </div>
          ) : badgeText ? (
            <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-surface-high text-ink-muted">
              {badgeText}
            </span>
          ) : (
            <div />
          )}

          {delta !== undefined && (
            <div
              className={`flex items-center gap-0.5 text-[11px] font-semibold px-1.5 py-0.5 rounded-md ${
                deltaType === "positive"
                  ? "text-success bg-success/10"
                  : deltaType === "negative"
                  ? "text-danger bg-danger/10"
                  : "text-ink-muted bg-surface-high"
              }`}
            >
              {deltaType === "positive" ? (
                <TrendingUp size={11} />
              ) : deltaType === "negative" ? (
                <TrendingDown size={11} />
              ) : (
                <Minus size={11} />
              )}
              <span>{delta}</span>
            </div>
          )}
        </div>
      )}

      {/* Power BI Target Progress Bar */}
      {progressPct !== undefined && (
        <div className="mt-2">
          <div className="w-full h-1.5 rounded-full bg-surface-high overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, Math.max(0, progressPct))}%`,
                backgroundColor: accentColor,
              }}
            />
          </div>
        </div>
      )}

      {subtext && <p className="text-[10px] text-ink-faint mt-1.5 truncate">{subtext}</p>}
    </Card>
  );
}
