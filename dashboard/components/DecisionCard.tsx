"use client";

import type { AgentDecision } from "../../shared/contracts";

const AGENT_COLORS: Record<string, { dot: string; label: string }> = {
  demand_planning:    { dot: "bg-blue-500",   label: "text-blue-400" },
  inventory_manager:  { dot: "bg-amber-500",  label: "text-amber-400" },
  shipment_analyst:   { dot: "bg-emerald-500", label: "text-emerald-400" },
  market_intelligence:{ dot: "bg-purple-500", label: "text-purple-400" },
  coordinator:        { dot: "bg-indigo-500", label: "text-indigo-400" },
};

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    value >= 0.8 ? "bg-emerald-900 text-emerald-300 ring-emerald-700" :
    value >= 0.6 ? "bg-yellow-900 text-yellow-300 ring-yellow-700" :
                   "bg-red-900 text-red-300 ring-red-700";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${color}`}>
      {pct}% confidence
    </span>
  );
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function agentLabel(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function DecisionCard({ decision }: { decision: AgentDecision }) {
  const colors = AGENT_COLORS[decision.agent_name] ?? {
    dot: "bg-gray-500",
    label: "text-gray-400",
  };

  return (
    <div className="animate-fade-slide-in rounded-lg border border-gray-800 bg-gray-900 p-4 shadow-sm">
      {/* Header row */}
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${colors.dot}`} />
          <span className={`text-sm font-medium ${colors.label}`}>
            {agentLabel(decision.agent_name)}
          </span>
          <span className="text-xs text-gray-500">·</span>
          <span className="text-xs text-gray-500">{formatTimestamp(decision.timestamp)}</span>
        </div>
        <ConfidenceBadge value={decision.confidence} />
      </div>

      {/* Summary */}
      <p className="text-sm font-semibold text-gray-100 mb-1">{decision.summary}</p>

      {/* Reasoning */}
      <p className="text-sm text-gray-400 leading-relaxed">{decision.reasoning}</p>

      {/* Inputs considered */}
      {decision.inputs_considered.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {decision.inputs_considered.map((inp) => (
            <span
              key={inp}
              className="rounded bg-gray-800 px-1.5 py-0.5 text-xs text-gray-500"
            >
              {inp}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
