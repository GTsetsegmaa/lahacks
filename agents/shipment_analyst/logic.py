"""Shipment Analyst — pure computation, no uAgents dependency."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.contracts import AgentDecision, FreightRecommendation
from agents.common.llm_client import generate_reasoning, query_asi1

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "shared" / "mock_data"

# Demo-locked numbers
REROUTED_SHIPMENTS = 2
GULF_COAST_LANE = "Gulf Coast-Midwest"


def _load(filename: str) -> list:
    return json.loads((DATA_DIR / filename).read_text())


async def run_freight_analysis(
    inventory_flags: list[dict],
    market_signals: list[dict],
    ctx=None,
) -> AgentDecision:
    rates = _load("freight_rates.json")

    has_fuel_spike = any(
        s.get("signal_type") == "fuel_surcharge_spike" for s in market_signals
    )

    # Find the two Gulf Coast rates
    truck_rate = next(
        (r for r in rates if r["lane"] == GULF_COAST_LANE and r["mode"] == "truck"), None
    )
    intermodal_rate = next(
        (r for r in rates if r["lane"] == GULF_COAST_LANE and r["mode"] == "intermodal"), None
    )

    recommendations: list[dict] = []
    total_savings = 0.0

    if has_fuel_spike and truck_rate and intermodal_rate:
        truck_cost = truck_rate["base_rate_usd"] * (1 + truck_rate["fuel_surcharge_pct"])
        intermodal_cost = intermodal_rate["base_rate_usd"] * (
            1 + intermodal_rate["fuel_surcharge_pct"]
        )
        per_shipment_savings = truck_cost - intermodal_cost
        total_savings = round(per_shipment_savings * REROUTED_SHIPMENTS, 2)

        for i in range(REROUTED_SHIPMENTS):
            recommendations.append(
                FreightRecommendation(
                    original_lane=GULF_COAST_LANE,
                    original_mode="truck",
                    original_cost_usd=round(truck_cost, 2),
                    recommended_lane=GULF_COAST_LANE,
                    recommended_mode="intermodal",
                    recommended_cost_usd=round(intermodal_cost, 2),
                    savings_usd=round(per_shipment_savings, 2),
                    reason=(
                        f"Fuel surcharge spike (+18%) on Gulf Coast truck lane. "
                        f"Intermodal alternative saves ${per_shipment_savings:,.2f}/shipment "
                        f"at +{intermodal_rate['transit_days'] - truck_rate['transit_days']} days transit."
                    ),
                    affected_shipment_ids=[f"SHIP-{1001 + i}"],
                ).model_dump()
            )

    at_risk_count = sum(1 for f in inventory_flags if f.get("flag_type") == "at_risk")

    if recommendations:
        summary = (
            f"Rerouted {REROUTED_SHIPMENTS} Gulf Coast shipment(s) to intermodal, "
            f"saving ${total_savings:,.0f}. {at_risk_count} at-risk SKU(s) flagged for expedite."
        )
    else:
        summary = f"No freight optimisations required. {at_risk_count} at-risk SKU(s) monitored."

    prompt = (
        "You are a logistics analyst for Diamond Foods. Write a 2-3 sentence reasoning "
        "for this freight optimisation decision for a supply chain dashboard activity log.\n\n"
        f"Fuel surcharge spike (+18%) active on Gulf Coast-Midwest truck lane.\n"
        f"Rerouted {REROUTED_SHIPMENTS} shipments to intermodal (FR-002), "
        f"saving ${total_savings:,.0f} total.\n"
        f"Transit time increases by 2 days (3→5 days) — acceptable given advance notice.\n\n"
        "Be precise and highlight the savings. Do not use bullet points."
    )
    reasoning = await query_asi1(ctx, prompt) if ctx else generate_reasoning(prompt)

    return AgentDecision(
        agent_name="shipment_analyst",
        decision_type="freight_recommendation",
        summary=summary,
        reasoning=reasoning,
        confidence=0.91,
        inputs_considered=[
            f"freight_rates.json ({len(rates)} lanes)",
            f"market_signals ({len(market_signals)} active, fuel spike={'yes' if has_fuel_spike else 'no'})",
            f"inventory_flags ({at_risk_count} at-risk SKUs)",
        ],
        outputs={
            "recommendations": recommendations,
            "total_savings_usd": total_savings,
            "rerouted_count": len(recommendations),
            "has_fuel_spike": has_fuel_spike,
        },
        timestamp=datetime.now(timezone.utc),
        downstream_targets=["coordinator"],
    )
