import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { FindingSeverity, AuditStatus } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function healthScoreColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#eab308";
  if (score >= 40) return "#f97316";
  return "#ef4444";
}

export function healthScoreLabel(score: number): string {
  if (score >= 80) return "Healthy";
  if (score >= 60) return "Moderate";
  if (score >= 40) return "Concerning";
  return "Critical";
}

export const SEVERITY_CONFIG: Record<
  FindingSeverity,
  { label: string; color: string; bg: string; border: string; dot: string }
> = {
  critical: {
    label: "Critical",
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    dot: "#ef4444",
  },
  high: {
    label: "High",
    color: "text-orange-400",
    bg: "bg-orange-500/10",
    border: "border-orange-500/30",
    dot: "#f97316",
  },
  medium: {
    label: "Medium",
    color: "text-yellow-400",
    bg: "bg-yellow-500/10",
    border: "border-yellow-500/30",
    dot: "#eab308",
  },
  low: {
    label: "Low",
    color: "text-green-400",
    bg: "bg-green-500/10",
    border: "border-green-500/30",
    dot: "#22c55e",
  },
};

export const STATUS_CONFIG: Record<
  AuditStatus,
  { label: string; color: string; bg: string; pulse: boolean }
> = {
  pending: {
    label: "Pending",
    color: "text-slate-400",
    bg: "bg-slate-500/10",
    pulse: false,
  },
  analyzing: {
    label: "Analyzing",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
    pulse: true,
  },
  complete: {
    label: "Complete",
    color: "text-green-400",
    bg: "bg-green-500/10",
    pulse: false,
  },
  failed: {
    label: "Failed",
    color: "text-red-400",
    bg: "bg-red-500/10",
    pulse: false,
  },
};

export const CATEGORY_ICONS: Record<string, string> = {
  security: "🔒",
  code_quality: "🧹",
  architecture: "🏗️",
  performance: "⚡",
  testing: "🧪",
  devops: "🐳",
  documentation: "📄",
};

export const CATEGORY_LABELS: Record<string, string> = {
  security: "Security",
  code_quality: "Code Quality",
  architecture: "Architecture",
  performance: "Performance",
  testing: "Testing",
  devops: "DevOps",
  documentation: "Documentation",
};
