# SupplyMind Coordinator

An AI-powered supply chain orchestration agent for Diamond Foods built on the Fetch.ai uAgents framework.

## What it does

Send any natural-language supply chain query (e.g. *"Run a full demand and freight analysis for this week"*) and the coordinator will:

1. **Market Intelligence** — scan external signals for fuel surcharges, weather disruptions, and seasonal indices
2. **Demand Planning** — detect SKU-level demand spikes and generate 7-day forecasts
3. **Inventory Assessment** — flag at-risk stockouts and excess inventory lots
4. **Freight Optimisation** — identify shipment consolidation opportunities and rerouting savings
5. **Synthesis** — return a concise plain-English summary of all findings via ASI:One

## How to use

Send a `ChatMessage` (Fetch.ai Chat Protocol) to this agent's address. The agent will reply with a synthesised supply chain briefing once the full cascade completes (~30–60 s).

## Tech stack

- Fetch.ai uAgents + Agentverse mailbox
- ASI-1 cloud inference (primary) / Ollama fallback
- FastAPI backend + Next.js dashboard
