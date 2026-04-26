"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowDown,
  CheckCircle2,
  DollarSign,
  Loader2,
  Package,
  Play,
  RefreshCw,
  ShoppingCart,
  TrendingDown,
  Warehouse,
} from "lucide-react";
import { cn } from "@/lib/utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Types ──────────────────────────────────────────────────────────────────

type Urgency = "high" | "medium" | "low";
type FlagType = "at_risk" | "excess";

interface ReplenishmentOrder {
  po_number: string;
  sku_id: string;
  sku_name: string;
  warehouse_id: string;
  urgency: Urgency;
  flag_type: FlagType;
  current_stock: number;
  forecast_demand_7d: number;
  days_of_supply: number;
  reorder_qty: number;
  safety_stock: number;
  reorder_point: number;
  estimated_unit_cost_usd: number;
  estimated_total_cost_usd: number;
  suggested_vendor: string;
  vendor_id: string;
  eta_days: number;
  recommended_action: string;
}

interface PlanSummary {
  critical_orders: number;
  total_orders: number;
  total_units_to_order: number;
  total_estimated_cost_usd: number;
  excess_skus: number;
}

interface PlanResponse {
  generated_at: string;
  summary: PlanSummary;
  replenishment_orders: ReplenishmentOrder[];
  excess_orders: ReplenishmentOrder[];
}

// ─── Helpers ────────────────────────────────────────────────────────────────

const URGENCY_CONFIG = {
  high: {
    label: "Critical",
    badge: "bg-red-950 text-red-400 ring-red-800",
    dot: "bg-red-400",
    bar: "bg-red-500",
  },
  medium: {
    label: "Medium",
    badge: "bg-yellow-950 text-yellow-400 ring-yellow-800",
    dot: "bg-yellow-400",
    bar: "bg-yellow-500",
  },
  low: {
    label: "Low",
    badge: "bg-gray-800 text-gray-400 ring-gray-700",
    dot: "bg-gray-400",
    bar: "bg-gray-500",
  },
};

function fmt(n: number, decimals = 0) {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function DaysBar({ days, max = 30 }: { days: number; max?: number }) {
  const pct = Math.min((days / max) * 100, 100);
  const color =
    days < 3 ? "bg-red-500" : days < 7 ? "bg-yellow-500" : "bg-emerald-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-800">
        <div className={cn("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className={cn("text-xs tabular-nums", days < 3 ? "text-red-400" : days < 7 ? "text-yellow-400" : "text-gray-400")}>
        {fmt(days, 1)}d
      </span>
    </div>
  );
}

function UrgencyBadge({ urgency }: { urgency: Urgency }) {
  const cfg = URGENCY_CONFIG[urgency];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset", cfg.badge)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", cfg.dot)} />
      {cfg.label}
    </span>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} className={accent ?? "text-gray-500"} />
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className={cn("text-2xl font-semibold tabular-nums", accent ?? "text-white")}>
        {value}
      </p>
      {sub && <p className="mt-0.5 text-xs text-gray-600">{sub}</p>}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function PlanPage() {
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPlan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/replenishment-plan`);
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      setPlan(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load plan");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPlan(); }, [fetchPlan]);

  async function generatePlan() {
    setGenerating(true);
    try {
      await fetch(`${API_URL}/api/trigger/cascade`, { method: "POST" });
      await fetchPlan();
    } finally {
      setGenerating(false);
    }
  }

  const generatedAt = plan
    ? new Date(plan.generated_at).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Replenishment Plan</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            AI-generated purchase orders · Diamond Foods · Week 47
            {generatedAt && (
              <span className="ml-2 text-gray-700">Updated {generatedAt}</span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchPlan}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-lg border border-gray-800 bg-gray-900 px-3 py-1.5 text-sm text-gray-400 transition-colors hover:bg-gray-800 disabled:opacity-40"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          <button
            onClick={generatePlan}
            disabled={generating || loading}
            className={cn(
              "flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-900",
              "px-3 py-1.5 text-sm font-medium text-gray-200 transition-colors",
              "hover:border-gray-600 hover:bg-gray-800",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {generating
              ? <Loader2 size={13} className="animate-spin text-gray-400" />
              : <Play size={13} className="text-blue-400" />}
            {generating ? "Running cascade…" : "Run Demo"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 rounded-lg border border-red-900/50 bg-red-950/30 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && !plan && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-gray-900/60" />
          ))}
        </div>
      )}

      {plan && (
        <>
          {/* Summary stats */}
          <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard
              icon={AlertTriangle}
              label="Critical Orders"
              value={fmt(plan.summary.critical_orders)}
              sub="urgency: high"
              accent={plan.summary.critical_orders > 0 ? "text-red-400" : "text-emerald-400"}
            />
            <StatCard
              icon={ShoppingCart}
              label="Total Orders"
              value={fmt(plan.summary.total_orders)}
              sub={`${plan.summary.excess_skus} excess SKU${plan.summary.excess_skus !== 1 ? "s" : ""}`}
            />
            <StatCard
              icon={Package}
              label="Units to Order"
              value={fmt(plan.summary.total_units_to_order)}
              sub="7-day horizon"
            />
            <StatCard
              icon={DollarSign}
              label="Est. PO Value"
              value={`$${fmt(plan.summary.total_estimated_cost_usd)}`}
              sub="at current vendor rates"
              accent="text-blue-400"
            />
          </div>

          {/* Replenishment orders table */}
          {plan.replenishment_orders.length > 0 ? (
            <section className="mb-8">
              <h2 className="mb-3 text-sm font-medium text-gray-300">
                Replenishment Orders
                <span className="ml-2 text-xs font-normal text-gray-600">
                  ({plan.replenishment_orders.length} SKU{plan.replenishment_orders.length !== 1 ? "s" : ""})
                </span>
              </h2>

              <div className="overflow-x-auto rounded-xl border border-gray-800">
                <table className="min-w-[720px] w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 bg-gray-900/80">
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">SKU / PO#</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">Urgency</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">Warehouse</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">Stock / Cover</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-gray-500">Order Qty</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-gray-500">Est. Cost</th>
                      <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500">Vendor</th>
                      <th className="px-4 py-2.5 text-right text-xs font-medium text-gray-500">ETA</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800/60">
                    {plan.replenishment_orders.map((order) => (
                      <tr
                        key={order.po_number}
                        className="bg-gray-900/40 transition-colors hover:bg-gray-900/70"
                      >
                        <td className="px-4 py-3">
                          <p className="font-medium text-gray-100 leading-snug">
                            {order.sku_name}
                          </p>
                          <p className="text-xs text-gray-600 font-mono mt-0.5">
                            {order.sku_id} · {order.po_number}
                          </p>
                        </td>
                        <td className="px-4 py-3">
                          <UrgencyBadge urgency={order.urgency} />
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1.5 text-gray-400">
                            <Warehouse size={12} />
                            <span className="text-xs">{order.warehouse_id}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <p className="text-xs text-gray-400 mb-1">
                            {fmt(order.current_stock)} on-hand
                          </p>
                          <DaysBar days={order.days_of_supply} />
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="font-medium text-gray-100 tabular-nums">
                            {fmt(order.reorder_qty)}
                          </span>
                          <p className="text-xs text-gray-600">units</p>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="font-medium text-blue-400 tabular-nums">
                            ${fmt(order.estimated_total_cost_usd)}
                          </span>
                          <p className="text-xs text-gray-600">
                            ${order.estimated_unit_cost_usd.toFixed(2)}/unit
                          </p>
                        </td>
                        <td className="px-4 py-3">
                          <p className="text-xs text-gray-300">{order.suggested_vendor}</p>
                          <p className="text-xs text-gray-600">{order.vendor_id}</p>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-xs font-medium text-gray-300">
                            {order.eta_days}d
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : (
            <div className="mb-8 flex items-center gap-3 rounded-xl border border-emerald-900/40 bg-emerald-950/20 px-5 py-4 text-sm text-emerald-400">
              <CheckCircle2 size={16} />
              All SKUs are within reorder thresholds. No replenishment needed.
            </div>
          )}

          {/* Excess inventory */}
          {plan.excess_orders.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-medium text-gray-300">
                Excess Inventory
                <span className="ml-2 text-xs font-normal text-gray-600">
                  reduce inbound or redirect
                </span>
              </h2>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {plan.excess_orders.map((order) => {
                  const excessUnits = Math.abs(order.reorder_qty);
                  const excessCost = excessUnits * order.estimated_unit_cost_usd;
                  return (
                    <div
                      key={order.po_number}
                      className="rounded-xl border border-gray-800 bg-gray-900/40 p-4"
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div>
                          <p className="text-sm font-medium text-gray-200 leading-snug">
                            {order.sku_name}
                          </p>
                          <p className="text-xs text-gray-600 font-mono mt-0.5">{order.sku_id}</p>
                        </div>
                        <span className="flex items-center gap-1 rounded-full bg-orange-950/60 px-2 py-0.5 text-xs font-medium text-orange-400 ring-1 ring-inset ring-orange-800/60">
                          <TrendingDown size={10} />
                          Excess
                        </span>
                      </div>
                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <p className="text-gray-600">On-hand</p>
                          <p className="text-gray-300 font-medium tabular-nums">{fmt(order.current_stock)}</p>
                        </div>
                        <div>
                          <p className="text-gray-600">Days cover</p>
                          <p className="text-gray-300 font-medium tabular-nums">{fmt(order.days_of_supply, 1)}d</p>
                        </div>
                        <div>
                          <p className="text-gray-600">Cancel / reduce</p>
                          <p className="text-orange-400 font-medium tabular-nums">{fmt(excessUnits)} units</p>
                        </div>
                        <div>
                          <p className="text-gray-600">Capital at risk</p>
                          <p className="text-gray-300 font-medium tabular-nums">${fmt(excessCost)}</p>
                        </div>
                      </div>
                      <div className="mt-3 flex items-start gap-1.5">
                        <ArrowDown size={11} className="mt-0.5 shrink-0 text-gray-600" />
                        <p className="text-xs text-gray-500 leading-relaxed">{order.recommended_action}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
