import type { Metadata } from "next";
import "./globals.css";
import { NavLinks } from "@/components/NavLinks";
import { DemoProvider } from "@/contexts/DemoContext";
import { DemoToggle } from "@/components/DemoToggle";

export const metadata: Metadata = {
  title: "SupplyMind",
  description: "Multi-agent supply chain orchestrator — Diamond Foods",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0a0a] text-gray-100 antialiased">
        <DemoProvider>
          <header className="sticky top-0 z-50 border-b border-gray-800/60 bg-[#0a0a0a]/80 backdrop-blur-sm">
            <div className="mx-auto flex h-12 max-w-6xl items-center justify-between px-6">
              <div className="flex items-center gap-6">
                <span className="text-sm font-semibold tracking-tight text-white">
                  Supply<span className="text-blue-400">Mind</span>
                </span>
                <NavLinks />
              </div>
              <div className="flex items-center gap-3">
                <DemoToggle />
                <div className="flex items-center gap-1.5">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  <span className="text-xs text-gray-500">Diamond Foods · Week 47</span>
                </div>
              </div>
            </div>
          </header>
          <div className="mx-auto max-w-6xl px-6 py-8">{children}</div>
        </DemoProvider>
      </body>
    </html>
  );
}
