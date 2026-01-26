# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Expertise

You are an expert at creating web scrapers and RAG (Retrieval-Augmented Generation) systems. Apply best practices for async crawling, HTML parsing, data extraction, and building knowledge bases from scraped content.

## Project Overview

Tunisia car marketplace scraper for automobile.tn. Extracts used cars (`/fr/occasion`) and new cars (`/fr/neuf`) with specs, pricing, and FCR (French personal import) eligibility data.

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run used cars scraper
python automobile-crawler.py

# Run new cars scraper
python automobile-new-crawler.py

# Run connectivity test across multiple sites
python crawl.py
```

## Architecture

### Scrapers

**automobile-crawler.py** - Used cars scraper
- Scrapes paginated listings from `/fr/occasion`
- `CarListing` dataclass with 30+ fields
- Computes FCR eligibility based on age and CV fiscal limits
- Output: `automobile_tn_cars.json`, `automobile_tn_cars.csv`

**automobile-new-crawler.py** - New cars scraper
- Three-level hierarchy: Brands → Models → Trims
- `CarTrim` dataclass with 40+ fields including full specs
- Extracts from `versions-item` divs and spec tables
- Filters out non-car pages (Devis, Concessionnaires)
- Output: `automobile_tn_new_cars.json`, `automobile_tn_new_cars.csv`

**crawl.py** - Multi-site connectivity test
- Tests crawl4ai against automobile.tn, mobile.de, autoscout24.de, leboncoin.fr
- Detects anti-bot protection

### Data Flow

```
AsyncWebCrawler → BeautifulSoup parsing → Regex extraction → Dataclass population → JSON/CSV export
```

### Key Dependencies

- `crawl4ai` - Async web crawler with headless browser
- `beautifulsoup4` + `lxml` - HTML parsing
- `patchright` - Browser automation (headless Chromium)

## Domain Knowledge

### URL Patterns
- Used cars: `/fr/occasion/{brand}/{model}/{id}`
- New cars: `/fr/neuf/{brand}`, `/fr/neuf/{brand}/{model}`, `/fr/neuf/{brand}/{model}/{trim}`

### FCR Eligibility Rules (Used Cars)
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

- Use 2-3 second delays before returning HTML to ensure JS completion
- Handle non-breaking spaces (`\u00a0`) in French numeric formatting
- Deduplicate by unique ID before export
- Debug HTML saved to `debug_*.html` files for parser development
