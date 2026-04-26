#!/usr/bin/env python3
"""
Generate synthetic mock data for the SupplyMind demo.
Run from repo root:  python shared/generate_mock_data.py
Requires: pip install faker

Demo hooks are marked  # DEMO HOOK  for easy auditing.
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

OUT = Path(__file__).parent / "mock_data"
OUT.mkdir(exist_ok=True)

# Anchor "now" to Monday of Week 47, 2024 (Nov 18 — Thanksgiving in 10 days)
NOW = datetime(2024, 11, 18, 9, 0, 0, tzinfo=timezone.utc)  # DEMO HOOK
DAY0 = NOW - timedelta(days=90)

WAREHOUSES = ["WH-1", "WH-3", "WH-5", "Warehouse-7", "WH-9"]
CARRIERS = ["FreightX", "SwiftCargo", "MidwestHaul", "CoastalShip", "InterModal Co"]


def iso(dt: datetime) -> str:
    return dt.isoformat()


def jdump(path: Path, data: list | dict) -> None:
    path.write_text(json.dumps(data, indent=2, default=str))
    count = len(data) if isinstance(data, list) else len(data)
    print(f"  wrote {path.name}  ({count} records)")


# =========================================================================
# skus.json
# =========================================================================

DEMO_SKUS: list[dict] = [
    {   # DEMO HOOK — hero SKU, 340% demand spike
        "sku_id": "SKU-4471",
        "name": "Diamond Foods Holiday Mixed Nuts, 16oz",
        "category": "nuts",
        "unit": "case",
        "shelf_life_days": 180,
        "safety_stock_units": 800,
        "reorder_point_units": 1200,
    },
    {   # DEMO HOOK — at-risk SKU (below safety stock)
        "sku_id": "SKU-2103",
        "name": "Diamond Foods Whole Cashews, 8oz",
        "category": "nuts",
        "unit": "case",
        "shelf_life_days": 270,
        "safety_stock_units": 500,
        "reorder_point_units": 750,
    },
    {   # DEMO HOOK — at-risk SKU (below safety stock)
        "sku_id": "SKU-3892",
        "name": "Diamond Foods Sliced Almonds, 6oz",
        "category": "nuts",
        "unit": "case",
        "shelf_life_days": 365,
        "safety_stock_units": 600,
        "reorder_point_units": 900,
    },
    {   # DEMO HOOK — excess SKU (250% of forecast on hand)
        "sku_id": "SKU-1099",
        "name": "Diamond Foods Sunflower Seeds, 32oz",
        "category": "seeds",
        "unit": "case",
        "shelf_life_days": 365,
        "safety_stock_units": 300,
        "reorder_point_units": 450,
    },
]

_CATEGORIES = ["nuts", "seeds", "dried fruit", "trail mix", "crackers"]
_SIZES = ["4oz", "8oz", "12oz", "16oz", "32oz"]
_SUFFIXES = ["Blend", "Mix", "Pack", "Snack", "Deluxe", "Roasted", "Natural"]

_demo_ids = {s["sku_id"] for s in DEMO_SKUS}
skus: list[dict] = list(DEMO_SKUS)
_n = 1000
while len(skus) < 50:
    sid = f"SKU-{_n}"
    if sid not in _demo_ids:
        ss = random.randint(100, 600)
        skus.append({
            "sku_id": sid,
            "name": f"Diamond Foods {fake.word().title()} {random.choice(_SUFFIXES)}, {random.choice(_SIZES)}",
            "category": random.choice(_CATEGORIES),
            "unit": random.choice(["case", "lb", "bag"]),
            "shelf_life_days": random.choice([90, 180, 270, 365]),
            "safety_stock_units": ss,
            "reorder_point_units": int(ss * 1.5),
        })
    _n += 1

jdump(OUT / "skus.json", skus)

# =========================================================================
# historical_shipments.json  —  90 days
# =========================================================================

# Baseline volumes per SKU (units/day, before noise)
_baselines: dict[str, int] = {
    "SKU-4471": 150,   # DEMO HOOK — ramps to 510+ in days 85-90
    "SKU-2103": 80,
    "SKU-3892": 95,
    "SKU-1099": 110,
}
for s in skus:
    if s["sku_id"] not in _baselines:
        _baselines[s["sku_id"]] = random.randint(20, 200)

_LANES = [
    ("WH-1", "Northeast Distribution", "Gulf Coast-Midwest"),
    ("WH-3", "Midwest Hub", "Southeast-Midwest"),
    ("WH-5", "Southwest Center", "Southwest-West Coast"),
    ("Warehouse-7", "Southeast Depot", "Southeast-Northeast"),
    ("WH-9", "West Coast Terminal", "West Coast-Mountain West"),
]

shipments: list[dict] = []
for day_idx in range(90):
    ship_date = DAY0 + timedelta(days=day_idx)
    # Each day, generate one shipment per active SKU (subset for realism)
    active_skus = random.sample(skus, k=random.randint(12, 20))
    for s in active_skus:
        sid = s["sku_id"]
        base = _baselines[sid]

        if sid == "SKU-4471":
            if day_idx < 84:
                # Baseline with mild seasonal ramp
                units = int(base * random.uniform(0.85, 1.15))
            else:
                # DEMO HOOK — spike to 510+ in days 85-90 (day_idx 84-89)
                ramp_factor = 3.4 + (day_idx - 84) * 0.08   # 3.40 → 3.88
                units = int(base * ramp_factor * random.uniform(0.98, 1.02))
        else:
            units = int(base * random.uniform(0.8, 1.2))

        origin, destination, lane = random.choice(_LANES)
        shipments.append({
            "shipment_id": f"SHP-{uuid.uuid4().hex[:8].upper()}",
            "sku_id": sid,
            "ship_date": iso(ship_date),
            "units_shipped": max(1, units),
            "origin_warehouse": origin,
            "destination": destination,
            "carrier": random.choice(CARRIERS),
            "lane": lane,
        })

jdump(OUT / "historical_shipments.json", shipments)

# =========================================================================
# inventory.json
# =========================================================================

# SKU-4471 7-day forecast demand ≈ 510 * 7 = 3,570  →  30% on hand = 1,071
# SKU-2103 safety_stock=500  →  on hand=187 (below threshold)           DEMO HOOK
# SKU-3892 safety_stock=600  →  on hand=234 (below threshold)           DEMO HOOK
# SKU-4471 safety_stock=800  →  on hand=1,071 (below safety stock too)  DEMO HOOK
# SKU-1099 forecast ≈ 110*7=770  →  250% on hand = 1,925                DEMO HOOK

_inventory_overrides: dict[str, dict] = {
    "SKU-4471": {
        "warehouse_id": "Warehouse-7",
        "quantity_on_hand": 1071,    # 30% of 3,570 forecast  # DEMO HOOK
        "quantity_in_transit": 0,
        "quantity_wip": 200,
        "expiry_date": iso(NOW + timedelta(days=90)),
    },
    "SKU-2103": {
        "warehouse_id": "Warehouse-7",
        "quantity_on_hand": 187,     # below safety stock of 500  # DEMO HOOK
        "quantity_in_transit": 50,
        "quantity_wip": 0,
        "expiry_date": iso(NOW + timedelta(days=180)),
    },
    "SKU-3892": {
        "warehouse_id": "Warehouse-7",
        "quantity_on_hand": 234,     # below safety stock of 600  # DEMO HOOK
        "quantity_in_transit": 80,
        "quantity_wip": 0,
        "expiry_date": iso(NOW + timedelta(days=270)),
    },
    "SKU-1099": {
        "warehouse_id": "WH-3",
        "quantity_on_hand": 1925,    # 250% of 770 forecast  # DEMO HOOK
        "quantity_in_transit": 300,
        "quantity_wip": 0,
        "expiry_date": iso(NOW + timedelta(days=300)),
    },
}

lots: list[dict] = []
for s in skus:
    sid = s["sku_id"]
    if sid in _inventory_overrides:
        override = _inventory_overrides[sid]
        lots.append({
            "lot_id": f"LOT-{uuid.uuid4().hex[:8].upper()}",
            "sku_id": sid,
            **override,
            "last_updated": iso(NOW - timedelta(hours=random.randint(1, 6))),
        })
    else:
        ss = s["safety_stock_units"]
        # Healthy stock: 1.0x–2.5x safety stock
        qoh = int(ss * random.uniform(1.0, 2.5))
        lots.append({
            "lot_id": f"LOT-{uuid.uuid4().hex[:8].upper()}",
            "sku_id": sid,
            "warehouse_id": random.choice(WAREHOUSES),
            "quantity_on_hand": qoh,
            "quantity_in_transit": random.randint(0, int(ss * 0.3)),
            "quantity_wip": random.randint(0, int(ss * 0.2)),
            "expiry_date": iso(NOW + timedelta(days=s["shelf_life_days"] // 2)),
            "last_updated": iso(NOW - timedelta(hours=random.randint(1, 12))),
        })

jdump(OUT / "inventory.json", lots)

# =========================================================================
# production.json
# =========================================================================

# V-203 produces almonds; fill rate declines 95% → 78% over 3 months  # DEMO HOOK

_COMMODITIES = ["almonds", "cashews", "mixed nuts", "sunflower seeds", "pecans", "walnuts"]
_VENDORS = ["V-101", "V-142", "V-203", "V-317", "V-408", "V-512"]

# V-203 weekly fill-rate schedule (12 weeks back → now)
_V203_FILL_RATES = [0.95, 0.95, 0.93, 0.92, 0.91, 0.90, 0.88, 0.86, 0.83, 0.81, 0.79, 0.78]

records: list[dict] = []
# V-203 almond records — one per week for 12 weeks        # DEMO HOOK
for week in range(12):
    prod_date = NOW - timedelta(weeks=11 - week)
    fill = _V203_FILL_RATES[week]
    planned = random.randint(800, 1200)
    records.append({
        "record_id": f"PROD-{uuid.uuid4().hex[:8].upper()}",
        "sku_id": "SKU-3892",      # Sliced Almonds uses almonds commodity
        "commodity": "almonds",
        "vendor_id": "V-203",
        "planned_units": planned,
        "actual_units": int(planned * fill),
        "production_date": iso(prod_date),
        "fill_rate": fill,
        "constrained": True,       # DEMO HOOK — almonds flagged constrained
    })

# Other vendors / commodities — filler records
for _ in range(60):
    vendor = random.choice([v for v in _VENDORS if v != "V-203"])
    commodity = random.choice([c for c in _COMMODITIES if c != "almonds"])
    planned = random.randint(200, 1500)
    fill = random.uniform(0.85, 0.99)
    sku = random.choice(skus)
    records.append({
        "record_id": f"PROD-{uuid.uuid4().hex[:8].upper()}",
        "sku_id": sku["sku_id"],
        "commodity": commodity,
        "vendor_id": vendor,
        "planned_units": planned,
        "actual_units": int(planned * fill),
        "production_date": iso(NOW - timedelta(days=random.randint(1, 90))),
        "fill_rate": round(fill, 3),
        "constrained": False,
    })

jdump(OUT / "production.json", records)

# =========================================================================
# freight_rates.json
# =========================================================================

# Gulf Coast → Midwest is the affected lane (+18% fuel surcharge)  # DEMO HOOK

_FREIGHT_LANES: list[dict] = [
    {   # DEMO HOOK — affected lane, truck mode (re-routed away from this)
        "rate_id": "FR-001",
        "lane": "Gulf Coast-Midwest",
        "mode": "truck",
        "base_rate_usd": 2100.0,
        "fuel_surcharge_pct": 0.18,   # DEMO HOOK +18%
        "transit_days": 3,
        "carrier": "FreightX",
        "effective_date": iso(NOW - timedelta(hours=20)),
    },
    {   # Gulf Coast → Midwest intermodal — the recommended alternative
        "rate_id": "FR-002",
        "lane": "Gulf Coast-Midwest",
        "mode": "intermodal",
        "base_rate_usd": 1650.0,
        "fuel_surcharge_pct": 0.06,
        "transit_days": 5,
        "carrier": "InterModal Co",
        "effective_date": iso(NOW - timedelta(days=7)),
    },
    {
        "rate_id": "FR-003",
        "lane": "Southeast-Midwest",
        "mode": "truck",
        "base_rate_usd": 1800.0,
        "fuel_surcharge_pct": 0.07,
        "transit_days": 2,
        "carrier": "MidwestHaul",
        "effective_date": iso(NOW - timedelta(days=3)),
    },
    {
        "rate_id": "FR-004",
        "lane": "Southeast-Northeast",
        "mode": "truck",
        "base_rate_usd": 1950.0,
        "fuel_surcharge_pct": 0.08,
        "transit_days": 2,
        "carrier": "CoastalShip",
        "effective_date": iso(NOW - timedelta(days=5)),
    },
    {
        "rate_id": "FR-005",
        "lane": "Southeast-Northeast",
        "mode": "rail",
        "base_rate_usd": 1400.0,
        "fuel_surcharge_pct": 0.04,
        "transit_days": 4,
        "carrier": "SwiftCargo",
        "effective_date": iso(NOW - timedelta(days=14)),
    },
    {
        "rate_id": "FR-006",
        "lane": "Southwest-West Coast",
        "mode": "truck",
        "base_rate_usd": 2300.0,
        "fuel_surcharge_pct": 0.09,
        "transit_days": 3,
        "carrier": "FreightX",
        "effective_date": iso(NOW - timedelta(days=2)),
    },
    {
        "rate_id": "FR-007",
        "lane": "West Coast-Mountain West",
        "mode": "truck",
        "base_rate_usd": 1700.0,
        "fuel_surcharge_pct": 0.07,
        "transit_days": 2,
        "carrier": "SwiftCargo",
        "effective_date": iso(NOW - timedelta(days=4)),
    },
    {
        "rate_id": "FR-008",
        "lane": "West Coast-Mountain West",
        "mode": "intermodal",
        "base_rate_usd": 1300.0,
        "fuel_surcharge_pct": 0.05,
        "transit_days": 4,
        "carrier": "InterModal Co",
        "effective_date": iso(NOW - timedelta(days=10)),
    },
    {
        "rate_id": "FR-009",
        "lane": "Midwest-Northeast",
        "mode": "truck",
        "base_rate_usd": 1550.0,
        "fuel_surcharge_pct": 0.06,
        "transit_days": 2,
        "carrier": "MidwestHaul",
        "effective_date": iso(NOW - timedelta(days=1)),
    },
]

jdump(OUT / "freight_rates.json", _FREIGHT_LANES)

# =========================================================================
# external_signals.json
# =========================================================================

external_signals = [
    {   # DEMO HOOK — primary trigger for Shipment Analyst re-routing
        "signal_id": "SIG-001",
        "signal_type": "fuel_surcharge_spike",
        "affected_lane": "Gulf Coast-Midwest",
        "affected_commodity": None,
        "magnitude": 0.18,
        "description": "Gulf Coast fuel surcharge spiked +18% due to shipping disruption. Effective immediately for all Gulf Coast outbound lanes.",
        "source": "mock_feed",
        "published_at": iso(NOW - timedelta(hours=6)),  # within last 24h  # DEMO HOOK
    },
    {
        "signal_id": "SIG-002",
        "signal_type": "port_delay",
        "affected_lane": "West Coast-Mountain West",
        "affected_commodity": None,
        "magnitude": None,
        "description": "Port of Long Beach reporting 2-3 day delays on inbound containers due to labor action. West Coast outbound unaffected.",
        "source": "mock_feed",
        "published_at": iso(NOW - timedelta(hours=18)),
    },
    {
        "signal_id": "SIG-003",
        "signal_type": "holiday_demand_alert",
        "affected_lane": None,
        "affected_commodity": "mixed nuts",
        "magnitude": 2.8,
        "description": "Retail scanner data shows mixed nuts category tracking +180% YoY for Thanksgiving week. Analyst consensus expects continued elevation through Week 51.",
        "source": "mock_feed",
        "published_at": iso(NOW - timedelta(hours=30)),
    },
    {
        "signal_id": "SIG-004",
        "signal_type": "commodity_constraint",
        "affected_lane": None,
        "affected_commodity": "almonds",
        "magnitude": None,
        "description": "California almond harvest shortfall estimated at 12% below forecast. Spot prices up 9% week-over-week. Buyers advised to secure forward contracts.",
        "source": "mock_feed",
        "published_at": iso(NOW - timedelta(hours=48)),
    },
]

jdump(OUT / "external_signals.json", external_signals)

# =========================================================================
# seasonal_index.json  — weekly multipliers, weeks 1-52
# =========================================================================

# Peaks: weeks 47-51 (Thanksgiving + Christmas).  Summer trough weeks 26-30.
def _seasonal(week: int) -> float:
    """Simple hand-tuned seasonal curve."""
    # Thanksgiving / Christmas peak
    if week in (47, 48):
        return 2.40
    if week in (49, 50):
        return 2.60
    if week == 51:
        return 2.80   # Christmas run-up peak
    if week == 52:
        return 2.20
    # New Year bump
    if week in (1, 2):
        return 1.40
    # Valentine's / Easter area
    if week in (7, 8):
        return 1.20
    if week in (14, 15, 16):
        return 1.15
    # Memorial Day
    if week in (21, 22):
        return 1.10
    # Summer trough
    if 26 <= week <= 30:
        return 0.80
    # Labor Day
    if week in (35, 36):
        return 1.05
    # Fall ramp-up
    if 40 <= week <= 46:
        return round(1.0 + (week - 40) * 0.08, 2)
    return 1.00

seasonal_index = [
    {"week": w, "index": _seasonal(w)}
    for w in range(1, 53)
]

jdump(OUT / "seasonal_index.json", seasonal_index)

# =========================================================================
# promo_calendar.json
# =========================================================================

promo_calendar = [
    {   # DEMO HOOK — Thanksgiving promo on the hero SKU
        "promo_id": "PROMO-001",
        "sku_id": "SKU-4471",
        "name": "Thanksgiving Holiday Mixed Nuts Feature",
        "week": 47,                                   # DEMO HOOK
        "start_date": "2024-11-18",
        "end_date": "2024-11-28",
        "promo_type": "feature_display",
        "demand_lift_pct": 1.20,                      # +120% on top of seasonal index
        "channels": ["grocery", "club", "online"],
        "notes": "Diamond Foods flagship Thanksgiving SKU. End-cap display at major grocery chains.",
    },
    {
        "promo_id": "PROMO-002",
        "sku_id": "SKU-2103",
        "name": "Holiday Cashew Bundle",
        "week": 48,
        "start_date": "2024-11-25",
        "end_date": "2024-12-02",
        "promo_type": "price_reduction",
        "demand_lift_pct": 0.40,
        "channels": ["grocery", "online"],
        "notes": "Buy-2-get-1 promotion tied to holiday gifting.",
    },
    {
        "promo_id": "PROMO-003",
        "sku_id": "SKU-3892",
        "name": "Holiday Baking Season Almonds",
        "week": 48,
        "start_date": "2024-11-25",
        "end_date": "2024-12-15",
        "promo_type": "digital_coupon",
        "demand_lift_pct": 0.30,
        "channels": ["online", "club"],
        "notes": "Targeted at baking occasion. Digital coupon via loyalty app.",
    },
]

jdump(OUT / "promo_calendar.json", promo_calendar)

# =========================================================================
print(f"\nAll mock data written to {OUT}/")
print(f"Reference 'now': {iso(NOW)}  (Monday, Week 47 — Thanksgiving in 10 days)")
