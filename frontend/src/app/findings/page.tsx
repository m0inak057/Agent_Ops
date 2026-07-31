"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import FindingCard from "@/components/FindingCard";
import SeverityBadge from "@/components/SeverityBadge";
import { listAudits, listFindings, MOCK_FINDINGS } from "@/lib/api";
import { Finding, FindingCategory, FindingSeverity } from "@/types";
import { CATEGORY_LABELS, CATEGORY_ICONS } from "@/lib/utils";
import { Search } from "lucide-react";

const SEVERITY_FILTERS: { value: FindingSeverity | "all"; label: string }[] = [
  { value: "all", label: "All Severities" },
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const CATEGORY_FILTERS = [
  { value: "all" as const, label: "All Categories" },
  ...Object.keys(CATEGORY_LABELS).map((k) => ({
    value: k as FindingCategory,
    label: `${CATEGORY_ICONS[k]} ${CATEGORY_LABELS[k]}`,
  })),
];

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [useMock, setUseMock] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<FindingSeverity | "all">("all");
  const [categoryFilter, setCategoryFilter] = useState<FindingCategory | "all">("all");

  useEffect(() => {
    async function fetchAll() {
      try {
        const audits = await listAudits("complete");
        const allFindings = await Promise.all(
          audits.slice(0, 10).map((a) => listFindings(a.id))
        );
        setFindings(allFindings.flat());
        setUseMock(false);
      } catch {
        setFindings(MOCK_FINDINGS);
        setUseMock(true);
      } finally {
        setLoading(false);
      }
    }
    fetchAll();
  }, []);

  const filtered = findings.filter((f) => {
    const matchesSeverity = severityFilter === "all" || f.severity === severityFilter;
    const matchesCategory = categoryFilter === "all" || f.category === categoryFilter;
    const matchesSearch =
      !searchQuery ||
      f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      f.detail.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSeverity && matchesCategory && matchesSearch;
  });

  const critCount = findings.filter((f) => f.severity === "critical").length;
  const highCount = findings.filter((f) => f.severity === "high").length;

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="max-w-7xl mx-auto px-6 pt-24 pb-16">
        {/* Header */}
        <div className="mb-8 animate-fade-in-up">
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-xl bg-indigo-600/15 border border-indigo-500/20 flex items-center justify-center">
              <Search className="w-4.5 h-4.5 text-indigo-400" />
            </div>
            <h1 className="text-xl font-bold text-slate-100">All Findings</h1>
          </div>
          <p className="text-xs text-slate-500 ml-12">
            {findings.length} total findings across all audits
            {useMock && (
              <span className="ml-2 text-yellow-500/70">(demo data)</span>
            )}
          </p>
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8 animate-fade-in-up" style={{ animationDelay: "80ms", animationFillMode: "both" }}>
          {(["critical", "high", "medium", "low"] as FindingSeverity[]).map((sev, i) => {
            const count = findings.filter((f) => f.severity === sev).length;
            return (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev === severityFilter ? "all" : sev)}
                className="glass rounded-xl p-4 text-center cursor-pointer hover:border-indigo-500/20 transition-all duration-200"
              >
                <div className="text-2xl font-bold text-slate-100 mb-1">{count}</div>
                <SeverityBadge severity={sev} />
              </button>
            );
          })}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-6 animate-fade-in-up" style={{ animationDelay: "160ms", animationFillMode: "both" }}>
          {/* Search */}
          <div className="flex-1 min-w-48 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600" />
            <input
              type="text"
              placeholder="Search findings…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 glass rounded-lg text-sm text-slate-300 placeholder-slate-600 outline-none border border-white/5 focus:border-indigo-500/30 transition-colors bg-transparent"
            />
          </div>

          {/* Severity */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as FindingSeverity | "all")}
            className="px-3 py-2 glass rounded-lg text-xs text-slate-400 border border-white/10 bg-transparent outline-none"
          >
            {SEVERITY_FILTERS.map(({ value, label }) => (
              <option key={value} value={value} className="bg-[#0e0e1a]">
                {label}
              </option>
            ))}
          </select>

          {/* Category */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value as FindingCategory | "all")}
            className="px-3 py-2 glass rounded-lg text-xs text-slate-400 border border-white/10 bg-transparent outline-none"
          >
            {CATEGORY_FILTERS.map(({ value, label }) => (
              <option key={value} value={value} className="bg-[#0e0e1a]">
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* Results count */}
        <p className="text-xs text-slate-600 mb-4">
          Showing {filtered.length} of {findings.length} findings
        </p>

        {/* List */}
        {loading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="shimmer h-20 rounded-xl" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="glass rounded-xl p-16 text-center">
            <p className="text-4xl mb-4">🔍</p>
            <p className="text-slate-400 text-sm">No findings match your filters.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((finding, i) => (
              <FindingCard key={finding.id} finding={finding} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
