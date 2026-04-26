# SupplyMind — Project Spec

## What this is
A multi-agent push-based supply chain orchestrator for perishable goods companies (Diamond Foods is the example customer). The system proactively positions inventory ahead of demand using forecasts, production schedules, freight signals, and external market intelligence — instead of reacting to customer orders.

Built for LaHacks 2026, targeting:
- Fetch.ai Agentverse track (primary)
- ASUS Ascent GX10 track (secondary)
- MLH Gemma, MongoDB, ElevenLabs (free side prizes)

## Architecture

### Agents (all built on Fetch.ai uAgents framework, registered on Agentverse)

1. **Coordinator** — implements Chat Protocol, receives natural-language requests via ASI:One, orchestrates the specialist cascade, returns a natural-language summary.
2. **Demand Planning Agent** — reads historical shipments + seasonal index + promo calendar, produces 7-day SKU-level forecast with confidence.
3. **Inventory Manager Agent** — reads stock-on-hand, in-transit, WIP, safety stock; flags at-risk and excess SKUs.
4. **Shipment Analyst Agent** — reads freight rates, fuel surcharge, lane options; recommends mode and routing; calculates cost savings.
5. **Market Intelligence Agent** — reads external signal feed (mock JSON); emits structured signals that downstream agents consume.

The Coordinator runs the cascade in this order: Market Intelligence → Demand Planning → Inventory Manager → Shipment Analyst → synthesis.

### Communication
- Coordinator ↔ User: Chat Protocol via ASI:One
- Coordinator ↔ Specialists: uAgent messages (structured)
- Agents → Dashboard: HTTP POST to FastAPI `/api/decisions`
- Dashboard ← Backend: Server-Sent Events at `/api/stream`

### Stack
- Python 3.11 (agents, backend)
- TypeScript / Next.js 14 App Router (dashboard)
- Fetch.ai uAgents
- FastAPI
- MongoDB Atlas (free tier) — falls back to JSON files if unavailable
- Gemma via Ollama (local LLM, runs on GX10)
- ElevenLabs (voice narration in dashboard)
- Tailwind CSS + shadcn/ui (frontend)
- Docker + docker-compose

## Repo structure
```
supplymind/
  PROJECT.md                  ← this file
  README.md
  docker-compose.yml
  shared/
    contracts.py              ← Pydantic models, NEVER edited unilaterally
    contracts.ts              ← TypeScript mirror of contracts.py
    mock_data/                ← generated synthetic data
      skus.json
      historical_shipments.json
      inventory.json
      production.json
      freight_rates.json
      external_signals.json
      seasonal_index.json
      promo_calendar.json
  agents/
    coordinator/
    demand_planning/
    inventory_manager/
    shipment_analyst/
    market_intelligence/
    common/                   ← shared agent utilities, LLM client, etc.
  backend/
    main.py
    routes/
    services/
  dashboard/
    app/
      activity/page.tsx       ← Activity Log (hero)
      plan/page.tsx           ← Replenishment Plan + Cost Savings
      page.tsx                ← Overview
    components/
    lib/
```

## Demo scenario (the ONLY scenario we build for)

**Setting**: Monday, Week 47 (mid-November). Thanksgiving in 10 days. Diamond Foods has a Thanksgiving promo on mixed nuts. A fuel surcharge spike just hit the news due to a Gulf shipping disruption.

**The trigger**: Judge types into ASI:One: *"Generate this week's replenishment plan"*

**The cascade**:
1. Market Intelligence Agent reads external signals; emits `fuel_surcharge_spike` signal affecting Gulf Coast → Midwest lane (+18%).
2. Demand Planning Agent forecasts 7-day demand; detects 340% spike on SKU-4471 (mixed nuts) due to seasonal index + promo overlay.
3. Inventory Manager Agent flags 3 SKUs at risk of stockout and 1 SKU sitting on excess; identifies redistribution opportunity.
4. Shipment Analyst Agent receives the fuel surcharge signal; re-routes 2 shipments away from Gulf Coast lane, recommends intermodal for 1 shipment; calculates $3,420 in savings.
5. Coordinator synthesizes natural-language response: *"Three risks identified. SKU-4471 needs immediate replenishment of 5,000 units. Three lots at risk of stockout in Warehouse-7. I've re-routed two shipments to avoid the Gulf Coast fuel spike, saving $3,420 this week."*

**Headline numbers (locked, must be consistent everywhere)**:
- Demand spike on SKU-4471: 340%
- SKUs at risk: 3
- SKUs on excess: 1
- Cost savings this week: $3,420
- Lots affected by re-routing: 2

## Demo hooks planted in synthetic data

When generating mock data, MUST include:
- SKU-4471 (Diamond Foods Holiday Mixed Nuts, 16oz): historical shipments showing baseline ~150 units/day, then ramping to 510+ units/day in days 85-90 (the spike).
- SKU-2103, SKU-3892: stock-on-hand below safety stock threshold by Week 47.
- SKU-4471: stock-on-hand at 30% of forecast demand (the at-risk hero SKU).
- SKU-1099: stock-on-hand at 250% of forecast (the excess SKU).
- One commodity (almonds) flagged as constrained in production data.
- One vendor (V-203) with declining fill rate: 95% three months ago → 78% this month.
- Gulf Coast → Midwest lane in freight rates.
- External signal: `fuel_surcharge_spike` for Gulf Coast lane, +18%, dated within last 24h.

## Agent decision contract

Every agent MUST output an `AgentDecision` with these fields:
- `agent_name`: str
- `decision_type`: str (e.g., "demand_forecast", "inventory_flag", "freight_recommendation")
- `summary`: str — one-sentence headline of what was decided
- `reasoning`: str — 2-3 sentence natural-language explanation; this is what judges read in Activity Log
- `confidence`: float (0.0-1.0)
- `inputs_considered`: list[str] — what data the agent looked at
- `outputs`: dict — the structured decision data (varies by agent)
- `timestamp`: datetime
- `downstream_targets`: list[str] — which agents this decision should be sent to next

## Hard rules (do not violate)
1. NEVER edit `shared/contracts.py` without explicit instruction.
2. NEVER add agents beyond the 5 listed.
3. NEVER add dashboard pages beyond the 3 listed.
4. During a demo run, only two external services may be called: the LLM (Gemma via local Ollama on GX10, or a hosted LLM API as fallback) and ElevenLabs for voice narration. All other data (market signals, freight rates, ERP, carrier APIs) must come from static local mock files. The Market Intelligence Agent reads `shared/mock_data/external_signals.json` — not a live API.
5. ALL agent outputs MUST be `AgentDecision` objects.
6. Coordinator response to ASI:One MUST be natural language, not JSON.
7. Dashboard MUST work even if Chat Protocol fails (fallback path: dashboard "Run Demo" button calls FastAPI directly).

## Out of scope (do not build)
- User authentication
- Multi-tenancy
- Real ERP integration
- Bill of materials at component level
- Truckload weight/cube optimization
- Holding cost optimization beyond flat rate
- Customer order windows
- Replenishment Agent as separate agent (folded into Coordinator synthesis)
- Supply Line Optimizer as separate agent (vendor logic folded into Inventory Manager)
- Demand Forecast Charts page
- Shipment Optimizer page
- Inventory Tracker as separate page
