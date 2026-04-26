"""Shared uAgent message models used across agents."""
import asyncio

# Python 3.14 removed implicit event loop creation; uagents requires one at import time.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from uagents import Model


class ForecastRequest(Model):
    requester: str = "coordinator"
    week: int = 47


class ForecastResponse(Model):
    """Demand Planning → Coordinator."""
    summary: str
    key_finding: str
    decision_json: str    # JSON-serialised AgentDecision


class MarketIntelRequest(Model):
    requester: str = "coordinator"


class MarketIntelResponse(Model):
    """Market Intelligence → Coordinator."""
    summary: str
    has_fuel_spike: bool
    affected_lanes: list[str]
    signals_json: str     # JSON list of active ExternalSignal dicts
    decision_json: str    # JSON-serialised AgentDecision


class InventoryAssessmentRequest(Model):
    """Coordinator → Inventory Manager."""
    demand_decision_json: str   # full AgentDecision from Demand Planning
    requester: str = "coordinator"


class InventoryAssessmentResponse(Model):
    """Inventory Manager → Coordinator."""
    summary: str
    at_risk_count: int
    excess_count: int
    flags_json: str       # JSON list of InventoryFlag dicts
    decision_json: str    # JSON-serialised AgentDecision


class FreightAnalysisRequest(Model):
    """Coordinator → Shipment Analyst."""
    inventory_flags_json: str   # JSON list of InventoryFlag dicts
    market_signals_json: str    # JSON list of active ExternalSignal dicts
    requester: str = "coordinator"


class FreightAnalysisResponse(Model):
    """Shipment Analyst → Coordinator."""
    summary: str
    total_savings_usd: float
    rerouted_count: int
    recommendations_json: str   # JSON list of FreightRecommendation dicts
    decision_json: str          # JSON-serialised AgentDecision
