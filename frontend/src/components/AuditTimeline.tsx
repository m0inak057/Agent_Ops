"use client";

import { AuditSpan } from "@/lib/api";

interface AuditTimelineProps {
  spans: AuditSpan[];
  totalDurationMs: number;
}

const SPAN_LABELS: Record<string, string> = {
  repo_analyzer: "Repository Analysis",
  unified_agent: "AI Audit (All 7 Dimensions)",
  confidence_pipeline: "Confidence Validation",
  manager: "Finding Synthesis",
  db_write: "Database Write",
  notifier: "Change Detection",
  evaluation: "Agent Evaluation",
  prompt_optimizer: "Self-Improvement Check",
};

const SPAN_ICONS: Record<string, string> = {
  repo_analyzer: "🔍",
  unified_agent: "🤖",
  confidence_pipeline: "✅",
  manager: "📊",
  db_write: "💾",
  notifier: "🔔",
  evaluation: "📈",
  prompt_optimizer: "🧠",
};

function formatDuration(ms: number | null): string {
  if (ms === null) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function StatusIcon({ status }: { status: AuditSpan["status"] }) {
  if (status === "success")
    return <span className="text-green-500 text-lg">✓</span>;
  if (status === "failed")
    return <span className="text-red-500 text-lg">✗</span>;
  if (status === "running")
    return <span className="text-yellow-500 text-lg animate-spin">⟳</span>;
  return <span className="text-gray-400 text-lg">—</span>;
}

export default function AuditTimeline({
  spans,
  totalDurationMs,
}: AuditTimelineProps) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-100">
          Pipeline Timeline
        </h3>
        <span className="text-sm text-slate-400">
          Total: {formatDuration(totalDurationMs)}
        </span>
      </div>

      {spans.map((span, index) => (
        <div
          key={span.id}
          className="glass rounded-lg p-4 border border-white/10"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-slate-500 text-sm w-5 text-right">
                {index + 1}
              </span>
              <span className="text-xl">
                {SPAN_ICONS[span.span_name] ?? "⚙️"}
              </span>
              <div>
                <p className="text-slate-100 font-medium text-sm">
                  {SPAN_LABELS[span.span_name] ?? span.span_name}
                </p>
                {span.output_summary && (
                  <p className="text-slate-400 text-xs mt-0.5">
                    {span.output_summary}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-4">
              <span
                className={`text-sm font-mono ${
                  span.duration_ms && span.duration_ms > 10000
                    ? "text-yellow-400"
                    : "text-slate-300"
                }`}
              >
                {formatDuration(span.duration_ms)}
              </span>
              <StatusIcon status={span.status} />
            </div>
          </div>

          {span.duration_ms && totalDurationMs > 0 && (
            <div className="mt-2 h-1 bg-white/10 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  span.status === "failed"
                    ? "bg-red-500"
                    : span.duration_ms > 10000
                    ? "bg-yellow-500"
                    : "bg-indigo-500"
                }`}
                style={{
                  width: `${Math.min(
                    100,
                    (span.duration_ms / totalDurationMs) * 100
                  )}%`,
                }}
              />
            </div>
          )}

          {span.error && (
            <div className="mt-2 text-red-400 text-xs bg-red-950/50 rounded p-2">
              Error: {span.error}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
