"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { createAudit } from "@/lib/api";
import { Bot, GitBranch, Shield, Zap, BarChart3, Layers, TestTube, Container, BookOpen, ArrowRight, Sparkles } from "lucide-react";

const FEATURES = [
  { icon: Shield, label: "Security", desc: "Hardcoded secrets, injection risks, auth issues" },
  { icon: Zap, label: "Performance", desc: "N+1 queries, blocking ops, missing indexes" },
  { icon: Layers, label: "Architecture", desc: "Coupling, scalability risks, missing async" },
  { icon: TestTube, label: "Testing", desc: "Coverage gaps, untested critical paths" },
  { icon: Container, label: "DevOps", desc: "Docker security, CI/CD gaps" },
  { icon: BookOpen, label: "Documentation", desc: "README quality, API doc coverage" },
];

const DEMO_REPOS = [
  "https://github.com/django/django",
  "https://github.com/tiangolo/fastapi",
  "https://github.com/pallets/flask",
];

export default function HomePage() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await createAudit(repoUrl.trim());
      router.push(`/audits/${result.audit_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start audit");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 pt-32 pb-20">
        {/* Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 mb-8 animate-fade-in-up">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-xs text-indigo-400 font-medium">AI-Powered Codebase Auditor</span>
        </div>

        {/* Headline */}
        <h1
          className="text-5xl md:text-6xl lg:text-7xl font-bold text-center max-w-3xl leading-tight mb-6 animate-fade-in-up"
          style={{ animationDelay: "80ms", animationFillMode: "both" }}
        >
          <span className="gradient-text-hero">Your AI Senior</span>
          <br />
          <span className="gradient-text-hero">Engineer.</span>
        </h1>

        <p
          className="text-lg text-slate-400 text-center max-w-xl leading-relaxed mb-12 animate-fade-in-up"
          style={{ animationDelay: "160ms", animationFillMode: "both" }}
        >
          Point AgentOps at any GitHub repository. 7 specialist AI agents
          audit it in parallel — finding bugs, security holes, and performance
          issues — then score it and optionally fix them.
        </p>

        {/* Submit Form */}
        <div
          className="w-full max-w-2xl animate-fade-in-up"
          style={{ animationDelay: "240ms", animationFillMode: "both" }}
        >
          <div className="gradient-border p-[1px] rounded-2xl mb-3">
            <form
              onSubmit={handleSubmit}
              className="flex items-center gap-3 bg-[#0e0e1a] rounded-2xl px-4 py-3"
            >
              <GitBranch className="w-5 h-5 text-slate-500 flex-shrink-0" />
              <input
                id="repo-url-input"
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/username/repository"
                className="flex-1 bg-transparent text-slate-200 placeholder-slate-600 text-sm outline-none font-code"
                disabled={loading}
                required
              />
              <button
                type="submit"
                disabled={loading || !repoUrl.trim()}
                className="flex items-center gap-2 px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-all duration-200 flex-shrink-0"
                id="audit-submit-btn"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Starting…
                  </>
                ) : (
                  <>
                    Audit Now
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          {error && (
            <p className="text-xs text-red-400 text-center mb-2">{error}</p>
          )}

          {/* Demo repos */}
          <div className="flex items-center gap-2 flex-wrap justify-center">
            <span className="text-xs text-slate-600">Try:</span>
            {DEMO_REPOS.map((url) => (
              <button
                key={url}
                onClick={() => setRepoUrl(url)}
                className="text-xs text-indigo-500 hover:text-indigo-400 font-code transition-colors"
              >
                {url.replace("https://github.com/", "")}
              </button>
            ))}
          </div>
        </div>

        {/* Agent icons */}
        <div
          className="flex items-center gap-4 mt-16 animate-fade-in-up"
          style={{ animationDelay: "320ms", animationFillMode: "both" }}
        >
          <div className="w-10 h-10 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center float">
            <Bot className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="text-xs text-slate-600 text-center">
            Manager Agent coordinates
          </div>
          <div className="flex gap-2">
            {FEATURES.map(({ icon: Icon, label }, i) => (
              <div
                key={label}
                className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/10 flex items-center justify-center float float-delay-1"
                style={{ animationDelay: `${i * 200}ms` }}
                title={label}
              >
                <Icon className="w-4 h-4 text-slate-500" />
              </div>
            ))}
          </div>
        </div>

        {/* Feature grid */}
        <div
          className="grid grid-cols-2 md:grid-cols-3 gap-4 max-w-3xl mt-20 w-full animate-fade-in-up stagger-children"
          style={{ animationDelay: "400ms", animationFillMode: "both" }}
        >
          {FEATURES.map(({ icon: Icon, label, desc }) => (
            <div
              key={label}
              className="glass rounded-xl p-4 animate-fade-in-up group hover:border-indigo-500/20 transition-all duration-300"
            >
              <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center mb-3 group-hover:bg-indigo-500/20 transition-colors">
                <Icon className="w-4 h-4 text-indigo-400" />
              </div>
              <p className="text-sm font-semibold text-slate-300 mb-1">{label}</p>
              <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>

        {/* Confidence CTA */}
        <div className="mt-16 glass rounded-2xl p-6 max-w-2xl w-full text-center">
          <p className="text-sm text-slate-400 mb-3">
            Every finding is validated by a confidence pipeline before you see it.
          </p>
          <div className="flex items-center justify-center gap-6 flex-wrap">
            {[
              { pct: ">95%", label: "Auto-fix allowed", color: "#22c55e" },
              { pct: "85–95%", label: "Suggest, needs approval", color: "#eab308" },
              { pct: "<85%", label: "Evidence only", color: "#94a3b8" },
            ].map(({ pct, label, color }) => (
              <div key={pct} className="flex items-center gap-2">
                <span className="text-sm font-bold font-code" style={{ color }}>
                  {pct}
                </span>
                <span className="text-xs text-slate-500">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
