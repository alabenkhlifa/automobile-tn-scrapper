#!/usr/bin/env python3
"""
Build the compact data files behind the dashboard app (index.html).

Reads the scraper outputs and writes small files under data/:
- dashboard.json      aggregates for every dashboard page + source freshness
- history.json        time series, upserted on every run (one point per day)
- used_listings.json  cleaned 9annas listings, column-packed for the browser
- eu_listings.json    AutoScout24 listings, column-packed
- new_trims.json      automobile.tn new-car trims, column-packed

Usage:
    python build_dashboard_data.py                  # daily run (CI)
    python build_dashboard_data.py --seed-from-git  # rebuild history from git log
"""

import argparse
import json
import os
import re
import statistics
import subprocess
from collections import Counter
from datetime import datetime, timezone

NEW_FILE = "automobile_tn_new_cars.json"
USED_FILE = "9annas_tn_used_cars.json"
EU_FILE = "autoscout24_all.json"
CATALOG_HISTORY_FILE = "new_cars_history.json"
OUT_DIR = "data"
HISTORY_FILE = os.path.join(OUT_DIR, "history.json")

# 9annas is user-generated: keep only plausible asking prices and years
USED_PRICE_MIN, USED_PRICE_MAX = 3_000, 400_000
USED_YEAR_MIN, USED_YEAR_MAX = 1995, datetime.now().year + 1

# A source whose last scrape is older than this is shown as frozen
STALE_DAYS = 10
# automobile.tn new cars are scraped on the Pi on the 1st and 15th (gaps up to 17 days)
NEW_STALE_DAYS = 18

COUNTRIES = ["de", "fr", "it", "be"]

# automobile.tn brand slugs title-cased by the scraper -> how the brands write themselves
BRAND_NAMES = {
    "Bmw": "BMW", "Mercedes Benz": "Mercedes-Benz", "Mg": "MG", "Dfsk": "DFSK", "Byd": "BYD",
    "Im Motors": "IM Motors", "Gac Motor": "GAC Motor", "Ssangyong": "SsangYong", "Faw": "FAW",
    "Jmc": "JMC", "Lynk Co": "Lynk & Co", "Jmev": "JMEV", "Jac": "JAC", "Omoda Jaecoo": "Omoda & Jaecoo",
}

# AutoScout24 scrape settings (600/market, <= 8 years, <= 100k EUR) apply from this
# date; earlier points used other filters and are not comparable
EU_SERIES_SINCE = "2026-04-15"


# =============================================================================
# HELPERS
# =============================================================================

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Saved {path} ({os.path.getsize(path) / 1024:.0f} KB)")


def median(values):
    values = [v for v in values if v is not None]
    return int(statistics.median(values)) if values else None


def quartiles(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    n = len(values)
    return [values[int(n * 0.25)], values[n // 2], values[min(n - 1, int(n * 0.75))]]


def histogram(values, step, upper):
    """Counts per [i*step, (i+1)*step) bin; the last bin collects everything >= upper."""
    bins = [0] * (upper // step + 1)
    for v in values:
        bins[min(int(v // step), len(bins) - 1)] += 1
    return {"step": step, "counts": bins}


def pack(rows, cols):
    """Column-packed table: much smaller than a list of dicts."""
    return {"cols": cols, "rows": [[r.get(c) for c in cols] for r in rows]}


def day(iso):
    return (iso or "")[:10]


def is_stale(iso, max_days=STALE_DAYS):
    try:
        scraped = datetime.fromisoformat(iso.replace("Z", "")).replace(tzinfo=None)
    except (AttributeError, ValueError):
        return True
    return (datetime.now() - scraped).days > max_days


def normalize_fuel(value):
    v = (value or "").strip().lower()
    if not v:
        return None
    if "hybride" in v or "hybrid" in v:
        return "Hybride"
    if v.startswith("elec") or v.startswith("élec"):
        return "Électrique"
    if v.startswith("ess") or "gaz" in v or v == "lpg":
        return "Essence"
    if v.startswith("die") or v.startswith("dle"):
        return "Diesel"
    return "Autre"


def clean_used(cars):
    out = []
    for c in cars:
        price, year = c.get("price_tnd"), c.get("year")
        if not price or not year:
            continue
        if not (USED_PRICE_MIN <= price <= USED_PRICE_MAX and USED_YEAR_MIN <= year <= USED_YEAR_MAX):
            continue
        out.append(c)
    return out


def clean_eu_title(title):
    """AutoScout24 titles glue the model line to the version line ("TFSITFSI", "AustralEvolution")."""
    s = title or ""
    # Drop a repeated word run glued to itself: "50 TDI50 TDI" -> "50 TDI", "TFSITFSI" -> "TFSI"
    i = 1
    while i < len(s):
        for k in range(min(16, i, len(s) - i), 2, -1):
            start = i - k
            at_word = start == 0 or not s[start - 1].isalnum()
            if at_word and (s[start].isupper() or s[start].isdigit()) and s[start:i] == s[i:i + k]:
                s = s[:i] + s[i + k:]
                break
        i += 1
    # Split glued words: "AustralEvolution", "M2Competition" (but keep "xDrive", "kW")
    s = re.sub(r"(?<=[a-z]{3})(?=[A-Z][a-z])", " ", s)
    s = re.sub(r"(?<=[0-9])(?=[A-Z][a-z]{2,})", " ", s)
    s = re.sub(r"(?<=\bkW)(?=[A-Z])", " ", s)
    # Version codes glued to the next token: "420d420 d" -> "420d", "3004MATIC" -> "300 4MATIC"
    s = re.sub(r"\b(\d{3})([a-z])\1 \2\b", r"\1\2", s)
    s = re.sub(r"(?<=\d)(?=4MATIC|AWD\b|xDrive|quattro)", " ", s)
    s = re.sub(r"\b(TD4|TDI|TFSI)(?=\d\.\d)", r"\1 ", s)
    s = re.sub(r"\s*\|\s*", " | ", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def drop_partial_scrapes(series, ratio=0.8):
    """Days where the scrape returned far fewer listings than usual skew the medians; treat them as missing."""
    if len(series) < 5:
        return series
    typical = statistics.median(p["n"] for p in series)
    return [p for p in series if p["n"] >= ratio * typical]


def model_key(car):
    return f"{car.get('brand', '')} {car.get('model') or ''}".strip()


# =============================================================================
# SNAPSHOTS (one point of history)
# =============================================================================

def new_snapshot(data, top_brands=12):
    cars = data.get("cars") or []
    if not cars:
        return None
    brands = [b for b, _ in Counter(c["brand"] for c in cars).most_common(top_brands)]
    return {
        "date": day(data.get("scraped_at")),
        "n": len(cars),
        "median": median([c["price_tnd"] for c in cars]),
        "brands": {b: median([c["price_tnd"] for c in cars if c["brand"] == b]) for b in brands},
    }


def used_snapshot(data, top_models=30):
    cars = clean_used(data.get("cars") or [])
    if not cars:
        return None
    models = [m for m, _ in Counter(model_key(c) for c in cars if c.get("model")).most_common(top_models)]
    return {
        "date": day(data.get("scraped_at")),
        "n": len(cars),
        "median": median([c["price_tnd"] for c in cars]),
        "models": {m: median([c["price_tnd"] for c in cars if model_key(c) == m]) for m in models},
    }


def eu_snapshot(data):
    cars = [c for c in (data.get("cars") or []) if c.get("price_eur")]
    if not cars:
        return None
    return {
        "date": day(data.get("scraped_at")),
        "n": len(cars),
        "median": median([c["price_eur"] for c in cars]),
        "countries": {k: median([c["price_eur"] for c in cars if c.get("country") == k]) for k in COUNTRIES},
    }


def upsert(series, point):
    """Insert or replace the point for its date, keeping the series sorted."""
    if not point or not point.get("date"):
        return series
    series = [p for p in series if p["date"] != point["date"]]
    series.append(point)
    return sorted(series, key=lambda p: p["date"])


def seed_history_from_git():
    """Rebuild the time series from every committed version of the scraper outputs."""
    history = {"new": [], "used": [], "eu": []}
    for key, path, snap in (("new", NEW_FILE, new_snapshot), ("used", USED_FILE, used_snapshot), ("eu", EU_FILE, eu_snapshot)):
        revs = subprocess.run(["git", "log", "--format=%h", "--", path], capture_output=True, text=True).stdout.split()
        print(f"Seeding {key} from {len(revs)} commits...")
        for rev in revs:
            raw = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True).stdout
            try:
                point = snap(json.loads(raw))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
            # Keep the earliest commit's view of each scrape date
            if point and not any(p["date"] == point["date"] for p in history[key]):
                history[key] = upsert(history[key], point)
    return history


# =============================================================================
# PAGE AGGREGATES
# =============================================================================

def brand_name(raw):
    return BRAND_NAMES.get(raw, raw)


def build_new(data):
    cars = [{**c, "brand": brand_name(c["brand"])} for c in (data.get("cars") or [])]
    if not cars:
        return None
    prices = [c["price_tnd"] for c in cars]
    cheapest = sorted(cars, key=lambda c: c["price_tnd"])
    body = Counter(c.get("body_type") or "Autre" for c in cars)
    brands = Counter(c["brand"] for c in cars)
    segments = [(0, 50_000), (50_000, 80_000), (80_000, 120_000), (120_000, 180_000), (180_000, 300_000), (300_000, None)]
    return {
        "count": len(cars),
        "brands": len(brands),
        "median": median(prices),
        "quartiles": quartiles(prices),
        "min": cheapest[0]["price_tnd"],
        "cheapest": [{"name": c["full_name"], "price": c["price_tnd"]} for c in cheapest[:5]],
        "electrified": sum(1 for c in cars if c.get("is_electric") or c.get("is_hybrid")),
        "segments": [{"lo": lo, "hi": hi, "n": sum(1 for p in prices if p >= lo and (hi is None or p < hi))} for lo, hi in segments],
        "body": body.most_common(8),
        "fuel": Counter(normalize_fuel(c.get("fuel_type")) or "Autre" for c in cars).most_common(),
        "brandRange": [
            {
                "brand": b,
                "n": n,
                "min": min(c["price_tnd"] for c in cars if c["brand"] == b),
                "median": median([c["price_tnd"] for c in cars if c["brand"] == b]),
                "max": max(c["price_tnd"] for c in cars if c["brand"] == b),
            }
            for b, n in brands.most_common()
        ],
    }


def build_used(data, eu_cars):
    raw = data.get("cars") or []
    cars = clean_used(raw)
    if not cars:
        return None
    prices = [c["price_tnd"] for c in cars]
    km = [c["mileage_km"] for c in cars if c.get("mileage_km")]
    eu_by_model = {}
    for c in eu_cars:
        if c.get("price_eur"):
            eu_by_model.setdefault(f"{c['make']} {c.get('model') or ''}".lower(), []).append(c["price_eur"])
    models = []
    for name, n in Counter(model_key(c) for c in cars if c.get("model")).most_common(40):
        mp = [c["price_tnd"] for c in cars if model_key(c) == name]
        eu = eu_by_model.get(name.lower(), [])
        models.append({"name": name, "n": n, "quartiles": quartiles(mp), "euMedian": median(eu), "euN": len(eu)})
    return {
        "count": len(cars),
        "raw": len(raw),
        "brands": len({c["brand"] for c in cars}),
        "median": median(prices),
        "quartiles": quartiles(prices),
        "medianKm": median(km),
        "medianYear": median([c["year"] for c in cars]),
        "hist": histogram(prices, 10_000, 200_000),
        "years": sorted(Counter(c["year"] for c in cars if c["year"] >= 2000).items()),
        "fuel": Counter(normalize_fuel(c.get("fuel_type")) or "Non précisé" for c in cars).most_common(),
        "transmission": Counter((c.get("transmission") or "Non précisé").capitalize() for c in cars).most_common(3),
        "governorates": Counter(c.get("governorate") or "Non précisé" for c in cars).most_common(),
        "makes": Counter(c["brand"] for c in cars).most_common(15),
        "models": models,
    }


def build_eu(data):
    cars = [c for c in (data.get("cars") or []) if c.get("price_eur")]
    if not cars:
        return None
    prices = [c["price_eur"] for c in cars]
    return {
        "count": len(cars),
        "median": median(prices),
        "quartiles": quartiles(prices),
        "medianKm": median([c["mileage_km"] for c in cars if c.get("mileage_km") is not None]),
        "medianYear": median([c["year"] for c in cars if c.get("year")]),
        "countries": [
            {"code": k, "n": sum(1 for c in cars if c.get("country") == k),
             "quartiles": quartiles([c["price_eur"] for c in cars if c.get("country") == k])}
            for k in COUNTRIES
        ],
        "hist": histogram(prices, 5_000, 100_000),
        "makes": Counter(c["make"] for c in cars).most_common(15),
        "fuel": Counter(c.get("fuel_type") or "other" for c in cars).most_common(),
        "condition": Counter(c.get("condition") or "used" for c in cars).most_common(),
    }


def build_catalog_history(history):
    # The first snapshot has nothing to compare against: every trim shows up as "added"
    entries = sorted((e for e in (history or {}).get("entries", []) if e["summary"].get("total_before")), key=lambda e: e["date"])
    changes, added, removed = [], [], []
    for e in entries:
        ch = e.get("changes", {})
        for p in ch.get("price_changes", []):
            changes.append({"date": e["date"], "name": p["full_name"], "brand": brand_name(p.get("brand")),
                            "old": p["old_price"], "new": p["new_price"], "pct": p["change_pct"]})
        for t in ch.get("trims_added", []):
            added.append({"date": e["date"], "name": t.get("full_name"), "brand": brand_name(t.get("brand")), "price": t.get("price_tnd")})
        for t in ch.get("trims_removed", []):
            removed.append({"date": e["date"], "name": t.get("full_name"), "brand": brand_name(t.get("brand")), "price": t.get("price_tnd")})
    return {
        "entries": [{"date": e["date"], **e["summary"]} for e in entries],
        "priceChanges": sorted(changes, key=lambda c: c["date"], reverse=True),
        "added": sorted(added, key=lambda c: c["date"], reverse=True),
        "removed": sorted(removed, key=lambda c: c["date"], reverse=True),
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Build dashboard data files")
    parser.add_argument("--seed-from-git", action="store_true", help="Rebuild history.json from git log")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    new = load_json(NEW_FILE) or {}
    used = load_json(USED_FILE) or {}
    eu = load_json(EU_FILE) or {}

    history = seed_history_from_git() if args.seed_from_git else (load_json(HISTORY_FILE) or {"new": [], "used": [], "eu": []})
    history["new"] = upsert(history.get("new", []), new_snapshot(new))
    history["used"] = upsert(history.get("used", []), used_snapshot(used))
    history["eu"] = [p for p in upsert(history.get("eu", []), eu_snapshot(eu)) if p["date"] >= EU_SERIES_SINCE]
    history["eu"] = drop_partial_scrapes(history["eu"])
    save_json(history, HISTORY_FILE)

    eu_cars = eu.get("cars") or []
    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": {
            "new": {"name": "automobile.tn", "scraped_at": new.get("scraped_at"), "stale": is_stale(new.get("scraped_at"), NEW_STALE_DAYS)},
            "used": {"name": "9annas.tn", "scraped_at": used.get("scraped_at"), "stale": is_stale(used.get("scraped_at"))},
            "eu": {"name": "AutoScout24", "scraped_at": eu.get("scraped_at"), "stale": is_stale(eu.get("scraped_at"))},
        },
        "new": build_new(new),
        "used": build_used(used, eu_cars),
        "eu": build_eu(eu),
        "catalog": build_catalog_history(load_json(CATALOG_HISTORY_FILE)),
    }
    save_json(dashboard, os.path.join(OUT_DIR, "dashboard.json"))

    used_rows = [{
        "id": c["id"], "brand": c.get("brand"), "model": c.get("model"), "title": c.get("full_name"),
        "year": c["year"], "km": c.get("mileage_km"), "price": c["price_tnd"], "gov": c.get("governorate"),
        "fuel": normalize_fuel(c.get("fuel_type")), "gearbox": (c.get("transmission") or "").capitalize() or None,
        "thumb": c.get("thumbnail"),
    } for c in clean_used(used.get("cars") or [])]
    save_json(pack(used_rows, ["id", "brand", "model", "title", "year", "km", "price", "gov", "fuel", "gearbox", "thumb"]),
              os.path.join(OUT_DIR, "used_listings.json"))

    eu_rows = [{
        "url": c.get("listing_url"), "make": c.get("make"), "model": c.get("model"), "title": clean_eu_title(c.get("full_name")),
        "year": c.get("year"), "km": c.get("mileage_km"), "price": c["price_eur"], "country": c.get("country"),
        "fuel": c.get("fuel_type"), "hp": c.get("power_hp"), "thumb": c.get("thumbnail"),
    } for c in eu_cars if c.get("price_eur")]
    save_json(pack(eu_rows, ["url", "make", "model", "title", "year", "km", "price", "country", "fuel", "hp", "thumb"]),
              os.path.join(OUT_DIR, "eu_listings.json"))

    trims = [{
        "brand": brand_name(c["brand"]), "model": c["model"], "trim": c.get("trim"), "price": c["price_tnd"],
        "fuel": normalize_fuel(c.get("fuel_type")), "body": c.get("body_type"), "cv": c.get("cv_fiscal"),
        "hp": c.get("cv_din"), "url": c.get("url"), "thumb": c.get("thumbnail"),
    } for c in (new.get("cars") or [])]
    save_json(pack(trims, ["brand", "model", "trim", "price", "fuel", "body", "cv", "hp", "url", "thumb"]),
              os.path.join(OUT_DIR, "new_trims.json"))


if __name__ == "__main__":
    main()
