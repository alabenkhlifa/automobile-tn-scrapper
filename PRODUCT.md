# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Portfolio visitors:** recruiters, engineers, and peers who land on the public GitHub Pages site to see what the scraping and data pipeline produces. They browse, they do not buy; the site has to show the work is real, live, and well made.
- **Market watchers:** dealers, analysts, and journalists tracking Tunisian and European car prices, catalog changes, and price moves over time. They come back to check what moved.

## Product Purpose

Public, auto-updating dashboards over car-market data scraped daily by GitHub Actions: Tunisian new cars (automobile.tn), Tunisian used cars (9annas.tn, plus a frozen automobile.tn used set), and European listings (AutoScout24 DE, FR, IT, BE). Success: a visitor understands within one screen that this is live, multi-source market data, and a returning watcher can see what changed.

## Positioning

The only place showing Tunisian new-car list prices, Tunisian used-car asking prices, and European listing prices side by side, refreshed daily from scrapers, with a week-by-week change log of the Tunisian new-car catalog.

## Operating Context

- Static site on GitHub Pages; each dashboard fetches JSON files committed to the repo by the daily workflow.
- Data cadence: 9annas and AutoScout24 daily; automobile.tn new cars weekly (Mondays). automobile.tn blocks GitHub runners since May 2026, so its new (548 trims, 2026-05-04) and used (60 listings, 2026-05-06) data are frozen at the last good scrape.
- Current surfaces: `index.html` (TN new cars), `used_cars_dashboard.html` (TN used, automobile.tn), `autoscout24_dashboard.html` (EU), `new_cars_history.html` (new-car change log). No 9annas dashboard yet; 9annas should become the main TN used-car source.

## Capabilities and Constraints

- Static HTML/JS only, no backend; Chart.js and Tailwind CDN today. Data files are large (9annas JSON ~29 MB, 18,630 listings), so loading cost matters.
- Bilingual FR/EN UI toggle exists on every dashboard and must remain.
- Currencies: TND for Tunisia, EUR for Europe.
- 9annas data is user-generated and noisy (prices up to 100,000,000 TND, years 8 to 9999, free-text fuel values); views must filter or flag outliers rather than show them raw.
- Data freshness must be shown honestly per source, including frozen sources.

## Evidence on Hand

- Real scraped data: `automobile_tn_new_cars.json`, `automobile_tn_used_cars.json`, `9annas_tn_used_cars.json`, `autoscout24_*.json`, `new_cars_history.json` (weekly snapshots since 2026-02-07).
- Listing thumbnails/image URLs exist for 9annas, AutoScout24, and new cars.
- No testimonials, user counts, or traffic numbers exist; do not invent them.

## Product Principles

1. Live data is the proof: show freshness and source for every number.
2. Comparison across sources and markets is the reason to visit; make it one step away.
3. Change over time beats a static snapshot for returning watchers.
4. Honest about gaps: frozen or noisy sources are labeled, never hidden.
