"""Demand Planning Agent — uAgents wrapper around demand_planning/logic.py."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import httpx
from uagents import Agent, Context

# Python 3.14 removed implicit event loop creation; uagents requires one at init time.
asyncio.set_event_loop(asyncio.new_event_loop())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from agents.common.messages import ForecastRequest, ForecastResponse
from agents.demand_planning.logic import run_demand_planning

logger = logging.getLogger(__name__)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

agent = Agent(
    name="demand_planning",
    seed="demand_planning_seed_supplymind_2024",
    port=8001,
    endpoint=["http://localhost:8001/submit"],
)

# Exported so trigger_demand.py can resolve the address without starting a server
AGENT_ADDRESS = agent.address


@agent.on_event("startup")
async def on_startup(ctx: Context) -> None:
    ctx.logger.info("Demand Planning Agent ready. Address: %s", ctx.agent.address)


@agent.on_message(model=ForecastRequest)
async def handle_forecast_request(ctx: Context, sender: str, msg: ForecastRequest) -> None:
    ctx.logger.info("ForecastRequest from %s (week %d)", sender, msg.week)

    decision = run_demand_planning()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{BACKEND_URL}/api/decisions",
                content=decision.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            ctx.logger.info("Decision posted to backend (status %d)", resp.status_code)
        except Exception as exc:  # noqa: BLE001
            ctx.logger.error("Failed to post decision to backend: %s", exc)

    # Extract hero stat for the coordinator's synthesis prompt
    forecasts = decision.outputs.get("forecasts", [])
    hero = next((f for f in forecasts if f["sku_id"] == "SKU-4471" and f["spike_detected"]), None)
    key_finding = (
        f"SKU-4471 demand at {hero['spike_magnitude_pct']:.0f}% of baseline, "
        f"7-day forecast total {hero['total_units']:.0f} units"
        if hero else "No spike detected in this forecast run."
    )

    await ctx.send(sender, ForecastResponse(
        summary=decision.summary,
        key_finding=key_finding,
        decision_json=decision.model_dump_json(),
    ))


if __name__ == "__main__":
    agent.run()
