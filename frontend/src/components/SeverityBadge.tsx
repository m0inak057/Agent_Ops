"use client";

import { cn, SEVERITY_CONFIG } from "@/lib/utils";
import { FindingSeverity } from "@/types";

interface SeverityBadgeProps {
  severity: FindingSeverity;
  className?: string;
}

export default function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  const config = SEVERITY_CONFIG[severity];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border",
        config.bg,
        config.color,
        config.border,
        className
      )}
    >
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ backgroundColor: config.dot }}
      />
      {config.label}
    </span>
  );
}
