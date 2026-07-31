"use client";

import { CATEGORY_ICONS, CATEGORY_LABELS, healthScoreColor } from "@/lib/utils";
import { FindingSummary } from "@/types";

interface CategoryScoresProps {
  summary: FindingSummary;
  healthScore: number;
}

const CATEGORY_WEIGHTS: Record<string, number> = {
  security: 0.25,
  code_quality: 0.15,
  architecture: 0.15,
  performance: 0.15,
  testing: 0.15,
  devops: 0.10,
  documentation: 0.05,
};

function computeCategoryScore(category: string, count: number): number {
  const weight = CATEGORY_WEIGHTS[category] ?? 0.1;
  const penalty = Math.min(count * 8, 40);
  return Math.max(Math.round(100 - penalty), 0);
}

interface ScoreBarProps {
  label: string;
  icon: string;
  score: number;
  delay: number;
}

function ScoreBar({ label, icon, score, delay }: ScoreBarProps) {
  const color = healthScoreColor(score);
  return (
    <div className="group" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-sm">{icon}</span>
          <span className="text-xs font-medium text-slate-400 group-hover:text-slate-300 transition-colors">
            {label}
          </span>
        </div>
        <span className="text-xs font-bold" style={{ color }}>
          {score}
        </span>
      </div>
      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{
            width: `${score}%`,
            backgroundColor: color,
            boxShadow: `0 0 6px ${color}55`,
          }}
        />
      </div>
    </div>
  );
}

export default function CategoryScores({ summary, healthScore }: CategoryScoresProps) {
  const categories = Object.keys(CATEGORY_WEIGHTS);

  return (
    <div className="glass rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">Category Scores</h3>
      <div className="space-y-3.5">
        {categories.map((cat, i) => {
          const count = summary.by_category[cat] ?? 0;
          const score = computeCategoryScore(cat, count);
          return (
            <ScoreBar
              key={cat}
              label={CATEGORY_LABELS[cat]}
              icon={CATEGORY_ICONS[cat]}
              score={score}
              delay={i * 80}
            />
          );
        })}
      </div>
    </div>
  );
}
