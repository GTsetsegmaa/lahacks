"""Market Intelligence — reads external_signals.json, filters to last 24h."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.contracts import AgentDecision, ExternalSignal
from agents.common.llm_client import generate_reasoning, query_asi1

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "shared" / "mock_data"

# Anchored to the same Monday as the rest of the mock data
NOW = datetime(2024, 11, 18, 9, 0, 0, tzinfo=timezone.utc)
SIGNAL_WINDOW_HOURS = 24


def _load(filename: str) -> list:
    return json.loads((DATA_DIR / filename).read_text())


async def run_market_intelligence(ctx=None) -> AgentDecision:
    raw_signals = _load("external_signals.json")
    cutoff = NOW - timedelta(hours=SIGNAL_WINDOW_HOURS)

    active = [
        s for s in raw_signals
        if datetime.fromisoformat(s["published_at"]) >= cutoff
    ]

    has_fuel_spike = any(s["signal_type"] == "fuel_surcharge_spike" for s in active)
    affected_lanes = [s["affected_lane"] for s in active if s.get("affected_lane")]

    if has_fuel_spike:
        summary = (
            f"Fuel surcharge spike (+18%) detected on Gulf Coast-Midwest lane. "
            f"{len(active)} signal(s) active in the past 24h."
        )
    else:
        summary = f"{len(active)} active market signal(s) in the past 24h."

    descriptions = [s["description"] for s in active]
    prompt = (
        "You are a market intelligence analyst for a supply chain company. "
        "Write a 2-3 sentence summary of these active signals for a supply chain "
        "dashboard activity log. Be precise and flag the most urgent signal first.\n\n"
        + "\n".join(f"- {d}" for d in descriptions)
    )
    reasoning = await query_asi1(ctx, prompt) if ctx else generate_reasoning(prompt)

    return AgentDecision(
        agent_name="market_intelligence",
        decision_type="market_signal",
        summary=summary,
        reasoning=reasoning,
        confidence=0.95,
        inputs_considered=[
            f"external_signals.json ({len(active)} signals within 24h)",
        ],
        outputs={
            "active_signals": active,
            "has_fuel_spike": has_fuel_spike,
            "affected_lanes": affected_lanes,
            "signal_count": len(active),
        },
        timestamp=datetime.now(timezone.utc),
        downstream_targets=["demand_planning"],
    )
