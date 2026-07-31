"use client";

import Link from "next/link";
import { AuditJob } from "@/types";
import { timeAgo, healthScoreColor, CATEGORY_ICONS } from "@/lib/utils";
import StatusBadge from "./StatusBadge";
import HealthScoreRing from "./HealthScoreRing";
import { GitFork, Clock, FileSearch } from "lucide-react";

interface AuditCardProps {
  audit: AuditJob;
}

export default function AuditCard({ audit }: AuditCardProps) {
  const isComplete = audit.status === "complete" && audit.health_score !== null;

  return (
    <Link href={`/audits/${audit.id}`}>
      <div className="glass rounded-xl p-5 hover:border-indigo-500/30 transition-all duration-300 group cursor-pointer h-full flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              <GitFork className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
              <span className="text-sm font-semibold text-slate-200 truncate group-hover:text-white transition-colors">
                {audit.repo_name ?? audit.repo_url}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Clock className="w-3 h-3" />
              {timeAgo(audit.created_at)}
            </div>
          </div>
          <StatusBadge status={audit.status} className="flex-shrink-0" />
        </div>

        {/* Health score or loading */}
        <div className="flex items-center justify-center py-2">
          {isComplete ? (
            <HealthScoreRing score={audit.health_score!} size={120} />
          ) : audit.status === "analyzing" ? (
            <div className="flex flex-col items-center gap-3 py-4">
              <div className="flex gap-1.5">
                {Object.keys(CATEGORY_ICONS).slice(0, 5).map((cat, i) => (
                  <span
                    key={cat}
                    className="text-lg agent-active"
                    style={{ animationDelay: `${i * 300}ms` }}
                  >
                    {CATEGORY_ICONS[cat]}
                  </span>
                ))}
              </div>
              <p className="text-xs text-indigo-400 font-medium animate-pulse">
                Agents analyzing…
              </p>
            </div>
          ) : audit.status === "pending" ? (
            <div className="flex flex-col items-center gap-2 py-4">
              <div className="w-8 h-8 rounded-full border-2 border-slate-700 border-t-indigo-500 animate-spin" />
              <p className="text-xs text-slate-500">Queued…</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 py-4">
              <FileSearch className="w-8 h-8 text-red-400/50" />
              <p className="text-xs text-red-400">Audit failed</p>
            </div>
          )}
        </div>

        {/* Footer */}
        {isComplete && (
          <div className="text-center">
            <span className="text-xs text-slate-500">
              Completed {timeAgo(audit.completed_at!)}
            </span>
          </div>
        )}
      </div>
    </Link>
  );
}
