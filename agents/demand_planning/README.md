# Demand Planning Agent

Generates 7-day SKU-level demand forecasts for Diamond Foods, detects demand spikes, and applies seasonal and promotional overlays.

## What it does

- Computes 90-day baseline demand per SKU from historical shipments
- Detects spikes when recent 7-day average exceeds baseline by 3× or more
- Applies Week 47 seasonal index (2.40×) and active promotional lifts
- Returns a structured `ForecastResponse` with per-SKU forecasts to the coordinator

## Part of SupplyMind

Stage 2 of the SupplyMind cascade. Receives a trigger from the **SupplyMind Coordinator** and passes its forecast downstream to the Inventory Manager.
