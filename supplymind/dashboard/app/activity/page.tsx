"use client";

import { useEffect, useRef, useState } from "react";
import type { AgentDecision } from "@shared/contracts";
import { DecisionCard } from "../../components/DecisionCard";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ActivityPage() {
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // SSE stream — replays history then pushes new decisions
    const es = new EventSource(`${API_URL}/api/stream`);
    esRef.current = es;

    es.onopen = () => setConnected(true);

    es.onmessage = (event) => {
      if (!event.data) return;
      try {
        const decision = JSON.parse(event.data) as AgentDecision;
        setDecisions((prev) => {
          // Deduplicate by timestamp + agent_name in case of SSE replay
          const key = `${decision.agent_name}:${decision.timestamp}`;
          if (prev.some((d) => `${d.agent_name}:${d.timestamp}` === key)) return prev;
          return [decision, ...prev];
        });
      } catch {
        // ignore ping / malformed frames
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, []);

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      {/* Page header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Activity Log</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Live agent decisions — most recent first
          </p>
        </div>
        <span
          className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
            connected
              ? "bg-emerald-900 text-emerald-300"
              : "bg-gray-800 text-gray-500"
          }`}
        >
          <span
            className={`inline-block h-1.5 w-1.5 rounded-full ${
              connected ? "bg-emerald-400" : "bg-gray-600"
            }`}
          />
          {connected ? "Live" : "Connecting…"}
        </span>
      </div>

      {/* Decision feed */}
      {decisions.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-800 py-16 text-center text-sm text-gray-600">
          No decisions yet. Run{" "}
          <code className="rounded bg-gray-800 px-1 py-0.5 text-gray-400">
            python agents/trigger_demand.py
          </code>{" "}
          or{" "}
          <code className="rounded bg-gray-800 px-1 py-0.5 text-gray-400">
            curl -X POST {API_URL}/api/trigger/demand
          </code>
          .
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {decisions.map((d) => (
            <DecisionCard key={`${d.agent_name}:${d.timestamp}`} decision={d} />
          ))}
        </div>
      )}
    </main>
  );
}
