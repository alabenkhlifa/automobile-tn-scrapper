# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Expertise

You are an expert at creating web scrapers and RAG (Retrieval-Augmented Generation) systems. Apply best practices for async crawling, HTML parsing, data extraction, and building knowledge bases from scraped content.

## Project Overview

Multi-source car marketplace scraper. Covers:
- **automobile.tn** new cars (`/fr/neuf`) and used cars (`/fr/occasion`)
- **9annas.tn** used cars via JSON API (~12k listings, aggregates from Tayara)
- **AutoScout24** multi-country used/new listings (DE, FR, IT, BE)

Data is exported to JSON + CSV and used by downstream projects via GitHub Actions daily runs.

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run new cars scraper (all brands)
python automobile_scraper.py

# Run scraper for specific brands only
python automobile_scraper.py --brands alfa-romeo,citroen

# Run AutoScout24 scraper (multi-country)
python autoscout24_scraper.py --countries de,fr,it,be --max-listings 100
python autoscout24_scraper.py --countries de --makes bmw,audi --condition used --max-price 30000
python autoscout24_scraper.py --countries de --use-playwright  # anti-bot fallback

# Run 9annas.tn used cars scraper
python 9annas_scraper.py                    # incremental (default, stops at known listings)
python 9annas_scraper.py --full             # full scrape
python 9annas_scraper.py --max-pages 5      # limit pages (20 ads/page)
python 9annas_scraper.py --skip-images      # skip image URL fetching
```

## Architecture

### Scrapers

**automobile_scraper.py** - New cars scraper
- Three-level hierarchy: Brands → Models → Trims
- `CarTrim` dataclass with 40+ fields including full specs
- Extracts from `versions-item` divs and spec tables
- Filters out non-car pages (Devis, Concessionnaires)
- Output: `automobile_tn_new_cars.json`, `automobile_tn_new_cars.csv`

**autoscout24_scraper.py** - AutoScout24 multi-country scraper (DE, FR, IT, BE)
- Scrapes both new and used car listings across 4 European countries
- `AutoScout24Car` dataclass with ~35 fields
- Three-tier extraction: JSON-LD → localized HTML spec tables → regex fallback
- Rate limiting: 5 concurrent, 0.5s delay + jitter, exponential backoff on 429/403
- User-Agent rotation and per-country Accept-Language headers
- Optional Playwright fallback for anti-bot protection (`--use-playwright`)
- Output: `autoscout24_{country}.json/csv`, `autoscout24_all.json/csv`

**9annas_scraper.py** - 9annas.tn used cars scraper (JSON API)
- Uses `/search` + `/searchmore` + `/images/?ad={id}` endpoints (no HTML parsing)
- `NineannasCar` dataclass with car specs + thumbnail + list of image URLs
- Reverse-engineered cursor pagination: offset encoded as `num_to_letters(id+99) + "A" + num_to_letters(timestamp-1420070400)` where digit d → chr(98+d) uppercase
- Parses specs from description field (French `Key: Value` format)
- Incremental mode (default): loads existing JSON, stops pagination at known ad IDs
- Data cleaning: drops empty/`Autres` brands + Arabic-only titles, price fallback to French-formatted title ("28.500" → 28500), discards implausible mileage (<10km, >500k km, or <100km on 2+ year old cars), dedupes by ID and title+brand
- Rate limiting: 0.3s between search pages, semaphore(10) for images, exp backoff on 429/403
- Output: `9annas_tn_used_cars.json/csv`

### Data Flow

```
httpx requests → BeautifulSoup parsing → Regex extraction → Dataclass population → JSON/CSV export
```

### Key Dependencies

- `httpx` - Async HTTP client
- `beautifulsoup4` + `lxml` - HTML parsing

## Domain Knowledge

### URL Patterns
- automobile.tn used cars: `/fr/occasion/{brand}/{model}/{id}`
- automobile.tn new cars: `/fr/neuf/{brand}`, `/fr/neuf/{brand}/{model}`, `/fr/neuf/{brand}/{model}/{trim}`
- 9annas.tn ad page: `https://9annas.tn/ad/{id}`

### 9annas.tn API
- `POST /search` — initial search, returns 20 ads + total `hits` count
- `POST /searchmore` — paginated, takes `{searchQuery, offset}`, returns plain array of 20 ads
- `GET /images/?ad={id}` — returns array of full-resolution image URLs (WebP, hosted on GCS)
- Cars category: `categoryId: 1`, broad query: `"voiture"` (~12k results)

### FCR Eligibility Rules (Used Cars - for future implementation)
- Max 8 years old for FCR Famille
- Essence: ≤9 CV fiscal
- Diesel: ≤10 CV fiscal
- Electric/Hybrid rechargeable: Always eligible

### Common Regex Patterns
- Price: `(\d{2,3}[\s\u00a0]?\d{3})\s*(?:DT|TND)`
- Year: `\b(20[0-2]\d)\b`
- Mileage: `(\d[\d\s\u00a0]*\d{3})\s*km`
- CV fiscal: `(\d{1,2})\s*(?:CV|cv)`

### Filtering (New Cars)
Skip brand slugs: `electrique`, `comparateur`, `concessionnaires`
Skip model slugs: `devis`, `comparateur`

## Conventions

- Handle non-breaking spaces (`\u00a0`) in French numeric formatting
- Deduplicate by unique ID before export
- Debug HTML saved to `debug_*.html` files for parser development
