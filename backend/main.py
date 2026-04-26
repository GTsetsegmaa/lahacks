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
