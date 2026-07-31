import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentOps — AI Codebase Auditor",
  description:
    "AI-powered autonomous codebase auditor. Point it at any GitHub repository and get a full health report with severity-ranked findings, confidence scores, and optional auto-fixes.",
  keywords: ["AI", "code audit", "security", "LLMOps", "codebase analysis"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-grid min-h-screen">
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
