"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import AuditCard from "@/components/AuditCard";
import HealthTrendChart from "@/components/HealthTrendChart";
import { listAudits } from "@/lib/api";
import { MOCK_AUDITS } from "@/lib/api";
import { AuditJob, AuditStatus } from "@/types";
import { LayoutDashboard, RefreshCw } from "lucide-react";

const STATUS_FILTERS: { value: AuditStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "complete", label: "Complete" },
  { value: "analyzing", label: "Analyzing" },
  { value: "pending", label: "Pending" },
  { value: "failed", label: "Failed" },
];

function SkeletonCard() {
  return (
    <div className="glass rounded-xl p-5 h-[240px] flex flex-col gap-4">
      <div className="flex justify-between">
        <div className="shimmer h-4 w-40 rounded" />
        <div className="shimmer h-5 w-20 rounded-full" />
      </div>
      <div className="flex-1 flex items-center justify-center">
        <div className="shimmer w-24 h-24 rounded-full" />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [audits, setAudits] = useState<AuditJob[]>([]);
  const [filter, setFilter] = useState<AuditStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [useMock, setUseMock] = useState(false);

  async function fetchAudits() {
    setLoading(true);
    try {
      const data = await listAudits(filter === "all" ? undefined : filter);
      setAudits(data);
      setUseMock(false);
    } catch {
      setAudits(MOCK_AUDITS);
      setUseMock(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data fetch on mount
    fetchAudits();
  }, [filter]);

  const filtered = filter === "all"
    ? audits
    : audits.filter((a) => a.status === filter);

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="max-w-7xl mx-auto px-6 pt-24 pb-16">
        {/* Header */}
        <div className="flex items-center justify-between mb-8 animate-fade-in-up">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600/15 border border-indigo-500/20 flex items-center justify-center">
              <LayoutDashboard className="w-4.5 h-4.5 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-100">Audit Dashboard</h1>
              <p className="text-xs text-slate-500 mt-0.5">
                {audits.length} audit{audits.length !== 1 ? "s" : ""}
                {useMock && (
                  <span className="ml-2 text-yellow-500/70">(demo data — backend offline)</span>
                )}
              </p>
            </div>
          </div>
          <button
            onClick={fetchAudits}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg glass text-xs text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Filter tabs */}
        <div
          className="flex gap-1 mb-8 p-1 glass rounded-xl w-fit animate-fade-in-up"
          style={{ animationDelay: "80ms", animationFillMode: "both" }}
        >
          {STATUS_FILTERS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                filter === value
                  ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/30"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <p className="text-4xl mb-4">🔍</p>
            <p className="text-slate-400 font-medium mb-2">No audits found</p>
            <p className="text-slate-600 text-sm">
              {filter === "all"
                ? "Submit a GitHub repo URL to start your first audit."
                : `No audits with status "${filter}".`}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 stagger-children">
            {filtered.map((audit, i) => (
              <div
                key={audit.id}
                className="animate-fade-in-up"
                style={{ animationDelay: `${i * 60}ms`, animationFillMode: "both" }}
              >
                <AuditCard audit={audit} />
              </div>
            ))}
          </div>
        )}

        {/* Health Score Trends */}
        {(() => {
          const repoGroups = audits.reduce((acc, audit) => {
            const key = audit.repo_name ?? audit.repo_url;
            if (!acc[key]) acc[key] = [];
            acc[key].push(audit);
            return acc;
          }, {} as Record<string, typeof audits>);

          const reposWithTrends = Object.entries(repoGroups).filter(
            ([, repoAudits]) =>
              repoAudits.filter((a) => a.status === "complete").length >= 2
          );

          if (reposWithTrends.length === 0) return null;

          return (
            <div className="mt-8">
              <h2 className="text-xl font-semibold text-slate-100 mb-4">
                Health Score Trends
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {reposWithTrends.map(([repoName, repoAudits]) => (
                  <div key={repoName} className="glass rounded-xl p-4">
                    <p className="text-sm text-slate-400 mb-3 truncate">{repoName}</p>
                    <HealthTrendChart audits={repoAudits} />
                  </div>
                ))}
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
