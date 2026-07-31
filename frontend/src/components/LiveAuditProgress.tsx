"use client";

import { CATEGORY_ICONS } from "@/lib/utils";

const AGENTS = [
  { role: "repo_analyzer", label: "Repository Analyzer" },
  { role: "security", label: "Security Agent" },
  { role: "code_quality", label: "Code Quality Agent" },
  { role: "architecture", label: "Architecture Agent" },
  { role: "performance", label: "Performance Agent" },
  { role: "testing", label: "Testing Agent" },
  { role: "devops", label: "DevOps Agent" },
  { role: "documentation", label: "Documentation Agent" },
];

const ICONS: Record<string, string> = {
  repo_analyzer: "🔍",
  security: CATEGORY_ICONS.security,
  code_quality: CATEGORY_ICONS.code_quality,
  architecture: CATEGORY_ICONS.architecture,
  performance: CATEGORY_ICONS.performance,
  testing: CATEGORY_ICONS.testing,
  devops: CATEGORY_ICONS.devops,
  documentation: CATEGORY_ICONS.documentation,
};

export default function LiveAuditProgress() {
  return (
    <div className="glass rounded-xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="pulse-dot" />
        <div>
          <p className="text-sm font-semibold text-slate-200">Audit In Progress</p>
          <p className="text-xs text-slate-500 mt-0.5">Agent team is analyzing your repository</p>
        </div>
      </div>

      <div className="space-y-2.5">
        {AGENTS.map((agent, i) => (
          <div
            key={agent.role}
            className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.03] border border-white/5"
          >
            <span className="text-base agent-active" style={{ animationDelay: `${i * 250}ms` }}>
              {ICONS[agent.role]}
            </span>
            <span className="text-sm text-slate-400 flex-1">{agent.label}</span>
            <div className="flex gap-1">
              {[0, 1, 2].map((dot) => (
                <div
                  key={dot}
                  className="w-1 h-1 rounded-full bg-indigo-500 animate-bounce"
                  style={{ animationDelay: `${dot * 200 + i * 100}ms` }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-slate-600 mt-4 text-center">
        This typically takes 30–90 seconds. Page refreshes automatically.
      </p>
    </div>
  );
}
