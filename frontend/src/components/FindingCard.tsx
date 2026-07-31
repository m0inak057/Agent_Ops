"use client";

import { useState } from "react";
import { Finding } from "@/types";
import { CATEGORY_ICONS, CATEGORY_LABELS } from "@/lib/utils";
import SeverityBadge from "./SeverityBadge";
import ConfidenceBar from "./ConfidenceBar";
import { approveFix } from "@/lib/api";
import {
  FileCode,
  ChevronDown,
  ChevronUp,
  Wrench,
  CheckCircle,
  ExternalLink,
  Hash,
} from "lucide-react";

interface FindingCardProps {
  finding: Finding;
  index?: number;
}

export default function FindingCard({ finding, index = 0 }: FindingCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [fixing, setFixing] = useState(false);
  const [fixed, setFixed] = useState(false);
  const [fixError, setFixError] = useState<string | null>(null);

  const canFix =
    finding.auto_fix_available &&
    finding.confidence >= 0.95 &&
    finding.fix_status === "none";

  async function handleApprove() {
    setFixing(true);
    setFixError(null);
    try {
      await approveFix(finding.id);
      setFixed(true);
    } catch (e: unknown) {
      setFixError(e instanceof Error ? e.message : "Fix request failed");
    } finally {
      setFixing(false);
    }
  }

  return (
    <div
      className="glass rounded-xl border animate-fade-in-up overflow-hidden"
      style={{ animationDelay: `${index * 60}ms`, animationFillMode: "both" }}
    >
      {/* Card header — always visible */}
      <button
        className="w-full text-left p-5 flex items-start gap-4 hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Category icon */}
        <span className="text-2xl flex-shrink-0 mt-0.5">
          {CATEGORY_ICONS[finding.category] ?? "🔍"}
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <SeverityBadge severity={finding.severity} />
            <span className="text-xs text-slate-500 font-medium">
              {CATEGORY_LABELS[finding.category]}
            </span>
            {finding.fix_status === "pr_created" && (
              <span className="text-xs text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20 font-medium">
                PR Created
              </span>
            )}
            {fixed && (
              <span className="text-xs text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20 font-medium">
                Fix Queued ✓
              </span>
            )}
          </div>
          <p className="text-sm font-semibold text-slate-200 mb-3 leading-snug">
            {finding.title}
          </p>
          <ConfidenceBar
            confidence={finding.confidence}
            severity={finding.severity}
            showLabel={true}
            className="max-w-48"
          />
        </div>

        <div className="flex-shrink-0 text-slate-600 mt-1">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-5 pb-5 border-t border-white/5">
          <div className="pt-4 space-y-4">
            {/* Evidence detail */}
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Evidence & Detail
              </p>
              <p className="text-sm text-slate-300 leading-relaxed">{finding.detail}</p>
            </div>

            {/* File / line info */}
            {finding.file_path && (
              <div className="flex items-center gap-3 p-3 bg-white/[0.03] rounded-lg border border-white/5">
                <FileCode className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                <span className="text-sm font-code text-slate-300">
                  {finding.file_path}
                  {finding.line_number && (
                    <span className="text-indigo-400 ml-1">
                      <Hash className="w-3 h-3 inline" />
                      {finding.line_number}
                    </span>
                  )}
                </span>
              </div>
            )}

            {/* Agent info */}
            <p className="text-xs text-slate-600">
              Detected by{" "}
              <span className="text-slate-500 font-medium">{finding.agent_role}</span> agent
            </p>

            {/* Actions */}
            <div className="flex items-center gap-3 pt-2">
              {finding.pr_url && (
                <a
                  href={finding.pr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  View Pull Request
                </a>
              )}

              {canFix && !fixed && (
                <button
                  onClick={handleApprove}
                  disabled={fixing}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold transition-all duration-200 glow-indigo"
                >
                  {fixing ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Queuing fix…
                    </>
                  ) : (
                    <>
                      <Wrench className="w-3.5 h-3.5" />
                      Fix Automatically
                    </>
                  )}
                </button>
              )}

              {fixed && (
                <div className="flex items-center gap-1.5 text-xs text-green-400 font-medium">
                  <CheckCircle className="w-4 h-4" />
                  Auto-fix approved — Developer agent will create a PR shortly
                </div>
              )}

              {fixError && (
                <p className="text-xs text-red-400">{fixError}</p>
              )}

              {finding.confidence >= 0.85 && finding.confidence < 0.95 && finding.fix_status === "none" && (
                <p className="text-xs text-slate-500 italic">
                  Confidence {Math.round(finding.confidence * 100)}% — manual review recommended
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
