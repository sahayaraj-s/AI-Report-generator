import React from "react";
import { AlertCircle, RefreshCw, UploadCloud } from "lucide-react";
import { Card } from "./Card";

export function PowerBiGauge({
  title = "Cohort Placement Readiness",
  value = 0,
  target = 80,
  min = 0,
  max = 100,
  qualifiedCount,
  totalCount,
  placedCount,
  isLoading = false,
  isError = false,
  isEmpty = false,
  onRetry,
  subtitle,
}) {
  if (isLoading) {
    return (
      <Card className="p-4 flex flex-col items-center justify-between text-center relative overflow-hidden h-[240px]">
        <div className="w-full flex items-center justify-between mb-2">
          <div className="h-3 w-32 bg-surface-high animate-pulse rounded" />
          <div className="h-4 w-16 bg-surface-high animate-pulse rounded-full" />
        </div>
        <div className="w-36 h-20 bg-surface-high animate-pulse rounded-t-full mt-4" />
        <div className="space-y-1 w-full flex flex-col items-center">
          <div className="h-6 w-20 bg-surface-high animate-pulse rounded" />
          <div className="h-3 w-28 bg-surface-high animate-pulse rounded" />
        </div>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card className="p-4 flex flex-col items-center justify-center text-center relative overflow-hidden h-[240px] border-danger/30 bg-danger/5">
        <AlertCircle className="w-8 h-8 text-danger mb-2" />
        <span className="text-xs font-semibold text-ink mb-1">Failed to load readiness</span>
        <p className="text-[11px] text-ink-muted mb-3">Unable to compute placement gauge.</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-medium bg-brand text-white rounded-lg hover:bg-brand-dark transition-colors shadow-sm"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        )}
      </Card>
    );
  }

  const noData = isEmpty || totalCount === 0 || totalCount === undefined;
  if (noData) {
    return (
      <Card className="p-4 flex flex-col items-center justify-center text-center relative overflow-hidden h-[240px]">
        <div className="w-10 h-10 rounded-full bg-surface-high/60 flex items-center justify-center text-ink-muted mb-2">
          <UploadCloud className="w-5 h-5 text-brand" />
        </div>
        <span className="text-xs font-bold text-ink mb-1">{title}</span>
        <p className="text-xs text-ink-muted max-w-[200px]">
          Upload a batch to see readiness
        </p>
      </Card>
    );
  }

  // Clamped percentage: 0 to 100
  const numericValue = typeof value === "number" && !isNaN(value) ? value : 0;
  const percentage = Math.min(max, Math.max(min, numericValue));
  const targetPct = Math.min(max, Math.max(min, target));

  // Geometry
  const radius = 68;
  const cx = 100;
  const cy = 92;
  const strokeWidth = 12;
  const circumference = Math.PI * radius; // Half circle
  const progressOffset = circumference - (percentage / 100) * circumference;

  // Needle angle: 0% = 180 deg (far left), 100% = 0 deg (far right)
  const angleDeg = 180 - (percentage / 100) * 180;
  const angleRad = (angleDeg * Math.PI) / 180;
  const needleLength = radius - 14;
  const nx = cx + needleLength * Math.cos(angleRad);
  const ny = cy - needleLength * Math.sin(angleRad);

  // Target tick mark geometry
  const targetAngleDeg = 180 - (targetPct / 100) * 180;
  const targetAngleRad = (targetAngleDeg * Math.PI) / 180;
  const tx1 = cx + (radius - 10) * Math.cos(targetAngleRad);
  const ty1 = cy - (radius - 10) * Math.sin(targetAngleRad);
  const tx2 = cx + (radius + 10) * Math.cos(targetAngleRad);
  const ty2 = cy - (radius + 10) * Math.sin(targetAngleRad);

  const delta = percentage - targetPct;
  const isAbove = delta > 0.05;
  const isOnTarget = Math.abs(delta) <= 0.05;

  const resolvedQualified = qualifiedCount !== undefined ? qualifiedCount : Math.round((percentage / 100) * totalCount);
  const resolvedPlaced = placedCount !== undefined ? placedCount : 0;
  const placedPct = totalCount > 0 ? ((resolvedPlaced / totalCount) * 100).toFixed(1) : "0.0";

  return (
    <Card
      className="p-4 flex flex-col items-center justify-between text-center relative overflow-hidden h-[240px]"
      role="meter"
      aria-label={`${title}: ${percentage.toFixed(1)}%`}
      aria-valuenow={percentage}
      aria-valuemin={min}
      aria-valuemax={max}
    >
      {/* Header & Delta Pill */}
      <div className="w-full flex items-center justify-between mb-1">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-faint">
          {title}
        </span>
        <span
          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
            isAbove
              ? "bg-success/10 text-success"
              : isOnTarget
              ? "bg-brand/10 text-brand"
              : "bg-warning/15 text-warning"
          }`}
        >
          {isAbove
            ? `+${delta.toFixed(1)} pp above target`
            : isOnTarget
            ? "On target"
            : `${Math.abs(delta).toFixed(1)} pp below target`}
        </span>
      </div>

      {/* SVG Arc with Needle and Target Tick */}
      <div className="relative w-48 h-28 my-1 flex items-center justify-center">
        <svg viewBox="0 0 200 115" className="w-full h-full">
          <defs>
            <linearGradient id="readinessGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#EF4444" />
              <stop offset="35%" stopColor="#EFBC19" />
              <stop offset="70%" stopColor="#72398C" />
              <stop offset="100%" stopColor="#22C55E" />
            </linearGradient>
          </defs>

          {/* Background Track Arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke="currentColor"
            className="text-surface-high"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Active Progress Arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none"
            stroke="url(#readinessGradient)"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={progressOffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />

          {/* Target Benchmark Tick Mark */}
          <line
            x1={tx1}
            y1={ty1}
            x2={tx2}
            y2={ty2}
            stroke="#0F172A"
            className="dark:stroke-white opacity-80"
            strokeWidth="3"
            strokeLinecap="round"
          />

          {/* Needle Indicator */}
          <line
            x1={cx}
            y1={cy}
            x2={nx}
            y2={ny}
            stroke="#8B1D55"
            strokeWidth="2.5"
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
          {/* Needle Center Pivot Hub */}
          <circle cx={cx} cy={cy} r="4" fill="#8B1D55" />
          <circle cx={cx} cy={cy} r="2" fill="#FFFFFF" />
        </svg>

        {/* Center Readout */}
        <div className="absolute bottom-1 left-0 right-0 flex flex-col items-center">
          <div className="text-2xl font-display font-extrabold text-ink tabular-nums tracking-tight">
            {percentage.toFixed(1)}%
          </div>
          <span className="text-[10px] font-medium text-ink-faint">
            Target: <span className="font-semibold text-ink-muted">{targetPct}%</span>
          </span>
        </div>
      </div>

      {/* Caption & Secondary Placed Line */}
      <div className="w-full flex flex-col items-center pt-1 border-t border-border/40">
        <span className="text-[11px] font-semibold text-ink">
          {resolvedQualified} of {totalCount} qualified
        </span>
        <span className="text-[10px] text-ink-muted">
          Placed: {resolvedPlaced} of {totalCount} ({placedPct}%)
        </span>
      </div>
    </Card>
  );
}
