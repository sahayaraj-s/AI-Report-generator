import { Card } from "./Card";

export function PowerBiGauge({
  title = "Placement Readiness",
  value = 0,
  target = 80,
  min = 0,
  max = 100,
  subtitle,
}) {
  const percentage = Math.min(max, Math.max(min, value));
  const targetPct = Math.min(max, Math.max(min, target));

  // Gauge geometry: radius 80, stroke width 14
  const radius = 70;
  const cx = 100;
  const cy = 95;
  const strokeWidth = 14;
  const circumference = Math.PI * radius; // Half circle
  const progressOffset = circumference - (percentage / 100) * circumference;
  const targetAngle = (targetPct / 100) * 180; // 0 deg = left, 180 deg = right

  // Target tick coordinates
  const rad = (Math.PI * (180 - targetAngle)) / 180;
  const tx1 = cx + (radius - 12) * Math.cos(rad);
  const ty1 = cy - (radius - 12) * Math.sin(rad);
  const tx2 = cx + (radius + 12) * Math.cos(rad);
  const ty2 = cy - (radius + 12) * Math.sin(rad);

  const delta = value - target;
  const isAbove = delta >= 0;

  return (
    <Card className="p-4 flex flex-col items-center text-center relative overflow-hidden">
      <div className="w-full flex items-center justify-between mb-1">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
          {title}
        </span>
        <span
          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
            isAbove ? "bg-success/10 text-success" : "bg-brand-yellow/10 text-brand-yellow"
          }`}
        >
          {isAbove ? `+${delta.toFixed(1)}%` : `${delta.toFixed(1)}%`} vs Target
        </span>
      </div>

      {/* SVG Arc Gauge */}
      <div className="relative w-48 h-28 my-1 flex items-center justify-center">
        <svg viewBox="0 0 200 115" className="w-full h-full">
          <defs>
            <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#EF4444" />
              <stop offset="35%" stopColor="#EFBC19" />
              <stop offset="70%" stopColor="#72398C" />
              <stop offset="100%" stopColor="#22C55E" />
            </linearGradient>
          </defs>

          {/* Background Arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke="currentColor"
            className="text-surface-high"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Value Progress Arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke="url(#gaugeGradient)"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={progressOffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />

          {/* Target Benchmark Tick Mark */}
          <line
            x1={tx1}
            y1={ty1}
            x2={tx2}
            y2={ty2}
            stroke="#0F172A"
            className="dark:stroke-white"
            strokeWidth="3"
            strokeLinecap="round"
          />
        </svg>

        {/* Center Metric */}
        <div className="absolute bottom-1 left-0 right-0 flex flex-col items-center">
          <div className="text-3xl font-display font-extrabold text-ink tabular-nums tracking-tight">
            {value}%
          </div>
          <span className="text-[10px] font-medium text-ink-faint">
            Target: <span className="font-semibold text-ink-muted">{target}%</span>
          </span>
        </div>
      </div>

      {subtitle && <p className="text-[11px] text-ink-muted mt-1">{subtitle}</p>}
    </Card>
  );
}
