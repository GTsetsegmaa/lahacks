"use client";

import { BarChart3, Cpu, Package, TrendingUp, Truck } from "lucide-react";
import type { AgentDecision } from "@shared/contracts";
import { cn } from "@/lib/utils";

// ─── Agent metadata ────────────────────────────────────────────────────────

type AgentMeta = {
  icon: React.ElementType;
  dot: string;
  label: string;
  border: string;
  glow: string;
};

const AGENT_META: Record<string, AgentMeta> = {
  market_intelligence: {
    icon: TrendingUp,
    dot:    "bg-yellow-400",
    label:  "text-yellow-400",
    border: "border-yellow-500/20",
    glow:   "shadow-yellow-950/40",
  },
  demand_planning: {
    icon: BarChart3,
    dot:    "bg-blue-400",
    label:  "text-blue-400",
    border: "border-blue-500/20",
    glow:   "shadow-blue-950/40",
  },
  inventory_manager: {
    icon: Package,
    dot:    "bg-purple-400",
    label:  "text-purple-400",
    border: "border-purple-500/20",
    glow:   "shadow-purple-950/40",
  },
  shipment_analyst: {
    icon: Truck,
    dot:    "bg-emerald-400",
    label:  "text-emerald-400",
    border: "border-emerald-500/20",
    glow:   "shadow-emerald-950/40",
  },
  coordinator: {
    icon: Cpu,
    dot:    "bg-gray-200",
    label:  "text-gray-200",
    border: "border-gray-500/30",
    glow:   "shadow-gray-900/40",
  },
};

const FALLBACK_META: AgentMeta = {
  icon: Cpu,
  dot: "bg-gray-500", label: "text-gray-400",
  border: "border-gray-700", glow: "",
};

// ─── Helpers ────────────────────────────────────────────────────────────────

const AGENT_NAMES = [
  "market_intelligence", "demand_planning",
  "inventory_manager", "shipment_analyst", "coordinator",
];

function agentLabel(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatTime(iso: string): string {
  const diffS = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diffS < 5)  return "just now";
  if (diffS < 60) return `${diffS}s ago`;
  if (diffS < 3600) return `${Math.floor(diffS / 60)}m ago`;
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const cls =
    value >= 0.8 ? "bg-emerald-950 text-emerald-400 ring-emerald-800" :
    value >= 0.6 ? "bg-yellow-950 text-yellow-400 ring-yellow-800" :
                   "bg-red-950 text-red-400 ring-red-800";
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset", cls)}>
      {pct}%
    </span>
  );
}

// ─── Cross-reference chips ──────────────────────────────────────────────────

function RefChip({
  agentName,
  agentRefs,
}: {
  agentName: string;
  agentRefs: Record<string, string>;
}) {
  const meta = AGENT_META[agentName] ?? FALLBACK_META;
  const targetId = agentRefs[agentName];

  const handleClick = () => {
    if (!targetId) return;
    document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <button
      onClick={handleClick}
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs transition-colors",
        meta.border,
        "bg-gray-900 hover:bg-gray-800",
        meta.label,
        !targetId && "opacity-40 cursor-default"
      )}
    >
      <span className={cn("inline-block h-1.5 w-1.5 rounded-full", meta.dot)} />
      {agentLabel(agentName)}
    </button>
  );
}

// ─── Main card ──────────────────────────────────────────────────────────────

export function DecisionCard({
  decision,
  cardId,
  agentRefs,
}: {
  decision: AgentDecision;
  cardId: string;
  agentRefs: Record<string, string>;
}) {
  const meta = AGENT_META[decision.agent_name] ?? FALLBACK_META;
  const Icon = meta.icon;

  // Extract referenced agents from inputs_considered
  const referencedAgents = Array.from(
    new Set(
      (decision.inputs_considered ?? [])
        .flatMap((inp) => AGENT_NAMES.filter((n) => inp.includes(n)))
    )
  ).filter((n) => n !== decision.agent_name);

  return (
    <div
      id={cardId}
      className={cn(
        "animate-fade-slide-down rounded-xl border bg-gray-900/60 p-4 shadow-sm backdrop-blur-sm",
        meta.border
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5">
          <div className={cn("flex h-7 w-7 items-center justify-center rounded-lg bg-gray-800", meta.label)}>
            <Icon size={14} />
          </div>
          <div>
            <span className={cn("text-sm font-medium", meta.label)}>
              {agentLabel(decision.agent_name)}
            </span>
            <span className="ml-2 text-xs text-gray-600">
              {formatTime(decision.timestamp)}
            </span>
          </div>
        </div>
        <ConfidenceBadge value={decision.confidence} />
      </div>

      {/* Summary */}
      <p className="text-sm font-medium text-gray-100 mb-1.5 leading-snug">
        {decision.summary}
      </p>

      {/* Reasoning */}
      <p className="text-sm text-gray-400 leading-relaxed mb-3">
        {decision.reasoning}
      </p>

      {/* Footer: inputs + cross-refs */}
      <div className="flex flex-wrap items-center gap-1.5">
        {decision.inputs_considered.map((inp) => (
          <span
            key={inp}
            className="rounded-md bg-gray-800/80 px-1.5 py-0.5 text-xs text-gray-500"
          >
            {inp}
          </span>
        ))}
        {referencedAgents.length > 0 && (
          <>
            <span className="text-xs text-gray-700">→</span>
            {referencedAgents.map((name) => (
              <RefChip key={name} agentName={name} agentRefs={agentRefs} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
