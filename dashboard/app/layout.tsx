import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SupplyMind",
  description: "Multi-agent supply chain orchestrator",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen antialiased">
        <nav className="border-b border-gray-800 px-6 py-3 flex items-center gap-6">
          <span className="font-semibold tracking-tight">SupplyMind</span>
          <a href="/activity" className="text-sm text-gray-400 hover:text-white transition-colors">
            Activity Log
          </a>
          <a href="/plan" className="text-sm text-gray-400 hover:text-white transition-colors">
            Replenishment Plan
          </a>
        </nav>
        {children}
      </body>
    </html>
  );
}
