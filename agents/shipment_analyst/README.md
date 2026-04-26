# Shipment Analyst Agent

Optimises freight routing for Diamond Foods by detecting consolidation opportunities and rerouting shipments away from lanes with active fuel surcharge spikes.

## What it does

- Detects active fuel surcharge spikes on freight lanes (e.g. Gulf Coast-Midwest +18%)
- Compares truck vs intermodal rates and calculates per-shipment savings
- Identifies shipments that can be consolidated or rerouted
- Returns a structured `FreightAnalysisResponse` with savings to the coordinator

## Part of SupplyMind

Stage 4 of the SupplyMind cascade. Receives inventory flags and market signals from the coordinator. The freight savings figure (typically $300–500) is the key demo output.
