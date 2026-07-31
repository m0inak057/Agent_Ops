"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import { listAudits, listEvaluations, MOCK_EVALUATIONS } from "@/lib/api";
import { Evaluation, AuditJob } from "@/types";
import { BarChart3, TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { timeAgo } from "@/lib/utils";

interface MetricRow {
  metric: string;
  score: number;
  feedback: string | null;
  auditId: string;
  evaluatedAt: string;
}

const METRIC_CONFIG: Record<string, { label: string; good: number; format: (n: number) => string }> = {
  agent_success_rate: { label: "Agent Success Rate", good: 0.80, format: (n) => `${(n * 100).toFixed(0)}%` },
  average_confidence: { label: "Average Confidence", good: 0.70, format: (n) => `${(n * 100).toFixed(0)}%` },
  audit_quality_finding_relevance: { label: "Finding Relevance", good: 0.70, format: (n) => `${(n * 100).toFixed(0)}%` },
  false_positive_rate: { label: "False Positive Rate", good: 0.10, format: (n) => `${(n * 100).toFixed(1)}%` },
};

function MetricCard({ label, score, good, format, trend }: {
  label: string; score: number; good: number; format: (n: number) => string; trend: "up" | "down" | "flat";
}) {
  const passing = score >= good;
  return (
    <div className="glass rounded-xl p-5">
      <p className="text-xs text-slate-500 font-medium mb-3">{label}</p>
      <div className="flex items-end justify-between">
        <div>
          <p className={`text-3xl font-bold ${passing ? "text-green-400" : "text-red-400"}`}>
            {format(score)}
          </p>
          <p className={`text-xs mt-1 ${passing ? "text-green-500/70" : "text-red-500/70"}`}>
            {passing ? `✓ Above threshold (${format(good)})` : `✗ Below threshold (${format(good)})`}
          </p>
        </div>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${passing ? "bg-green-500/10" : "bg-red-500/10"}`}>
          {trend === "up" ? (
            <TrendingUp className="w-4 h-4 text-green-400" />
          ) : trend === "down" ? (
            <TrendingDown className="w-4 h-4 text-red-400" />
          ) : (
            <Minus className="w-4 h-4 text-slate-500" />
          )}
        </div>
      </div>
    </div>
  );
}

const CHART_COLORS = ["#6366f1", "#22c55e", "#f97316", "#eab308"];

interface TooltipPayloadEntry {
  name: string;
  value: number;
  color: string;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-lg p-3 border border-indigo-500/20 text-xs">
      <p className="text-slate-400 mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-medium">
          {p.name}: {(p.value * 100).toFixed(0)}%
        </p>
      ))}
    </div>
  );
};

export default function EvaluationsPage() {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [audits, setAudits] = useState<AuditJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [useMock, setUseMock] = useState(false);

  useEffect(() => {
    async function fetch() {
      try {
        const auditList = await listAudits("complete");
        setAudits(auditList);
        const allEvals = await Promise.all(
          auditList.slice(0, 8).map((a) =>
            listEvaluations(a.id).then((evals) =>
              evals.map((e) => ({ ...e, auditId: a.id }))
            )
          )
        );
        setEvaluations(allEvals.flat());
        setUseMock(false);
      } catch {
        setEvaluations(MOCK_EVALUATIONS);
        setUseMock(true);
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  // Build chart data grouped by audit
  const chartData = audits.slice(0, 8).map((audit) => {
    const auditEvals = evaluations.filter((e) => e.audit_id === audit.id);
    const point: Record<string, unknown> = {
      name: audit.repo_name?.split("/")[1] ?? audit.id.slice(0, 6),
    };
    for (const metric of Object.keys(METRIC_CONFIG)) {
      const ev = auditEvals.find((e) => e.metric === metric);
      if (ev) point[metric] = ev.score;
    }
    return point;
  });

  // Latest metric summaries
  const latestByMetric: Record<string, number> = {};
  for (const metric of Object.keys(METRIC_CONFIG)) {
    const vals = evaluations.filter((e) => e.metric === metric).map((e) => e.score);
    if (vals.length) latestByMetric[metric] = vals[vals.length - 1];
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="max-w-7xl mx-auto px-6 pt-24 pb-16">
        {/* Header */}
        <div className="mb-8 animate-fade-in-up">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-xl bg-indigo-600/15 border border-indigo-500/20 flex items-center justify-center">
              <BarChart3 className="w-4.5 h-4.5 text-indigo-400" />
            </div>
            <h1 className="text-xl font-bold text-slate-100">Agent Evaluations</h1>
          </div>
          <p className="text-xs text-slate-500 ml-12">
            Agent performance metrics across {audits.length} audits
            {useMock && <span className="ml-2 text-yellow-500/70">(demo data)</span>}
          </p>
        </div>

        {/* Metric cards */}
        <div
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 stagger-children"
          style={{ animationFillMode: "both" }}
        >
          {Object.entries(METRIC_CONFIG).map(([key, cfg], i) => (
            <div
              key={key}
              className="animate-fade-in-up"
              style={{ animationDelay: `${i * 80}ms`, animationFillMode: "both" }}
            >
              {latestByMetric[key] !== undefined ? (
                <MetricCard
                  label={cfg.label}
                  score={latestByMetric[key]}
                  good={cfg.good}
                  format={cfg.format}
                  trend="flat"
                />
              ) : (
                <div className="glass rounded-xl p-5 h-full">
                  <p className="text-xs text-slate-500 font-medium mb-3">{cfg.label}</p>
                  <p className="text-slate-600 text-sm">No data yet</p>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Chart */}
        <div
          className="glass rounded-xl p-6 mb-8 animate-fade-in-up"
          style={{ animationDelay: "320ms", animationFillMode: "both" }}
        >
          <h2 className="text-sm font-semibold text-slate-300 mb-6">
            Metric Trends Over Audits
          </h2>
          {loading ? (
            <div className="shimmer h-64 rounded-lg" />
          ) : chartData.length < 2 ? (
            <div className="flex items-center justify-center h-64 text-slate-500 text-sm">
              Need at least 2 completed audits to show trends.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 11, color: "#64748b" }} />
                {Object.entries(METRIC_CONFIG).map(([key, cfg], i) => (
                  <Line
                    key={key}
                    type="monotone"
                    dataKey={key}
                    name={cfg.label}
                    stroke={CHART_COLORS[i % CHART_COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 4, fill: CHART_COLORS[i % CHART_COLORS.length], strokeWidth: 0 }}
                    activeDot={{ r: 6 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Raw evaluation log */}
        <div
          className="glass rounded-xl p-6 animate-fade-in-up"
          style={{ animationDelay: "400ms", animationFillMode: "both" }}
        >
          <h2 className="text-sm font-semibold text-slate-300 mb-4">
            Recent Evaluation Log
          </h2>
          {loading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => <div key={i} className="shimmer h-10 rounded-lg" />)}
            </div>
          ) : evaluations.length === 0 ? (
            <p className="text-slate-500 text-sm">No evaluations recorded yet.</p>
          ) : (
            <div className="space-y-2">
              {evaluations.slice(0, 20).map((ev) => {
                const cfg = METRIC_CONFIG[ev.metric];
                const passing = cfg ? ev.score >= cfg.good : true;
                return (
                  <div
                    key={ev.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-white/[0.03] border border-white/5 group hover:border-white/10 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${passing ? "bg-green-400" : "bg-red-400"}`} />
                      <span className="text-xs text-slate-400 font-medium truncate">
                        {cfg?.label ?? ev.metric}
                      </span>
                      {ev.feedback && (
                        <span className="text-xs text-slate-600 truncate hidden md:block">
                          — {ev.feedback}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 flex-shrink-0">
                      <span className={`text-sm font-bold ${passing ? "text-green-400" : "text-red-400"}`}>
                        {cfg ? cfg.format(ev.score) : ev.score.toFixed(3)}
                      </span>
                      <span className="text-xs text-slate-600">
                        {timeAgo(ev.evaluated_at)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
