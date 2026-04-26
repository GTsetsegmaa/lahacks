"""Shipment Analyst Agent."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from uagents import Agent, Context

asyncio.set_event_loop(asyncio.new_event_loop())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from agents.common.messages import FreightAnalysisRequest, FreightAnalysisResponse
from agents.shipment_analyst.logic import run_freight_analysis

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

agent = Agent(
    name="shipment_analyst",
    seed="shipment_analyst_seed_supplymind_2024",
    port=8006,
    endpoint=["http://localhost:8006/submit"],
)

AGENT_ADDRESS = agent.address


@agent.on_event("startup")
async def on_startup(ctx: Context) -> None:
    ctx.logger.info("Shipment Analyst Agent ready. Address: %s", ctx.agent.address)


@agent.on_message(model=FreightAnalysisRequest)
async def handle_request(
    ctx: Context, sender: str, msg: FreightAnalysisRequest
) -> None:
    ctx.logger.info("FreightAnalysisRequest from %s", sender)

    inventory_flags = json.loads(msg.inventory_flags_json)
    market_signals = json.loads(msg.market_signals_json)
    decision = run_freight_analysis(inventory_flags, market_signals)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{BACKEND_URL}/api/decisions",
                content=decision.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            ctx.logger.error("Failed to post to backend: %s", exc)

    outputs = decision.outputs
    recommendations = outputs.get("recommendations", [])
    await ctx.send(
        sender,
        FreightAnalysisResponse(
            summary=decision.summary,
            total_savings_usd=outputs.get("total_savings_usd", 0.0),
            rerouted_count=outputs.get("rerouted_count", 0),
            recommendations_json=json.dumps(recommendations),
            decision_json=decision.model_dump_json(),
        ),
    )


if __name__ == "__main__":
    agent.run()
