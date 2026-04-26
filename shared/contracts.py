"""
Shared Pydantic contracts for SupplyMind.
This is the single source of truth for all data shapes.
NEVER edit without explicit instruction.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------

class SKU(BaseModel):
    sku_id: str
    name: str
    category: str
    unit: str                          # e.g. "case", "lb", "oz"
    shelf_life_days: int
    safety_stock_units: int
    reorder_point_units: int


class InventoryLot(BaseModel):
    lot_id: str
    sku_id: str
    warehouse_id: str
    quantity_on_hand: int
    quantity_in_transit: int
    quantity_wip: int
    expiry_date: datetime | None = None
    last_updated: datetime


class HistoricalShipment(BaseModel):
    shipment_id: str
    sku_id: str
    ship_date: datetime
    units_shipped: int
    origin_warehouse: str
    destination: str
    carrier: str
    lane: str                          # e.g. "Gulf Coast-Midwest"


class ProductionRecord(BaseModel):
    record_id: str
    sku_id: str
    commodity: str                     # e.g. "almonds", "cashews"
    vendor_id: str
    planned_units: int
    actual_units: int
    production_date: datetime
    fill_rate: float                   # 0.0-1.0
    constrained: bool = False


class FreightRate(BaseModel):
    rate_id: str
    lane: str
    mode: str                          # "truck", "intermodal", "rail"
    base_rate_usd: float
    fuel_surcharge_pct: float          # e.g. 0.18 for 18%
    transit_days: int
    carrier: str
    effective_date: datetime


class ExternalSignal(BaseModel):
    signal_id: str
    signal_type: str                   # e.g. "fuel_surcharge_spike", "weather_event"
    affected_lane: str | None = None
    affected_commodity: str | None = None
    magnitude: float | None = None     # e.g. 0.18 for +18%
    description: str
    source: str                        # e.g. "mock_feed"
    published_at: datetime


# ---------------------------------------------------------------------------
# Agent output models (all agents MUST produce AgentDecision)
# ---------------------------------------------------------------------------

class AgentDecision(BaseModel):
    agent_name: str
    decision_type: str                 # "demand_forecast" | "inventory_flag" | "freight_recommendation" | "market_signal" | "synthesis"
    summary: str                       # one-sentence headline
    reasoning: str                     # 2-3 sentence explanation shown in Activity Log
    confidence: float = Field(ge=0.0, le=1.0)
    inputs_considered: list[str]
    outputs: dict[str, Any]
    timestamp: datetime
    downstream_targets: list[str]      # agent names this decision should be sent to next


# ---------------------------------------------------------------------------
# Typed outputs — embedded inside AgentDecision.outputs
# ---------------------------------------------------------------------------

class DemandForecast(BaseModel):
    sku_id: str
    forecast_period_days: int
    units_per_day: list[float]         # length == forecast_period_days
    total_units: float
    spike_detected: bool
    spike_magnitude_pct: float | None = None   # e.g. 340.0 for 340%
    confidence: float = Field(ge=0.0, le=1.0)
    seasonal_index_applied: bool = False
    promo_overlay_applied: bool = False


class InventoryFlag(BaseModel):
    sku_id: str
    warehouse_id: str
    flag_type: str                     # "at_risk" | "excess" | "ok"
    current_stock: int
    forecast_demand: float
    days_of_supply: float
    recommended_action: str            # e.g. "Replenish 5000 units immediately"
    urgency: str                       # "high" | "medium" | "low"


class FreightRecommendation(BaseModel):
    original_lane: str
    original_mode: str
    original_cost_usd: float
    recommended_lane: str
    recommended_mode: str
    recommended_cost_usd: float
    savings_usd: float
    reason: str
    affected_shipment_ids: list[str]
