"""SupplyMind FastAPI backend — receives AgentDecisions, broadcasts via SSE."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shared.contracts import AgentDecision

app = FastAPI(title="SupplyMind API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store (replaced by MongoDB when MONGODB_URI is set — future task)
_decisions: list[AgentDecision] = []
_subscribers: list[asyncio.Queue] = []


async def _broadcast(payload: str) -> None:
    for q in _subscribers:
        await q.put(payload)


@app.post("/api/decisions", status_code=201)
async def post_decision(decision: AgentDecision) -> dict:
    _decisions.append(decision)
    await _broadcast(decision.model_dump_json())
    return {"status": "accepted", "total": len(_decisions)}


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/decisions")
async def get_decisions() -> list[AgentDecision]:
    return _decisions


@app.get("/api/stream")
async def stream_decisions(request: Request) -> EventSourceResponse:
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.append(queue)

    async def generator() -> AsyncGenerator[dict, None]:
        try:
            # Replay all stored decisions to new subscriber
            for d in _decisions:
                yield {"data": d.model_dump_json()}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {"data": payload}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}  # keep-alive
        finally:
            _subscribers.remove(queue)

    return EventSourceResponse(generator())


# ---------------------------------------------------------------------------
# HTTP fallback trigger — "Run Demo" path (PROJECT.md hard rule 7)
# Also used by agents/trigger_demand.py when uAgent discovery is unavailable
# ---------------------------------------------------------------------------
@app.post("/api/trigger/demand", status_code=202)
async def trigger_demand() -> dict:
    """Invoke demand planning logic directly and post the decision."""
    from agents.demand_planning.logic import run_demand_planning  # lazy import

    decision = run_demand_planning()
    _decisions.append(decision)
    await _broadcast(decision.model_dump_json())
    return {"status": "triggered", "summary": decision.summary}


@app.post("/api/trigger/cascade", status_code=202)
async def trigger_cascade() -> dict:
    """Run the full 4-agent cascade sequentially and post all decisions."""
    import json

    from agents.demand_planning.logic import run_demand_planning
    from agents.inventory_manager.logic import run_inventory_assessment
    from agents.market_intelligence.logic import run_market_intelligence
    from agents.shipment_analyst.logic import run_freight_analysis
    from shared.contracts import AgentDecision

    # Stage 1: Market Intelligence
    market_decision = run_market_intelligence()
    _decisions.append(market_decision)
    await _broadcast(market_decision.model_dump_json())

    # Stage 2: Demand Planning
    demand_decision = run_demand_planning()
    _decisions.append(demand_decision)
    await _broadcast(demand_decision.model_dump_json())

    # Stage 3: Inventory Assessment
    inventory_decision = run_inventory_assessment(demand_decision.model_dump())
    _decisions.append(inventory_decision)
    await _broadcast(inventory_decision.model_dump_json())

    # Stage 4: Freight Analysis
    market_outputs = market_decision.outputs
    active_signals = market_outputs.get("active_signals", [])
    flags = inventory_decision.outputs.get("flags", [])
    freight_decision = run_freight_analysis(flags, active_signals)
    _decisions.append(freight_decision)
    await _broadcast(freight_decision.model_dump_json())

    # Stage 5: Coordinator synthesis
    at_risk = inventory_decision.outputs.get("at_risk_count", 0)
    savings = freight_decision.outputs.get("total_savings_usd", 0.0)
    rerouted = freight_decision.outputs.get("rerouted_count", 0)

    synthesis = AgentDecision(
        agent_name="coordinator",
        decision_type="synthesis",
        summary=(
            f"Full cascade complete: 340% demand spike on SKU-4471, "
            f"{at_risk} at-risk SKUs, ${savings:,.0f} freight savings."
        ),
        reasoning=(
            f"SupplyMind completed a full 4-agent analysis for Diamond Foods Week 47. "
            f"SKU-4471 (Holiday Mixed Nuts) shows a 340% demand spike driven by Thanksgiving "
            f"promotions. {at_risk} SKUs are at stockout risk and require immediate replenishment. "
            f"Rerouting {rerouted} Gulf Coast shipments from truck to intermodal saves ${savings:,.0f}."
        ),
        confidence=0.93,
        inputs_considered=[
            "market_intelligence decision",
            "demand_planning decision",
            "inventory_manager decision",
            "shipment_analyst decision",
        ],
        outputs={
            "cascade_complete": True,
            "at_risk_count": at_risk,
            "excess_count": inventory_decision.outputs.get("excess_count", 0),
            "total_savings_usd": savings,
            "rerouted_count": rerouted,
        },
        timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        downstream_targets=[],
    )
    _decisions.append(synthesis)
    await _broadcast(synthesis.model_dump_json())

    return {
        "status": "cascade_complete",
        "stages": 5,
        "at_risk_count": at_risk,
        "total_savings_usd": savings,
        "summary": synthesis.summary,
    }


# ---------------------------------------------------------------------------
# Demo Mode trigger — seeded reasoning, 3 s pacing between agents
# ---------------------------------------------------------------------------

_DEMO_DECISIONS = [
    {
        "agent_name": "market_intelligence",
        "decision_type": "market_signal",
        "summary": "18% fuel surcharge spike on Gulf Coast-Midwest truck lane. Week 47 seasonal index at 2.40 — annual peak.",
        "reasoning": (
            "External price indices show an 18% fuel surcharge spike on the Gulf Coast-Midwest "
            "truck corridor effective this week, driven by refinery constraints in Houston. "
            "Two active Thanksgiving promotional campaigns are amplifying inbound freight demand. "
            "The seasonal index for Week 47 sits at 2.40 — the highest of the year for Diamond Foods SKUs."
        ),
        "confidence": 0.94,
        "inputs_considered": ["external_signals.json (fuel_surcharge_spike, weather_clear)", "seasonal_index.json (week 47: 2.40)", "promo_calendar.json (2 active promos)"],
        "outputs": {"active_signals": [{"signal_type": "fuel_surcharge_spike", "affected_lane": "Gulf Coast-Midwest", "magnitude": 0.18, "description": "Fuel surcharge +18% on Gulf Coast truck lane"}], "has_fuel_spike": True, "affected_lanes": ["Gulf Coast-Midwest"]},
        "downstream_targets": ["demand_planning"],
    },
    {
        "agent_name": "demand_planning",
        "decision_type": "demand_forecast",
        "summary": "SKU-4471 demand spike detected at 340% of baseline (3.4x normal). 7-day forecast generated for 12 SKUs.",
        "reasoning": (
            "SKU-4471 (Diamond Foods Holiday Mixed Nuts, 16oz) has crossed the 300% spike threshold: "
            "the recent 7-day average is 510 units/day against a 90-day baseline of 150 units/day — "
            "a 340% lift. The Thanksgiving promo overlay adds a further 120% demand lift, yielding a "
            "7-day forecast of 3,570 units. Immediate replenishment action is required to avoid "
            "stockout by day 3."
        ),
        "confidence": 0.87,
        "inputs_considered": ["historical_shipments.json (90 days)", "seasonal_index.json (week 47 index: 2.40)", "promo_calendar.json (SKU-4471 Thanksgiving promo, +120%)"],
        "outputs": {
            "forecasts": [
                {"sku_id": "SKU-4471", "forecast_period_days": 7, "units_per_day": [504.0, 514.1, 524.2, 534.3, 544.4, 554.5, 564.6], "total_units": 3739.1, "spike_detected": True, "spike_magnitude_pct": 340.0, "confidence": 0.87, "seasonal_index_applied": True, "promo_overlay_applied": True},
                {"sku_id": "SKU-2103", "forecast_period_days": 7, "units_per_day": [28.0, 28.6, 29.1, 29.7, 30.2, 30.8, 31.3], "total_units": 207.7, "spike_detected": False, "spike_magnitude_pct": None, "confidence": 0.72, "seasonal_index_applied": True, "promo_overlay_applied": False},
                {"sku_id": "SKU-3892", "forecast_period_days": 7, "units_per_day": [36.0, 36.7, 37.4, 38.1, 38.9, 39.6, 40.3], "total_units": 267.0, "spike_detected": False, "spike_magnitude_pct": None, "confidence": 0.72, "seasonal_index_applied": True, "promo_overlay_applied": False},
            ]
        },
        "downstream_targets": ["inventory_manager"],
    },
    {
        "agent_name": "inventory_manager",
        "decision_type": "inventory_flag",
        "summary": "3 SKU(s) at stockout risk, 1 SKU(s) with excess inventory. Immediate replenishment required for SKU-2103, SKU-3892, SKU-4471.",
        "reasoning": (
            "Three SKUs are at acute stockout risk: SKU-4471 has 2.1 days of supply at current "
            "spike demand, SKU-2103 has 3.4 days, and SKU-3892 has 4.8 days. Combined, these "
            "require an emergency inbound of approximately 5,200 units within 48 hours to restore "
            "a 7-day cover position. One SKU (SKU-1099, Sunflower Seeds) is in excess by 1,600 "
            "units — reducing inbound will free warehouse capacity for the emergency replenishment."
        ),
        "confidence": 0.92,
        "inputs_considered": ["inventory.json (12 lots)", "demand_planning decision (3 SKU forecasts)"],
        "outputs": {
            "flags": [
                {"sku_id": "SKU-4471", "warehouse_id": "Warehouse-7", "flag_type": "at_risk", "current_stock": 1071, "forecast_demand": 3739.1, "days_of_supply": 2.1, "recommended_action": "Replenish SKU-4471: order 6407 units immediately", "urgency": "high"},
                {"sku_id": "SKU-2103", "warehouse_id": "Warehouse-7", "flag_type": "at_risk", "current_stock": 237, "forecast_demand": 207.7, "days_of_supply": 3.4, "recommended_action": "Replenish SKU-2103: order 178 units immediately", "urgency": "high"},
                {"sku_id": "SKU-3892", "warehouse_id": "Warehouse-7", "flag_type": "at_risk", "current_stock": 314, "forecast_demand": 267.0, "days_of_supply": 4.8, "recommended_action": "Replenish SKU-3892: order 220 units immediately", "urgency": "medium"},
                {"sku_id": "SKU-1099", "warehouse_id": "WH-3", "flag_type": "excess", "current_stock": 2225, "forecast_demand": 207.0, "days_of_supply": 75.2, "recommended_action": "Reduce inbound for SKU-1099: 1825 units above 14-day cover", "urgency": "low"},
            ],
            "at_risk_count": 3,
            "excess_count": 1,
            "at_risk_skus": ["SKU-4471", "SKU-2103", "SKU-3892"],
            "excess_skus": ["SKU-1099"],
        },
        "downstream_targets": ["shipment_analyst"],
    },
    {
        "agent_name": "shipment_analyst",
        "decision_type": "freight_recommendation",
        "summary": "Rerouted 2 Gulf Coast shipment(s) to intermodal, saving $3,421. 3 at-risk SKU(s) flagged for expedite.",
        "reasoning": (
            "Two open purchase orders bound for the same Gulf Coast DC are currently routed via "
            "truck at $3,540 per shipment. Switching both to intermodal via FR-002 at $1,830 "
            "per shipment saves $3,421 in total freight cost with only a 2-day transit extension "
            "— well within the available lead time window. This single consolidation move covers "
            "12% of the emergency replenishment order cost."
        ),
        "confidence": 0.91,
        "inputs_considered": ["freight_rates.json (9 lanes)", "market_signals (1 active, fuel spike=yes)", "inventory_flags (3 at-risk SKUs)"],
        "outputs": {
            "recommendations": [
                {"original_lane": "Gulf Coast-Midwest", "original_mode": "truck", "original_cost_usd": 3540.0, "recommended_lane": "Gulf Coast-Midwest", "recommended_mode": "intermodal", "recommended_cost_usd": 1829.56, "savings_usd": 1710.44, "reason": "Fuel surcharge spike (+18%) on Gulf Coast truck lane. Intermodal saves $1,710.44/shipment at +2 days transit.", "affected_shipment_ids": ["SHIP-1001"]},
                {"original_lane": "Gulf Coast-Midwest", "original_mode": "truck", "original_cost_usd": 3540.0, "recommended_lane": "Gulf Coast-Midwest", "recommended_mode": "intermodal", "recommended_cost_usd": 1829.56, "savings_usd": 1710.44, "reason": "Fuel surcharge spike (+18%) on Gulf Coast truck lane. Intermodal saves $1,710.44/shipment at +2 days transit.", "affected_shipment_ids": ["SHIP-1002"]},
            ],
            "total_savings_usd": 3420.88,
            "rerouted_count": 2,
            "has_fuel_spike": True,
        },
        "downstream_targets": ["coordinator"],
    },
    {
        "agent_name": "coordinator",
        "decision_type": "synthesis",
        "summary": "Full cascade complete: 340% demand spike on SKU-4471, 3 at-risk SKUs, $3,421 freight savings.",
        "reasoning": (
            "SupplyMind has completed its full 5-agent analysis for Diamond Foods Week 47. "
            "The headline: a 340% demand spike on SKU-4471 (Holiday Mixed Nuts) requires "
            "emergency replenishment within 48 hours, while a freight consolidation move saves "
            "$3,421 — all computed locally on the GX10 with no external API calls. "
            "Three at-risk SKUs are flagged and purchase orders have been pre-staged in the "
            "Replenishment Plan."
        ),
        "confidence": 0.93,
        "inputs_considered": ["market_intelligence decision", "demand_planning decision", "inventory_manager decision", "shipment_analyst decision"],
        "outputs": {"cascade_complete": True, "at_risk_count": 3, "excess_count": 1, "total_savings_usd": 3420.88, "rerouted_count": 2},
        "downstream_targets": [],
    },
]


@app.post("/api/trigger/demo", status_code=202)
async def trigger_demo() -> dict:
    """Demo mode: broadcast seeded decisions with 3-second pacing between agents."""
    import datetime as _dt

    await asyncio.sleep(1)  # brief dramatic pause before first agent fires

    for raw in _DEMO_DECISIONS:
        from shared.contracts import AgentDecision

        decision = AgentDecision(
            **raw,
            timestamp=_dt.datetime.now(_dt.timezone.utc),
        )
        _decisions.append(decision)
        await _broadcast(decision.model_dump_json())
        await asyncio.sleep(3)

    return {"status": "demo_complete", "decisions": len(_DEMO_DECISIONS)}


# ---------------------------------------------------------------------------
# Replenishment Plan — structured purchase orders derived from inventory flags
# ---------------------------------------------------------------------------

_UNIT_COST_BY_CATEGORY: dict[str, float] = {
    "nuts": 12.50,
    "seeds": 8.75,
    "dried fruit": 9.25,
}
_DEFAULT_UNIT_COST = 10.00

_ETA_BY_URGENCY: dict[str, int] = {
    "high": 2,
    "medium": 5,
    "low": 10,
}

_VENDOR_NAMES: dict[str, str] = {
    "V-101": "Pacific Grove Supply Co.",
    "V-142": "Sunbelt Commodities",
    "V-203": "Central Valley Growers",
    "V-317": "Cascade Ag Partners",
    "V-408": "Heartland Nut Co.",
    "V-512": "Western Premium Foods",
}


@app.get("/api/replenishment-plan")
async def get_replenishment_plan() -> dict:
    """Compute purchase orders from current inventory and demand forecast."""
    import json
    import uuid
    from pathlib import Path

    from agents.demand_planning.logic import run_demand_planning
    from agents.inventory_manager.logic import run_inventory_assessment

    data_dir = Path(__file__).resolve().parent.parent / "shared" / "mock_data"

    skus_raw = json.loads((data_dir / "skus.json").read_text())
    sku_map = {s["sku_id"]: s for s in skus_raw}

    prod_raw = json.loads((data_dir / "production.json").read_text())
    sku_vendor: dict[str, str] = {}
    for rec in prod_raw:
        sku_vendor.setdefault(rec["sku_id"], rec["vendor_id"])

    demand_decision = run_demand_planning()
    inventory_decision = run_inventory_assessment(demand_decision.model_dump())

    flags: list[dict] = inventory_decision.outputs.get("flags", [])

    orders: list[dict] = []
    for flag in flags:
        if flag["flag_type"] == "ok":
            continue

        sku_id = flag["sku_id"]
        sku = sku_map.get(sku_id, {})
        category = sku.get("category", "")
        unit_cost = _UNIT_COST_BY_CATEGORY.get(category, _DEFAULT_UNIT_COST)
        vendor_id = sku_vendor.get(sku_id, "V-101")
        eta_days = _ETA_BY_URGENCY.get(flag["urgency"], 5)
        reorder_point = sku.get("reorder_point_units", 1000)
        safety_stock = sku.get("safety_stock_units", 500)

        if flag["flag_type"] == "at_risk":
            reorder_qty = max(
                int(flag["forecast_demand"] * 2) - flag["current_stock"],
                reorder_point - flag["current_stock"],
                0,
            )
        else:  # excess
            daily_rate = flag["forecast_demand"] / 7.0 if flag["forecast_demand"] > 0 else 1.0
            available = flag["current_stock"]
            excess_units = max(int(available - daily_rate * 14), 0)
            reorder_qty = -excess_units  # negative = cancel/reduce inbound

        orders.append({
            "po_number": f"PO-{uuid.uuid4().hex[:6].upper()}",
            "sku_id": sku_id,
            "sku_name": sku.get("name", sku_id),
            "warehouse_id": flag["warehouse_id"],
            "urgency": flag["urgency"],
            "flag_type": flag["flag_type"],
            "current_stock": flag["current_stock"],
            "forecast_demand_7d": flag["forecast_demand"],
            "days_of_supply": flag["days_of_supply"],
            "reorder_qty": reorder_qty,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "estimated_unit_cost_usd": unit_cost,
            "estimated_total_cost_usd": round(abs(reorder_qty) * unit_cost, 2),
            "suggested_vendor": _VENDOR_NAMES.get(vendor_id, vendor_id),
            "vendor_id": vendor_id,
            "eta_days": eta_days,
            "recommended_action": flag["recommended_action"],
        })

    at_risk_orders = [o for o in orders if o["flag_type"] == "at_risk"]
    excess_orders = [o for o in orders if o["flag_type"] == "excess"]
    total_units = sum(o["reorder_qty"] for o in at_risk_orders)
    total_cost = sum(o["estimated_total_cost_usd"] for o in at_risk_orders)
    critical_count = sum(1 for o in at_risk_orders if o["urgency"] == "high")

    return {
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "summary": {
            "critical_orders": critical_count,
            "total_orders": len(at_risk_orders),
            "total_units_to_order": total_units,
            "total_estimated_cost_usd": round(total_cost, 2),
            "excess_skus": len(excess_orders),
        },
        "replenishment_orders": at_risk_orders,
        "excess_orders": excess_orders,
    }
