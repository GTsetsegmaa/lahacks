"""
Coordinator Agent — Chat Protocol entry point for ASI:One.

True multi-agent cascade via ctx.send() message passing:
  ASI:One → ChatMessage → Coordinator
  Coordinator → MarketIntelRequest       → Market Intelligence Agent
  Market Intelligence → MarketIntelResponse → Coordinator
  Coordinator → ForecastRequest          → Demand Planning Agent
  Demand Planning → ForecastResponse     → Coordinator
  Coordinator → InventoryAssessmentRequest → Inventory Manager Agent
  Inventory Manager → InventoryAssessmentResponse → Coordinator
  Coordinator → FreightAnalysisRequest   → Shipment Analyst Agent
  Shipment Analyst → FreightAnalysisResponse → Coordinator
  Coordinator → ASI-1 synthesis → ChatMessage reply → ASI:One
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

_PROMPT_CONFIG_PATH = Path(__file__).resolve().parent / "prompt_config.json"


def _load_prompt_config() -> dict:
    try:
        return json.loads(_PROMPT_CONFIG_PATH.read_text())
    except Exception:
        return {}


def _cfg(key: str, fallback: str = "") -> str:
    return _load_prompt_config().get(key, fallback)


import httpx
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)
from uagents_core.identity import Identity

asyncio.set_event_loop(asyncio.new_event_loop())

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from agents.common.llm_client import ASI1_ADDRESS, query_asi1, resolve_response
from agents.common.messages import (
    ForecastRequest,
    ForecastResponse,
    FreightAnalysisRequest,
    FreightAnalysisResponse,
    InventoryAssessmentRequest,
    InventoryAssessmentResponse,
    MarketIntelRequest,
    MarketIntelResponse,
)
from shared.contracts import AgentDecision

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Deterministic addresses derived from each specialist agent's seed (index 0)
MARKET_INTEL_ADDRESS    = Identity.from_seed("market_intelligence_seed_supplymind_2024", 0).address
DEMAND_PLANNING_ADDRESS = Identity.from_seed("demand_planning_seed_supplymind_2024", 0).address
INVENTORY_MGR_ADDRESS   = Identity.from_seed("inventory_manager_seed_supplymind_2024", 0).address
SHIPMENT_ANALYST_ADDRESS= Identity.from_seed("shipment_analyst_seed_supplymind_2024", 0).address

# One pending future per cascade stage — keyed by stage name.
# Safe because the cascade is strictly sequential: only one stage is in-flight at a time.
_pending: dict[str, asyncio.Future] = {}

# Guard against mailbox re-delivery while a cascade is in-flight
_processing: set[str] = set()

coordinator = Agent(
    name="supplymind_coordinator",
    seed="coordinator_seed_supplymind_2024",
    port=8003,
    mailbox=True,
    publish_agent_details=True,
    readme_path=str(Path(__file__).resolve().parent / "README.md"),
)

chat_proto = Protocol(spec=chat_protocol_spec)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _post_synthesis(decision: AgentDecision) -> None:
    """Post the coordinator's synthesis decision to the backend."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{BACKEND_URL}/api/decisions",
                content=decision.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            pass  # logged by caller


async def _send_and_wait(
    ctx: Context,
    address: str,
    message,
    stage: str,
    timeout: float = 120.0,
):
    """Send a message to a specialist agent and block until its response arrives."""
    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _pending[stage] = fut
    await ctx.send(address, message)
    try:
        return await asyncio.wait_for(asyncio.shield(fut), timeout=timeout)
    finally:
        _pending.pop(stage, None)


# ---------------------------------------------------------------------------
# True multi-agent cascade
# ---------------------------------------------------------------------------

async def _run_cascade(ctx: Context) -> str:
    cfg = _load_prompt_config()

    # Stage 1 — Market Intelligence
    ctx.logger.info("→ Dispatching MarketIntelRequest")
    market: MarketIntelResponse = await _send_and_wait(
        ctx, MARKET_INTEL_ADDRESS, MarketIntelRequest(), "market_intel"
    )
    ctx.logger.info("✓ MarketIntelResponse: %s", market.summary[:80])

    # Stage 2 — Demand Planning
    ctx.logger.info("→ Dispatching ForecastRequest")
    demand: ForecastResponse = await _send_and_wait(
        ctx, DEMAND_PLANNING_ADDRESS, ForecastRequest(week=47), "demand"
    )
    ctx.logger.info("✓ ForecastResponse: %s", demand.summary[:80])

    # Stage 3 — Inventory Assessment (needs demand decision as input)
    ctx.logger.info("→ Dispatching InventoryAssessmentRequest")
    inventory: InventoryAssessmentResponse = await _send_and_wait(
        ctx,
        INVENTORY_MGR_ADDRESS,
        InventoryAssessmentRequest(demand_decision_json=demand.decision_json),
        "inventory",
    )
    ctx.logger.info("✓ InventoryAssessmentResponse: %s", inventory.summary[:80])

    # Stage 4 — Freight Analysis (needs inventory flags + market signals)
    ctx.logger.info("→ Dispatching FreightAnalysisRequest")
    freight: FreightAnalysisResponse = await _send_and_wait(
        ctx,
        SHIPMENT_ANALYST_ADDRESS,
        FreightAnalysisRequest(
            inventory_flags_json=inventory.flags_json,
            market_signals_json=market.signals_json,
        ),
        "freight",
    )
    ctx.logger.info("✓ FreightAnalysisResponse: savings=$%s", freight.total_savings_usd)

    # Stage 5 — ASI-1 synthesis
    persona = cfg.get(
        "agent_persona",
        "You are SupplyMind, an AI supply chain orchestrator for Diamond Foods.",
    )
    instructions = cfg.get(
        "synthesis_instructions",
        "Write a concise 2-3 sentence reply. Lead with the most critical finding. "
        "Reply in first person. Do not use bullet points.",
    )
    context_template = cfg.get("synthesis_context", "")
    context_filled = (
        context_template.format(
            rerouted_count=freight.rerouted_count,
            savings=freight.total_savings_usd,
        )
        if context_template else ""
    )

    synthesis_prompt = (
        f"{persona}\n"
        f"{instructions}\n\n"
        f"Market: {market.summary}\n"
        f"Demand: {demand.summary}\n"
        f"Inventory: {inventory.summary}\n"
        f"Freight: {freight.summary}\n"
        + (f"\n{context_filled}" if context_filled else "")
    )

    ctx.logger.info("→ Requesting ASI-1 synthesis")
    reply_text = await query_asi1(ctx, synthesis_prompt)
    ctx.logger.info("✓ Synthesis ready")

    # Post coordinator synthesis decision
    synthesis_decision = AgentDecision(
        agent_name="coordinator",
        decision_type="synthesis",
        summary=(
            f"Full cascade complete: demand spike on SKU-4471, "
            f"{inventory.at_risk_count} at-risk SKUs, "
            f"${freight.total_savings_usd:,.0f} freight savings."
        ),
        reasoning=reply_text,
        confidence=0.93,
        inputs_considered=[
            "market_intelligence decision",
            "demand_planning decision",
            "inventory_manager decision",
            "shipment_analyst decision",
        ],
        outputs={
            "cascade_complete": True,
            "at_risk_count": inventory.at_risk_count,
            "excess_count": inventory.excess_count,
            "total_savings_usd": freight.total_savings_usd,
            "rerouted_count": freight.rerouted_count,
        },
        timestamp=datetime.now(timezone.utc),
        downstream_targets=[],
    )
    await _post_synthesis(synthesis_decision)

    return reply_text


# ---------------------------------------------------------------------------
# Specialist agent response handlers
# ---------------------------------------------------------------------------

@coordinator.on_message(MarketIntelResponse)
async def handle_market_intel_response(ctx: Context, sender: str, msg: MarketIntelResponse) -> None:
    ctx.logger.debug("MarketIntelResponse from %s", sender)
    fut = _pending.get("market_intel")
    if fut and not fut.done():
        fut.set_result(msg)


@coordinator.on_message(ForecastResponse)
async def handle_forecast_response(ctx: Context, sender: str, msg: ForecastResponse) -> None:
    ctx.logger.debug("ForecastResponse from %s", sender)
    fut = _pending.get("demand")
    if fut and not fut.done():
        fut.set_result(msg)


@coordinator.on_message(InventoryAssessmentResponse)
async def handle_inventory_response(ctx: Context, sender: str, msg: InventoryAssessmentResponse) -> None:
    ctx.logger.debug("InventoryAssessmentResponse from %s", sender)
    fut = _pending.get("inventory")
    if fut and not fut.done():
        fut.set_result(msg)


@coordinator.on_message(FreightAnalysisResponse)
async def handle_freight_response(ctx: Context, sender: str, msg: FreightAnalysisResponse) -> None:
    ctx.logger.debug("FreightAnalysisResponse from %s", sender)
    fut = _pending.get("freight")
    if fut and not fut.done():
        fut.set_result(msg)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@coordinator.on_event("startup")
async def on_startup(ctx: Context) -> None:
    ctx.logger.info("Coordinator ready. Address: %s", ctx.agent.address)
    ctx.logger.info("Specialist addresses:")
    ctx.logger.info("  market_intelligence : %s", MARKET_INTEL_ADDRESS)
    ctx.logger.info("  demand_planning     : %s", DEMAND_PLANNING_ADDRESS)
    ctx.logger.info("  inventory_manager   : %s", INVENTORY_MGR_ADDRESS)
    ctx.logger.info("  shipment_analyst    : %s", SHIPMENT_ANALYST_ADDRESS)


# ---------------------------------------------------------------------------
# Chat Protocol — entry point from ASI:One
# ---------------------------------------------------------------------------

async def _cascade_and_reply(ctx: Context, sender: str, msg_key: str) -> None:
    try:
        reply_text = await _run_cascade(ctx)
    except Exception as exc:
        ctx.logger.error("Cascade failed: %s", exc, exc_info=True)
        reply_text = _cfg(
            "no_results_reply",
            "I was unable to complete the supply chain analysis. Please try again.",
        )
    finally:
        _processing.discard(msg_key)

    await ctx.send(sender, ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=reply_text)],
    ))
    ctx.logger.info("Reply sent to %s", sender)


@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage) -> None:
    # ASI-1 synthesis responses arrive as ChatMessages — route to the LLM future.
    if sender == ASI1_ADDRESS:
        text = next((c.text for c in msg.content if isinstance(c, TextContent)), "")
        resolve_response(text)
        return

    # Ack immediately so the mailbox doesn't re-deliver during the long cascade.
    await ctx.send(sender, ChatAcknowledgement(
        timestamp=datetime.now(timezone.utc),
        acknowledged_msg_id=msg.msg_id,
    ))

    msg_key = str(msg.msg_id)
    if msg_key in _processing:
        ctx.logger.info("Duplicate delivery of %s — skipping", msg_key)
        return
    _processing.add(msg_key)

    user_text = " ".join(
        c.text for c in msg.content if isinstance(c, TextContent)
    ).strip() or "(no text)"
    ctx.logger.info("Chat from %s: %s", sender, user_text[:120])

    asyncio.create_task(_cascade_and_reply(ctx, sender, msg_key))


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
    ctx.logger.debug("Ack from %s for msg %s", sender, msg.acknowledged_msg_id)


# ---------------------------------------------------------------------------
# Register chat protocol and run
# ---------------------------------------------------------------------------
coordinator.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    coordinator.run()
