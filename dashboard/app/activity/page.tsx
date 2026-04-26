"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Play, Loader2 } from "lucide-react";
import type { AgentDecision } from "@shared/contracts";
import { DecisionCard } from "@/components/DecisionCard";
import { useDemoMode } from "@/contexts/DemoContext";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function speak(text: string) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.rate = 0.92;
  u.pitch = 1.0;
  window.speechSynthesis.speak(u);
}

export default function ActivityPage() {
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [connected, setConnected]  = useState(false);
  const [running, setRunning]      = useState(false);
  const [, setTick] = useState(0); // increments every second to refresh relative times
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const id = setInterval(() => setTick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const { isDemoMode } = useDemoMode();
  // Use a ref so the SSE closure always reads the latest value without re-subscribing
  const demoRef = useRef(isDemoMode);
  useEffect(() => { demoRef.current = isDemoMode; }, [isDemoMode]);

  // ── SSE stream ─────────────────────────────────────────────────────────
  useEffect(() => {
    const es = new EventSource(`${API_URL}/api/stream`);
    esRef.current = es;
    es.onopen = () => setConnected(true);

    es.onmessage = (event) => {
      if (!event.data) return;
      try {
        const d = JSON.parse(event.data) as AgentDecision;
        setDecisions((prev) => {
          const key = `${d.agent_name}:${d.timestamp}`;
          if (prev.some((x) => `${x.agent_name}:${x.timestamp}` === key)) return prev;
          if (demoRef.current) speak(d.summary);
          return [d, ...prev];
        });
      } catch { /* ignore ping frames */ }
    };

    es.onerror = () => { setConnected(false); es.close(); };
    return () => { es.close(); esRef.current = null; };
  }, []);

  // ── Run / Demo trigger ─────────────────────────────────────────────────
  async function runDemo() {
    setRunning(true);
    const endpoint = isDemoMode ? "/api/trigger/demo" : "/api/trigger/cascade";
    try {
      await fetch(`${API_URL}${endpoint}`, { method: "POST" });
    } finally {
      setRunning(false);
    }
  }

  // ── agent → most-recent card id ────────────────────────────────────────
  const agentRefs: Record<string, string> = {};
  for (const d of decisions) {
    const key = `${d.agent_name}:${d.timestamp}`;
    if (!agentRefs[d.agent_name]) agentRefs[d.agent_name] = key;
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Agent Activity</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Live agent decisions — most recent first
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isDemoMode && (
            <span className="flex items-center gap-1.5 rounded-full bg-blue-950 px-2.5 py-1 text-xs font-medium text-blue-300 ring-1 ring-blue-700">
              <Mic size={11} />
              Demo Mode — seeded · 3 s pacing · voice on
            </span>
          )}

          <span
            className={cn(
              "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
              connected
                ? "bg-emerald-950 text-emerald-400 ring-1 ring-emerald-800"
                : "bg-gray-800 text-gray-500"
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", connected ? "bg-emerald-400 animate-pulse" : "bg-gray-600")} />
            {connected ? "Live" : "Connecting…"}
          </span>

          <button
            onClick={runDemo}
            disabled={running}
            className={cn(
              "flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              isDemoMode
                ? "border-blue-700 bg-blue-950 text-blue-200 hover:bg-blue-900"
                : "border-gray-700 bg-gray-900 text-gray-200 hover:border-gray-600 hover:bg-gray-800"
            )}
          >
            {running
              ? <Loader2 size={13} className="animate-spin text-gray-400" />
              : <Play size={13} className={isDemoMode ? "text-blue-400" : "text-blue-400"} />}
            {running
              ? (isDemoMode ? "Demo running…" : "Running…")
              : (isDemoMode ? "Run Demo" : "Run Demo")}
          </button>
        </div>
      </div>

      {/* Demo mode pacing hint */}
      {isDemoMode && running && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-blue-900/40 bg-blue-950/20 px-4 py-2.5 text-xs text-blue-400">
          <span className="flex gap-1">
            {["Market Intel", "Demand", "Inventory", "Freight", "Coordinator"].map((a) => (
              <span key={a} className="rounded bg-blue-900/40 px-1.5 py-0.5">{a}</span>
            ))}
          </span>
          <span className="text-blue-600">— each fires 3 s apart</span>
        </div>
      )}

      {/* Feed */}
      {decisions.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-800 py-24 text-center">
          <p className="text-sm text-gray-500">No decisions yet.</p>
          <p className="mt-1 text-xs text-gray-700">
            Hit{" "}
            <span className="font-medium text-gray-500">Run Demo</span>
            {" "}to trigger the full agent cascade.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {decisions.map((d) => {
            const cardId = `${d.agent_name}:${d.timestamp}`;
            return (
              <DecisionCard
                key={cardId}
                cardId={cardId}
                decision={d}
                agentRefs={agentRefs}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
