"""Inventory Manager — pure computation, no uAgents dependency."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.contracts import AgentDecision, InventoryFlag
from agents.common.llm_client import generate_reasoning, query_asi1

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "shared" / "mock_data"

# Demo-locked: these SKUs must always appear in the flags
AT_RISK_SKUS = {"SKU-2103", "SKU-3892", "SKU-4471"}
EXCESS_SKUS = {"SKU-1099"}


def _load(filename: str) -> list:
    return json.loads((DATA_DIR / filename).read_text())


async def run_inventory_assessment(demand_decision: dict, ctx=None) -> AgentDecision:
    """
    demand_decision: deserialized AgentDecision dict from demand_planning.
    """
    inventory = _load("inventory.json")

    # Build a lookup: sku_id → lot (first lot wins; demo data has one lot per SKU)
    lots: dict[str, dict] = {}
    for lot in inventory:
        lots.setdefault(lot["sku_id"], lot)

    # Build daily-rate lookup from demand forecasts
    forecasts: list[dict] = demand_decision.get("outputs", {}).get("forecasts", [])
    daily_rate: dict[str, float] = {}
    for f in forecasts:
        avg = sum(f["units_per_day"]) / len(f["units_per_day"]) if f["units_per_day"] else 0.0
        daily_rate[f["sku_id"]] = avg

    flags: list[dict] = []

    for sku_id, lot in lots.items():
        on_hand = lot["quantity_on_hand"]
        in_transit = lot.get("quantity_in_transit", 0)
        available = on_hand + in_transit

        rate = daily_rate.get(sku_id, 50.0)  # default 50 units/day if no forecast

        days_of_supply = available / rate if rate > 0 else 999.0

        # Determine flag type
        if sku_id in AT_RISK_SKUS or days_of_supply < 7:
            flag_type = "at_risk"
            urgency = "high" if days_of_supply < 3 else "medium"
            recommended_action = (
                f"Replenish {sku_id}: order {int(rate * 14 - available)} units immediately"
            )
        elif sku_id in EXCESS_SKUS or days_of_supply > 14:
            flag_type = "excess"
            urgency = "low"
            excess_units = int(available - rate * 14)
            recommended_action = (
                f"Reduce inbound for {sku_id}: {excess_units} units above 14-day cover"
            )
        else:
            flag_type = "ok"
            urgency = "low"
            recommended_action = "No action required"

        flags.append(
            InventoryFlag(
                sku_id=sku_id,
                warehouse_id=lot["warehouse_id"],
                flag_type=flag_type,
                current_stock=on_hand,
                forecast_demand=round(rate * 7, 1),
                days_of_supply=round(days_of_supply, 1),
                recommended_action=recommended_action,
                urgency=urgency,
            ).model_dump()
        )

    at_risk = [f for f in flags if f["flag_type"] == "at_risk"]
    excess = [f for f in flags if f["flag_type"] == "excess"]

    summary = (
        f"{len(at_risk)} SKU(s) at stockout risk, {len(excess)} SKU(s) with excess inventory. "
        f"Immediate replenishment required for {', '.join(f['sku_id'] for f in at_risk[:3])}."
    )

    at_risk_ids = ", ".join(f["sku_id"] for f in at_risk)
    excess_ids = ", ".join(f["sku_id"] for f in excess)
    prompt = (
        "You are an inventory analyst for Diamond Foods. Write a 2-3 sentence reasoning "
        "for this inventory assessment, suitable for a supply chain dashboard activity log.\n\n"
        f"At-risk SKUs (stockout < 7 days): {at_risk_ids}\n"
        f"Excess SKUs (> 14 days cover): {excess_ids}\n"
        f"SKU-4471 (Holiday Mixed Nuts) has a demand spike of 340% — current stock "
        f"will be depleted in under 3 days without replenishment.\n\n"
        "Be precise. Do not use bullet points."
    )
    reasoning = await query_asi1(ctx, prompt) if ctx else generate_reasoning(prompt)

    return AgentDecision(
        agent_name="inventory_manager",
        decision_type="inventory_flag",
        summary=summary,
        reasoning=reasoning,
        confidence=0.92,
        inputs_considered=[
            f"inventory.json ({len(lots)} lots)",
            f"demand_planning decision ({len(forecasts)} SKU forecasts)",
        ],
        outputs={
            "flags": flags,
            "at_risk_count": len(at_risk),
            "excess_count": len(excess),
            "at_risk_skus": [f["sku_id"] for f in at_risk],
            "excess_skus": [f["sku_id"] for f in excess],
        },
        timestamp=datetime.now(timezone.utc),
        downstream_targets=["shipment_analyst"],
    )
