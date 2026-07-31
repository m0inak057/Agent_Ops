"use client";

import { useEffect, useRef } from "react";
import { SEVERITY_CONFIG } from "@/lib/utils";
import { FindingSeverity } from "@/types";

interface ConfidenceBarProps {
  confidence: number;
  severity?: FindingSeverity;
  showLabel?: boolean;
  className?: string;
}

export default function ConfidenceBar({
  confidence,
  severity,
  showLabel = true,
  className,
}: ConfidenceBarProps) {
  const barRef = useRef<HTMLDivElement>(null);
  const pct = Math.round(confidence * 100);
  const color = severity ? SEVERITY_CONFIG[severity].dot : "#6366f1";

  useEffect(() => {
    if (!barRef.current) return;
    barRef.current.style.width = "0%";
    const t = setTimeout(() => {
      if (barRef.current) {
        barRef.current.style.transition = "width 1.1s cubic-bezier(0.4,0,0.2,1)";
        barRef.current.style.width = `${pct}%`;
      }
    }, 80);
    return () => clearTimeout(t);
  }, [pct]);

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-1">
        {showLabel && (
          <span className="text-xs text-slate-500 font-medium">Confidence</span>
        )}
        <span className="text-xs font-semibold" style={{ color }}>
          {pct}%
        </span>
      </div>
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div
          ref={barRef}
          className="h-full rounded-full"
          style={{
            backgroundColor: color,
            boxShadow: `0 0 8px ${color}66`,
            width: "0%",
          }}
        />
      </div>
    </div>
  );
}
