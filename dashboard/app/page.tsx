"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Cpu,
  DollarSign,
  Loader2,
  Package,
  Play,
  RefreshCw,
  TrendingUp,
  Truck,
  Zap,
} from "lucide-react";
import Link from "next/link";
import type { AgentDecision } from "@shared/contracts";
import { cn } from "@/lib/utils";
import { SavingsCounter } from "@/components/SavingsCounter";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Types ──────────────────────────────────────────────────────────────────

interface PlanSummary {
  critical_orders: number;
  total_orders: number;
  total_units_to_order: number;
  total_estimated_cost_usd: number;
}

// ─── Agent pipeline config ────────────────────────────────────────────────

const PIPELINE = [
  { name: "market_intelligence", label: "Market Intel",    icon: TrendingUp, color: "text-yellow-400",  ring: "ring-yellow-800/40",  bg: "bg-yellow-950/30"  },
  { name: "demand_planning",     label: "Demand Planning", icon: BarChart3,   color: "text-blue-400",    ring: "ring-blue-800/40",    bg: "bg-blue-950/30"    },
  { name: "inventory_manager",   label: "Inventory",       icon: Package,     color: "text-purple-400",  ring: "ring-purple-800/40",  bg: "bg-purple-950/30"  },
  { name: "shipment_analyst",    label: "Freight",         icon: Truck,       color: "text-emerald-400", ring: "ring-emerald-800/40", bg: "bg-emerald-950/30" },
  { name: "coordinator",         label: "Coordinator",     icon: Cpu,         color: "text-gray-200",    ring: "ring-gray-700/40",    bg: "bg-gray-800/30"    },
] as const;

// ─── Derived KPIs from decisions ──────────────────────────────────────────

interface KPIs {
  spikeDetected: boolean;
  spikePct: number | null;
  atRiskCount: number;
  excessCount: number;
  freightSavings: number;
  cascadeComplete: boolean;
  lastRunAt: string | null;
}

function deriveKPIs(decisions: AgentDecision[]): KPIs {
  const latest = (name: string) =>
    decisions.find((d) => d.agent_name === name);

  const demand   = latest("demand_planning");
  const inv      = latest("inventory_manager");
  const freight  = latest("shipment_analyst");
  const coord    = latest("coordinator");

  // demand spike
  let spikeDetected = false;
  let spikePct: number | null = null;
  if (demand) {
    const forecasts = (demand.outputs.forecasts as Array<Record<string, unknown>>) ?? [];
    const hero = forecasts.find((f) => f.spike_detected);
    if (hero) {
      spikeDetected = true;
      spikePct = (hero.spike_magnitude_pct as number) ?? null;
    }
  }

  const atRiskCount   = (inv?.outputs.at_risk_count as number)    ?? 0;
  const excessCount   = (inv?.outputs.excess_count as number)     ?? 0;
  const freightSavings = (freight?.outputs.total_savings_usd as number) ?? 0;
  const cascadeComplete = !!(coord?.outputs.cascade_complete);
  const lastRunAt = coord?.timestamp ?? demand?.timestamp ?? null;

  return { spikeDetected, spikePct, atRiskCount, excessCount, freightSavings, cascadeComplete, lastRunAt };
}

// ─── Sub-components ──────────────────────────────────────────────────────

function KpiCard({
  icon: Icon,
  label,
  value,
  savings,
  sub,
  accent,
  href,
}: {
  icon: React.ElementType;
  label: string;
  value: string | null;
  savings?: number;
  sub?: string;
  accent: string;
  href?: string;
}) {
  const inner = (
    <div className={cn(
      "rounded-xl border border-gray-800 bg-gray-900/60 p-4 transition-colors",
      href && "hover:border-gray-700 hover:bg-gray-900/90 cursor-pointer"
    )}>
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} className={accent} />
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      {savings !== undefined ? (
        <SavingsCounter
          target={savings}
          className={cn("text-2xl font-semibold tabular-nums", accent)}
        />
      ) : (
        <p className={cn("text-2xl font-semibold tabular-nums", accent)}>{value}</p>
      )}
      {sub && <p className="mt-0.5 text-xs text-gray-600">{sub}</p>}
    </div>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}

function AgentStep({
  agent,
  decision,
  index,
  total,
}: {
  agent: (typeof PIPELINE)[number];
  decision: AgentDecision | undefined;
  index: number;
  total: number;
}) {
  const Icon = agent.icon;
  const ran = !!decision;
  const conf = decision ? Math.round(decision.confidence * 100) : null;

  return (
    <div className="flex items-start gap-3">
      {/* Connector line + circle */}
      <div className="flex flex-col items-center gap-0">
        <div
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-full ring-1",
            ran ? cn(agent.bg, agent.ring) : "bg-gray-900 ring-gray-800"
          )}
        >
          <Icon size={14} className={ran ? agent.color : "text-gray-700"} />
        </div>
        {index < total - 1 && (
          <div className={cn("mt-1 h-8 w-px", ran ? "bg-gray-700" : "bg-gray-800/60")} />
        )}
      </div>

      {/* Content */}
      <div className="pb-6 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className={cn("text-sm font-medium", ran ? agent.color : "text-gray-700")}>
            {agent.label}
          </span>
          {ran && conf !== null && (
            <span className="text-xs text-gray-600">{conf}% confidence</span>
          )}
          {!ran && (
            <span className="text-xs text-gray-700">awaiting run</span>
          )}
        </div>
        {decision && (
          <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">
            {decision.summary}
          </p>
        )}
      </div>
    </div>
  );
}

function ActionItem({
  icon: Icon,
  iconClass,
  title,
  body,
  href,
}: {
  icon: React.ElementType;
  iconClass: string;
  title: string;
  body: string;
  href?: string;
}) {
  const inner = (
    <div className={cn(
      "flex items-start gap-3 rounded-lg border border-gray-800 bg-gray-900/40 p-3 transition-colors",
      href && "hover:border-gray-700 hover:bg-gray-900 cursor-pointer"
    )}>
      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-gray-800">
        <Icon size={12} className={iconClass} />
      </div>
      <div>
        <p className="text-sm font-medium text-gray-200">{title}</p>
        <p className="mt-0.5 text-xs text-gray-500 leading-relaxed">{body}</p>
      </div>
    </div>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}

// ─── Page ────────────────────────────────────────────────────────────────

export default function OverviewPage() {
  const [decisions, setDecisions]   = useState<AgentDecision[]>([]);
  const [plan, setPlan]             = useState<PlanSummary | null>(null);
  const [loading, setLoading]       = useState(true);
  const [running, setRunning]       = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [dRes, pRes] = await Promise.all([
        fetch(`${API_URL}/api/decisions`),
        fetch(`${API_URL}/api/replenishment-plan`),
      ]);
      if (dRes.ok) setDecisions(await dRes.json());
      if (pRes.ok) {
        const p = await pRes.json();
        setPlan(p.summary);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  async function runDemo() {
    setRunning(true);
    try {
      await fetch(`${API_URL}/api/trigger/cascade`, { method: "POST" });
      await fetchAll();
    } finally {
      setRunning(false);
    }
  }

  const kpis = deriveKPIs(decisions);
  const agentMap = Object.fromEntries(decisions.map((d) => [d.agent_name, d]));
  const hasData = decisions.length > 0;

  const lastRunDisplay = kpis.lastRunAt
    ? new Date(kpis.lastRunAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Overview</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Diamond Foods · Week 47 supply chain status
            {lastRunDisplay && (
              <span className="ml-2 text-gray-700">Last cascade: {lastRunDisplay}</span>
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={fetchAll}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-gray-800 bg-gray-900 px-3 py-1.5 text-sm text-gray-400 transition-colors hover:bg-gray-800 disabled:opacity-40"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          <button
            onClick={runDemo}
            disabled={running || loading}
            className={cn(
              "flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-900",
              "px-3 py-1.5 text-sm font-medium text-gray-200 transition-colors",
              "hover:border-gray-600 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {running
              ? <Loader2 size={13} className="animate-spin text-gray-400" />
              : <Play size={13} className="text-blue-400" />}
            {running ? "Running…" : "Run Demo"}
          </button>
        </div>
      </div>

      {/* Demand spike alert banner */}
      {hasData && kpis.spikeDetected && (
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-yellow-900/50 bg-yellow-950/20 px-5 py-3">
          <Zap size={16} className="shrink-0 text-yellow-400" />
          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium text-yellow-300">
              Demand spike detected on SKU-4471
            </span>
            <span className="ml-2 text-sm text-yellow-600">
              {kpis.spikePct !== null ? `${kpis.spikePct.toFixed(0)}% of baseline` : "above threshold"} · Holiday Mixed Nuts · Thanksgiving promo active
            </span>
          </div>
          <Link
            href="/activity"
            className="shrink-0 text-xs text-yellow-600 hover:text-yellow-400 transition-colors"
          >
            View decisions →
          </Link>
        </div>
      )}

      {/* Empty state */}
      {!hasData && !loading && (
        <div className="mb-8 flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-800 py-20 text-center">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-900 ring-1 ring-gray-800">
            <Play size={20} className="text-blue-400 ml-0.5" />
          </div>
          <p className="text-sm font-medium text-gray-200">No data yet</p>
          <p className="mt-1 text-xs text-gray-600 max-w-xs">
            Run the demo to trigger the full 5-agent cascade and populate this dashboard.
          </p>
          <button
            onClick={runDemo}
            disabled={running}
            className="mt-5 flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
          >
            {running ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
            {running ? "Running cascade…" : "Run Demo"}
          </button>
        </div>
      )}

      {/* KPI grid */}
      {hasData && (
        <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard
            icon={Zap}
            label="Demand Spike"
            value={kpis.spikePct !== null ? `${kpis.spikePct.toFixed(0)}%` : "—"}
            sub="SKU-4471 vs baseline"
            accent={kpis.spikeDetected ? "text-yellow-400" : "text-gray-400"}
            href="/activity"
          />
          <KpiCard
            icon={AlertTriangle}
            label="At-Risk SKUs"
            value={String(kpis.atRiskCount)}
            sub={`${kpis.excessCount} SKU${kpis.excessCount !== 1 ? "s" : ""} excess`}
            accent={kpis.atRiskCount > 0 ? "text-red-400" : "text-emerald-400"}
            href="/plan"
          />
          <KpiCard
            icon={DollarSign}
            label="Freight Savings"
            value={null}
            savings={kpis.freightSavings}
            sub="Gulf Coast consolidation"
            accent={kpis.freightSavings > 0 ? "text-emerald-400" : "text-gray-400"}
            href="/activity"
          />
          <KpiCard
            icon={Package}
            label="POs Pending"
            value={plan ? String(plan.total_orders) : "—"}
            sub={plan ? `$${plan.total_estimated_cost_usd.toLocaleString()} est. value` : "run cascade"}
            accent="text-blue-400"
            href="/plan"
          />
        </div>
      )}

      {/* Two-column body */}
      {hasData && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Agent pipeline */}
          <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
            <h2 className="mb-5 text-sm font-medium text-gray-300">Agent Pipeline</h2>
            <div>
              {PIPELINE.map((agent, i) => (
                <AgentStep
                  key={agent.name}
                  agent={agent}
                  decision={agentMap[agent.name]}
                  index={i}
                  total={PIPELINE.length}
                />
              ))}
            </div>
            {kpis.cascadeComplete && (
              <div className="mt-1 flex items-center gap-1.5 text-xs text-emerald-500">
                <CheckCircle2 size={12} />
                Cascade complete
              </div>
            )}
          </div>

          {/* Action items */}
          <div className="rounded-xl border border-gray-800 bg-gray-900/40 p-5">
            <h2 className="mb-4 text-sm font-medium text-gray-300">Action Items</h2>
            <div className="flex flex-col gap-2">
              {kpis.atRiskCount > 0 && (
                <ActionItem
                  icon={AlertTriangle}
                  iconClass="text-red-400"
                  title={`${kpis.atRiskCount} SKU${kpis.atRiskCount !== 1 ? "s" : ""} need immediate replenishment`}
                  body="SKU-4471 (Holiday Mixed Nuts) has under 3 days of supply. Emergency PO required."
                  href="/plan"
                />
              )}
              {kpis.freightSavings > 0 && (
                <ActionItem
                  icon={DollarSign}
                  iconClass="text-emerald-400"
                  title={`$${kpis.freightSavings.toLocaleString()} freight savings available`}
                  body="Consolidate SHIP-1001 and SHIP-1002 from Gulf Coast truck to intermodal. +2 days transit."
                  href="/activity"
                />
              )}
              {kpis.spikeDetected && (
                <ActionItem
                  icon={Zap}
                  iconClass="text-yellow-400"
                  title="Demand spike — Thanksgiving promo active"
                  body="Week 47 seasonal index 2.40 × +120% promo lift on SKU-4471. 7-day forecast: 3,500+ units."
                  href="/activity"
                />
              )}
              {kpis.excessCount > 0 && (
                <ActionItem
                  icon={TrendingUp}
                  iconClass="text-orange-400"
                  title={`${kpis.excessCount} SKU${kpis.excessCount !== 1 ? "s" : ""} with excess inventory`}
                  body="SKU-1099 (Sunflower Seeds) exceeds 14-day cover. Reduce inbound orders to free working capital."
                  href="/plan"
                />
              )}
              {!kpis.atRiskCount && !kpis.freightSavings && !kpis.spikeDetected && (
                <div className="flex items-center gap-2 rounded-lg border border-emerald-900/40 bg-emerald-950/20 px-4 py-3 text-sm text-emerald-400">
                  <CheckCircle2 size={14} />
                  All systems nominal. No actions required.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
