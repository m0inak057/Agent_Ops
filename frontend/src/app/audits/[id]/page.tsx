"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import HealthScoreRing from "@/components/HealthScoreRing";
import CategoryScores from "@/components/CategoryScores";
import FindingCard from "@/components/FindingCard";
import LiveAuditProgress from "@/components/LiveAuditProgress";
import SeverityBadge from "@/components/SeverityBadge";
import StatusBadge from "@/components/StatusBadge";
import { getAudit, listFindings, findingsSummary, MOCK_FINDINGS } from "@/lib/api";
import { AuditJob, Finding, FindingCategory, FindingSeverity, FindingSummary } from "@/types";
import { CATEGORY_LABELS, CATEGORY_ICONS, timeAgo } from "@/lib/utils";
import { ArrowLeft, GitFork, Clock, AlertTriangle } from "lucide-react";
import Link from "next/link";

const SEVERITY_FILTERS: { value: FindingSeverity | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "critical", label: "🔴 Critical" },
  { value: "high", label: "🟠 High" },
  { value: "medium", label: "🟡 Medium" },
  { value: "low", label: "🟢 Low" },
];

const CATEGORY_FILTERS = [
  { value: "all" as const, label: "All Categories" },
  ...Object.keys(CATEGORY_LABELS).map((k) => ({
    value: k as FindingCategory,
    label: `${CATEGORY_ICONS[k]} ${CATEGORY_LABELS[k]}`,
  })),
];

export default function AuditDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [audit, setAudit] = useState<AuditJob | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [summary, setSummary] = useState<FindingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<FindingSeverity | "all">("all");
  const [categoryFilter, setCategoryFilter] = useState<FindingCategory | "all">("all");
  const [useMock, setUseMock] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const auditData = await getAudit(id);
      setAudit(auditData);

      if (auditData.status === "complete") {
        const [findingsData, summaryData] = await Promise.all([
          listFindings(id),
          findingsSummary(id),
        ]);
        setFindings(findingsData);
        setSummary(summaryData);
      }
      setUseMock(false);
    } catch {
      // Use mock data for the first MOCK_AUDIT
      const mockAudit = {
        id,
        repo_url: "https://github.com/example/django-ecommerce",
        repo_name: "example/django-ecommerce",
        status: "complete" as const,
        health_score: 71,
        created_at: new Date(Date.now() - 3600000).toISOString(),
        completed_at: new Date(Date.now() - 3000000).toISOString(),
      };
      setAudit(mockAudit);
      setFindings(MOCK_FINDINGS);
      setSummary({
        critical: 2, high: 3, medium: 2, low: 1,
        by_category: { security: 2, performance: 1, devops: 2, testing: 1, code_quality: 1, documentation: 1, architecture: 0 },
      });
      setUseMock(true);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data fetch on mount
    fetchAll();
  }, [fetchAll]);

  // Poll while analyzing
  useEffect(() => {
    if (audit?.status !== "analyzing" && audit?.status !== "pending") return;
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, [audit?.status, fetchAll]);

  const filteredFindings = findings.filter((f) => {
    const sev = severityFilter === "all" || f.severity === severityFilter;
    const cat = categoryFilter === "all" || f.category === categoryFilter;
    return sev && cat;
  });

  if (loading) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <div className="max-w-7xl mx-auto px-6 pt-24 pb-16">
          <div className="animate-pulse space-y-6">
            <div className="shimmer h-6 w-48 rounded" />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="shimmer h-64 rounded-xl" />
              <div className="lg:col-span-2 shimmer h-64 rounded-xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!audit) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Navbar />
        <div className="text-center">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-slate-300 font-medium mb-2">Audit not found</p>
          <Link href="/dashboard" className="text-sm text-indigo-400 hover:underline">
            Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  const isLive = audit.status === "analyzing" || audit.status === "pending";

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="max-w-7xl mx-auto px-6 pt-24 pb-16">

        {/* Back + header */}
        <div className="mb-8 animate-fade-in-up">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-4 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
          </Link>

          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <GitFork className="w-4 h-4 text-slate-500" />
                <h1 className="text-xl font-bold text-slate-100">
                  {audit.repo_name ?? audit.repo_url}
                </h1>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={audit.status} />
                {useMock && (
                  <span className="text-xs text-yellow-500/70">(demo data)</span>
                )}
                <span className="text-xs text-slate-600 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {timeAgo(audit.created_at)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {isLive ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <LiveAuditProgress />
            <div className="glass rounded-xl p-6 flex flex-col items-center justify-center gap-4">
              <p className="text-slate-400 text-sm text-center">
                Findings will appear here once the audit completes.
              </p>
              <p className="text-xs text-slate-600 text-center">
                Audit ID: <span className="font-code text-slate-500">{id}</span>
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Summary row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              {/* Health score */}
              <div className="glass rounded-xl p-6 flex flex-col items-center justify-center gap-4 animate-fade-in-up">
                <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">
                  Health Score
                </p>
                {audit.health_score !== null && (
                  <HealthScoreRing score={audit.health_score} size={160} />
                )}
                <p className="text-xs text-slate-600">
                  Completed {audit.completed_at ? timeAgo(audit.completed_at) : "—"}
                </p>
              </div>

              {/* Severity counts */}
              <div
                className="glass rounded-xl p-6 animate-fade-in-up"
                style={{ animationDelay: "80ms", animationFillMode: "both" }}
              >
                <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mb-4">
                  Findings by Severity
                </p>
                {summary && (
                  <div className="space-y-3">
                    {(["critical", "high", "medium", "low"] as FindingSeverity[]).map((sev) => {
                      const count = summary[sev];
                      return (
                        <div key={sev} className="flex items-center justify-between">
                          <SeverityBadge severity={sev} />
                          <span className="text-sm font-bold text-slate-200">{count}</span>
                        </div>
                      );
                    })}
                    <div className="border-t border-white/5 pt-3 flex justify-between">
                      <span className="text-xs text-slate-500">Total findings</span>
                      <span className="text-sm font-bold text-slate-200">{findings.length}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Category scores */}
              {summary && (
                <div
                  className="animate-fade-in-up"
                  style={{ animationDelay: "160ms", animationFillMode: "both" }}
                >
                  <CategoryScores summary={summary} healthScore={audit.health_score ?? 0} />
                </div>
              )}
            </div>

            {/* Findings list */}
            <div
              className="animate-fade-in-up"
              style={{ animationDelay: "240ms", animationFillMode: "both" }}
            >
              <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                <h2 className="text-base font-bold text-slate-200">
                  Findings ({filteredFindings.length})
                </h2>
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Severity filter */}
                  <div className="flex gap-1 p-1 glass rounded-lg">
                    {SEVERITY_FILTERS.map(({ value, label }) => (
                      <button
                        key={value}
                        onClick={() => setSeverityFilter(value)}
                        className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-150 ${
                          severityFilter === value
                            ? "bg-indigo-600/25 text-indigo-300"
                            : "text-slate-500 hover:text-slate-300"
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  {/* Category filter */}
                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value as FindingCategory | "all")}
                    className="px-2.5 py-1.5 rounded-lg glass text-xs text-slate-400 border border-white/10 bg-transparent outline-none"
                  >
                    {CATEGORY_FILTERS.map(({ value, label }) => (
                      <option key={value} value={value} className="bg-[#0e0e1a]">
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {filteredFindings.length === 0 ? (
                <div className="glass rounded-xl p-12 text-center">
                  <p className="text-slate-400 text-sm">No findings match the current filter.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredFindings.map((finding, i) => (
                    <FindingCard key={finding.id} finding={finding} index={i} />
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
