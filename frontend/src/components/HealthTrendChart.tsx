"use client";

import { AuditJob } from "@/types";

interface HealthTrendChartProps {
  audits: AuditJob[];
}

export default function HealthTrendChart({ audits }: HealthTrendChartProps) {
  const data = audits
    .filter((a) => a.health_score !== null && a.status === "complete")
    .sort(
      (a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    )
    .slice(-10);

  if (data.length < 2) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-500 text-sm">
        Run at least 2 audits on this repo to see trends
      </div>
    );
  }

  const WIDTH = 400;
  const HEIGHT = 120;
  const PADDING = 20;
  const chartWidth = WIDTH - PADDING * 2;
  const chartHeight = HEIGHT - PADDING * 2;

  const scores = data.map((a) => a.health_score as number);
  const minScore = Math.max(0, Math.min(...scores) - 10);
  const maxScore = Math.min(100, Math.max(...scores) + 10);

  const xStep = chartWidth / (data.length - 1);
  const yScale = (score: number) =>
    PADDING +
    chartHeight -
    ((score - minScore) / (maxScore - minScore)) * chartHeight;

  const points = data.map((a, i) => ({
    x: PADDING + i * xStep,
    y: yScale(a.health_score as number),
    score: a.health_score as number,
    date: new Date(a.created_at).toLocaleDateString(),
  }));

  const pathD = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
    .join(" ");

  const latestScore = scores[scores.length - 1];
  const lineColor =
    latestScore >= 80 ? "#22c55e" : latestScore >= 60 ? "#eab308" : "#ef4444";

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full"
        style={{ height: 120 }}
      >
        {[0, 25, 50, 75, 100].map((score) => {
          if (score < minScore || score > maxScore) return null;
          const y = yScale(score);
          return (
            <g key={score}>
              <line
                x1={PADDING}
                y1={y}
                x2={WIDTH - PADDING}
                y2={y}
                stroke="#374151"
                strokeWidth="1"
                strokeDasharray="4"
              />
              <text
                x={PADDING - 4}
                y={y + 4}
                textAnchor="end"
                fill="#6b7280"
                fontSize="9"
              >
                {score}
              </text>
            </g>
          );
        })}

        <path
          d={pathD}
          fill="none"
          stroke={lineColor}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        <path
          d={`${pathD} L ${points[points.length - 1].x} ${
            HEIGHT - PADDING
          } L ${PADDING} ${HEIGHT - PADDING} Z`}
          fill={lineColor}
          fillOpacity="0.1"
        />

        {points.map((p, i) => (
          <g key={i}>
            <circle
              cx={p.x}
              cy={p.y}
              r="4"
              fill={lineColor}
              stroke="#111827"
              strokeWidth="2"
            />
            {(i === 0 || i === points.length - 1) && (
              <text
                x={p.x}
                y={p.y - 8}
                textAnchor="middle"
                fill={lineColor}
                fontSize="10"
                fontWeight="bold"
              >
                {p.score}
              </text>
            )}
          </g>
        ))}
      </svg>

      <div className="flex justify-between text-xs text-slate-500 mt-1 px-5">
        <span>{points[0]?.date}</span>
        {points.length > 2 && (
          <span className="text-slate-600">{points.length} audits</span>
        )}
        <span>{points[points.length - 1]?.date}</span>
      </div>
    </div>
  );
}
