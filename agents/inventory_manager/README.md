# Inventory Manager Agent

Assesses inventory positions across all SKUs, flags stockout risks and excess inventory, and recommends replenishment actions for Diamond Foods.

## What it does

- Compares on-hand + in-transit stock against the demand forecast
- Flags SKUs with less than 7 days of supply as at-risk
- Flags SKUs with more than 14 days of supply as excess
- Calculates recommended replenishment quantities
- Returns a structured `InventoryAssessmentResponse` to the coordinator

## Part of SupplyMind

Stage 3 of the SupplyMind cascade. Receives demand forecast data from the coordinator and passes inventory flags downstream to the Shipment Analyst.
