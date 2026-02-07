#!/usr/bin/env python3
"""
Generate history/changelog for automobile.tn new cars data.

Compares current scrape with a previous snapshot to detect:
- Added / removed brands, models, and trims
- Price changes (increases and drops)
- Specification changes (engine, fuel, dimensions, etc.)

Outputs to new_cars_history.json consumed by the history dashboard.
"""

import json
import os
import sys
from datetime import datetime, timezone

CURRENT_FILE = "automobile_tn_new_cars.json"
PREVIOUS_FILE = "automobile_tn_new_cars_previous.json"
HISTORY_FILE = "new_cars_history.json"

# Fields tracked for spec-change detection (price handled separately)
TRACKED_FIELDS = [
    "price_original", "discount_tnd", "has_discount",
    "engine_cc", "cv_fiscal", "cv_din", "torque_nm",
    "top_speed_kmh", "acceleration_0_100",
    "fuel_type", "consumption_mixed", "consumption_city", "consumption_highway",
    "co2_emissions", "fuel_tank_liters",
    "transmission", "gearbox_speeds", "drivetrain",
    "length_mm", "width_mm", "height_mm", "wheelbase_mm",
    "trunk_liters", "weight_kg",
    "body_type", "doors", "seats", "warranty_years",
    "is_electric", "is_hybrid", "battery_kwh", "range_km",
    "is_new", "is_populaire",
]


def load_json(filepath):
    """Load a JSON file; return None when missing or invalid."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, IOError) as exc:
        print(f"Warning: could not load {filepath}: {exc}")
        return None


def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _trim_summary(car):
    """Return a lightweight dict suitable for history storage."""
    return {
        "id": car.get("id", ""),
        "full_name": car.get("full_name", ""),
        "brand": car.get("brand", ""),
        "model": car.get("model", ""),
        "trim": car.get("trim", ""),
        "price_tnd": car.get("price_tnd"),
        "fuel_type": car.get("fuel_type", ""),
        "body_type": car.get("body_type", ""),
        "transmission": car.get("transmission", ""),
        "url": car.get("url", ""),
    }


def generate_diff(previous_data, current_data):
    """Compare previous and current scrape data; return a history entry."""
    prev_cars = {c["id"]: c for c in (previous_data or {}).get("cars", [])}
    curr_cars = {c["id"]: c for c in current_data.get("cars", [])}

    prev_ids = set(prev_cars)
    curr_ids = set(curr_cars)

    added_ids = sorted(curr_ids - prev_ids)
    removed_ids = sorted(prev_ids - curr_ids)
    common_ids = prev_ids & curr_ids

    # ---- trims added / removed ----
    trims_added = [_trim_summary(curr_cars[i]) for i in added_ids]
    trims_removed = [_trim_summary(prev_cars[i]) for i in removed_ids]

    # ---- price changes & spec changes ----
    price_changes = []
    spec_changes = []

    for cid in sorted(common_ids):
        prev = prev_cars[cid]
        curr = curr_cars[cid]

        # Price
        old_price = prev.get("price_tnd")
        new_price = curr.get("price_tnd")
        if old_price and new_price and old_price != new_price:
            delta = new_price - old_price
            price_changes.append({
                "id": cid,
                "full_name": curr.get("full_name", ""),
                "brand": curr.get("brand", ""),
                "model": curr.get("model", ""),
                "trim": curr.get("trim", ""),
                "old_price": old_price,
                "new_price": new_price,
                "change": delta,
                "change_pct": round(delta / old_price * 100, 2) if old_price else 0,
            })

        # Specs
        for field in TRACKED_FIELDS:
            ov = prev.get(field)
            nv = curr.get(field)
            if ov != nv and not (ov is None and nv is None):
                spec_changes.append({
                    "id": cid,
                    "full_name": curr.get("full_name", ""),
                    "brand": curr.get("brand", ""),
                    "model": curr.get("model", ""),
                    "field": field,
                    "old_value": ov,
                    "new_value": nv,
                })

    price_changes.sort(key=lambda x: abs(x["change"]), reverse=True)

    # ---- brand / model level ----
    prev_brands = set(c["brand"] for c in prev_cars.values())
    curr_brands = set(c["brand"] for c in curr_cars.values())
    brands_added = sorted(curr_brands - prev_brands)
    brands_removed = sorted(prev_brands - curr_brands)

    def _model_key(c):
        return f'{c["brand"]}|{c["model"]}'

    prev_models = set(_model_key(c) for c in prev_cars.values())
    curr_models = set(_model_key(c) for c in curr_cars.values())

    models_added = sorted(
        [{"brand": k.split("|")[0], "model": k.split("|")[1]} for k in curr_models - prev_models],
        key=lambda x: (x["brand"], x["model"]),
    )
    models_removed = sorted(
        [{"brand": k.split("|")[0], "model": k.split("|")[1]} for k in prev_models - curr_models],
        key=lambda x: (x["brand"], x["model"]),
    )

    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "previous_scrape": (previous_data or {}).get("scraped_at"),
        "current_scrape": current_data.get("scraped_at", ""),
        "summary": {
            "total_before": len(prev_cars),
            "total_after": len(curr_cars),
            "brands_added": len(brands_added),
            "brands_removed": len(brands_removed),
            "models_added": len(models_added),
            "models_removed": len(models_removed),
            "trims_added": len(trims_added),
            "trims_removed": len(trims_removed),
            "price_changes": len(price_changes),
            "price_drops": sum(1 for p in price_changes if p["change"] < 0),
            "price_increases": sum(1 for p in price_changes if p["change"] > 0),
            "spec_changes": len(spec_changes),
        },
        "changes": {
            "brands_added": brands_added,
            "brands_removed": brands_removed,
            "models_added": models_added,
            "models_removed": models_removed,
            "trims_added": trims_added,
            "trims_removed": trims_removed,
            "price_changes": price_changes,
            "spec_changes": spec_changes,
        },
    }


def main():
    current = load_json(CURRENT_FILE)
    if not current or not current.get("cars"):
        print(f"No valid current data in {CURRENT_FILE}. Skipping history generation.")
        sys.exit(0)

    previous = load_json(PREVIOUS_FILE)

    # Skip when nothing changed (identical scrape timestamp)
    if previous and previous.get("scraped_at") == current.get("scraped_at"):
        print("Current and previous data share the same timestamp. Skipping.")
        sys.exit(0)

    entry = generate_diff(previous, current)

    # Load / initialise history
    history = load_json(HISTORY_FILE) or {"entries": []}

    # Replace today's entry if one already exists
    history["entries"] = [e for e in history["entries"] if e.get("date") != entry["date"]]
    history["entries"].append(entry)
    history["entries"].sort(key=lambda e: e.get("date", ""), reverse=True)

    save_json(history, HISTORY_FILE)

    # Summary
    s = entry["summary"]
    total_changes = s["trims_added"] + s["trims_removed"] + s["price_changes"] + s["spec_changes"]
    print(f"\n{'=' * 60}")
    print(f"  New Cars History \u2014 {entry['date']}")
    print(f"{'=' * 60}")
    print(f"  Catalog : {s['total_before']} \u2192 {s['total_after']} trims")
    print(f"  Brands  : +{s['brands_added']}  -{s['brands_removed']}")
    print(f"  Models  : +{s['models_added']}  -{s['models_removed']}")
    print(f"  Trims   : +{s['trims_added']}  -{s['trims_removed']}")
    print(f"  Prices  : {s['price_changes']} changes "
          f"({s['price_drops']} \u2193, {s['price_increases']} \u2191)")
    print(f"  Specs   : {s['spec_changes']} field changes")
    print(f"  Total   : {total_changes} changes")
    print(f"{'=' * 60}")
    print(f"  Saved to {HISTORY_FILE}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
