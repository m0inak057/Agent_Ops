"use client";

import { useEffect, useRef } from "react";
import { healthScoreColor, healthScoreLabel } from "@/lib/utils";

interface HealthScoreRingProps {
  score: number;
  size?: number;
}

export default function HealthScoreRing({ score, size = 160 }: HealthScoreRingProps) {
  const circleRef = useRef<SVGCircleElement>(null);
  const radius = 68;
  const circumference = 2 * Math.PI * radius;
  const color = healthScoreColor(score);
  const label = healthScoreLabel(score);

  useEffect(() => {
    if (!circleRef.current) return;
    const offset = circumference - (score / 100) * circumference;
    circleRef.current.style.strokeDashoffset = String(circumference);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (circleRef.current) {
          circleRef.current.style.transition =
            "stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)";
          circleRef.current.style.strokeDashoffset = String(offset);
        }
      });
    });
  }, [score, circumference]);

  return (
    <div className="relative flex flex-col items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(99,102,241,0.1)"
          strokeWidth="10"
        />
        {/* Progress */}
        <circle
          ref={circleRef}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference}
          style={{ filter: `drop-shadow(0 0 8px ${color}66)` }}
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className="text-4xl font-bold text-white tracking-tight leading-none">
          {score}
        </span>
        <span className="text-xs font-medium mt-1" style={{ color }}>
          {label}
        </span>
      </div>
    </div>
  );
}
