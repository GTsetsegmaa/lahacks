# Market Intelligence Agent

Scans external market signals — fuel surcharges, weather events, seasonal indices — and surfaces the most urgent findings for the SupplyMind supply chain orchestration system.

## What it does

- Reads active market signals from the last 24 hours
- Detects fuel surcharge spikes on key freight lanes
- Flags seasonal demand index peaks (Week 47 = 2.40×, annual high)
- Returns a structured `MarketIntelResponse` to the coordinator

## Part of SupplyMind

This is one of four specialist agents in the SupplyMind multi-agent system. It is dispatched by the **SupplyMind Coordinator** as Stage 1 of the cascade and feeds its findings downstream to Demand Planning and Shipment Analyst.
