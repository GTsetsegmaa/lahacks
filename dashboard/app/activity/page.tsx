"use client";

import { useEffect, useRef, useState } from "react";
import { Play, Loader2 } from "lucide-react";
import type { AgentDecision } from "@shared/contracts";
import { DecisionCard } from "@/components/DecisionCard";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ActivityPage() {
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [connected, setConnected] = useState(false);
  const [running, setRunning]     = useState(false);
  const esRef = useRef<EventSource | null>(null);

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
          return [d, ...prev];
        });
      } catch { /* ignore ping frames */ }
    };

    es.onerror = () => { setConnected(false); es.close(); };
    return () => { es.close(); esRef.current = null; };
  }, []);

  // ── Run Demo ────────────────────────────────────────────────────────────
  async function runDemo() {
    setRunning(true);
    try {
      await fetch(`${API_URL}/api/trigger/cascade`, { method: "POST" });
    } finally {
      setRunning(false);
    }
  }

  // ── agent → most-recent card id (for cross-ref chip scrolling) ──────────
  const agentRefs: Record<string, string> = {};
  for (const d of decisions) {
    const key = `${d.agent_name}:${d.timestamp}`;
    if (!agentRefs[d.agent_name]) agentRefs[d.agent_name] = key;
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Activity Log</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Live agent decisions — most recent first
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span
            className={cn(
              "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
              connected
                ? "bg-emerald-950 text-emerald-400 ring-1 ring-emerald-800"
                : "bg-gray-800 text-gray-500"
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                connected ? "bg-emerald-400 animate-pulse" : "bg-gray-600"
              )}
            />
            {connected ? "Live" : "Connecting…"}
          </span>

          <button
            onClick={runDemo}
            disabled={running}
            className={cn(
              "flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-900",
              "px-3 py-1.5 text-sm font-medium text-gray-200 transition-colors",
              "hover:border-gray-600 hover:bg-gray-800",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {running
              ? <Loader2 size={13} className="animate-spin text-gray-400" />
              : <Play size={13} className="text-blue-400" />
            }
            {running ? "Running…" : "Run Demo"}
          </button>
        </div>
      </div>

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
