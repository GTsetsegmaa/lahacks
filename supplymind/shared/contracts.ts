/**
 * TypeScript mirror of shared/contracts.py.
 * NEVER edit without explicit instruction — keep in sync with contracts.py.
 */

// ---------------------------------------------------------------------------
// Core domain models
// ---------------------------------------------------------------------------

export interface SKU {
  sku_id: string;
  name: string;
  category: string;
  unit: string;
  shelf_life_days: number;
  safety_stock_units: number;
  reorder_point_units: number;
}

export interface InventoryLot {
  lot_id: string;
  sku_id: string;
  warehouse_id: string;
  quantity_on_hand: number;
  quantity_in_transit: number;
  quantity_wip: number;
  expiry_date: string | null;  // ISO 8601
  last_updated: string;        // ISO 8601
}

export interface HistoricalShipment {
  shipment_id: string;
  sku_id: string;
  ship_date: string;           // ISO 8601
  units_shipped: number;
  origin_warehouse: string;
  destination: string;
  carrier: string;
  lane: string;
}

export interface ProductionRecord {
  record_id: string;
  sku_id: string;
  commodity: string;
  vendor_id: string;
  planned_units: number;
  actual_units: number;
  production_date: string;     // ISO 8601
  fill_rate: number;           // 0.0–1.0
  constrained: boolean;
}

export interface FreightRate {
  rate_id: string;
  lane: string;
  mode: string;
  base_rate_usd: number;
  fuel_surcharge_pct: number;
  transit_days: number;
  carrier: string;
  effective_date: string;      // ISO 8601
}

export interface ExternalSignal {
  signal_id: string;
  signal_type: string;
  affected_lane: string | null;
  affected_commodity: string | null;
  magnitude: number | null;
  description: string;
  source: string;
  published_at: string;        // ISO 8601
}

// ---------------------------------------------------------------------------
// Agent output models
// ---------------------------------------------------------------------------

export type DecisionType =
  | "demand_forecast"
  | "inventory_flag"
  | "freight_recommendation"
  | "market_signal"
  | "synthesis";

export interface AgentDecision {
  agent_name: string;
  decision_type: DecisionType;
  summary: string;
  reasoning: string;
  confidence: number;          // 0.0–1.0
  inputs_considered: string[];
  outputs: Record<string, unknown>;
  timestamp: string;           // ISO 8601
  downstream_targets: string[];
}

// ---------------------------------------------------------------------------
// Typed outputs — embedded inside AgentDecision.outputs
// ---------------------------------------------------------------------------

export interface DemandForecast {
  sku_id: string;
  forecast_period_days: number;
  units_per_day: number[];
  total_units: number;
  spike_detected: boolean;
  spike_magnitude_pct: number | null;
  confidence: number;
  seasonal_index_applied: boolean;
  promo_overlay_applied: boolean;
}

export type FlagType = "at_risk" | "excess" | "ok";
export type Urgency = "high" | "medium" | "low";

export interface InventoryFlag {
  sku_id: string;
  warehouse_id: string;
  flag_type: FlagType;
  current_stock: number;
  forecast_demand: number;
  days_of_supply: number;
  recommended_action: string;
  urgency: Urgency;
}

export interface FreightRecommendation {
  original_lane: string;
  original_mode: string;
  original_cost_usd: number;
  recommended_lane: string;
  recommended_mode: string;
  recommended_cost_usd: number;
  savings_usd: number;
  reason: string;
  affected_shipment_ids: string[];
}
