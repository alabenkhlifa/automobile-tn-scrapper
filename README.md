# 🚗 Tunisia Car Market Dashboard

[![Scraper](https://github.com/alabenkhlifa/automobile-tn-scrapper/actions/workflows/scrape.yml/badge.svg)](https://github.com/alabenkhlifa/automobile-tn-scrapper/actions/workflows/scrape.yml)
[![GitHub Pages](https://img.shields.io/badge/demo-live-brightgreen)](https://alabenkhlifa.github.io/automobile-tn-scrapper/)
[![New Cars](https://img.shields.io/badge/new_cars-543+-blue)](automobile_tn_new_cars.json)
[![Used Cars](https://img.shields.io/badge/used_cars-1000+-orange)](automobile_tn_used_cars.json)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> **Live, auto-updating dashboard tracking new and used car prices in Tunisia** 🇹🇳

An interactive dashboard that visualizes the Tunisian car market with **daily automated data updates**. Explore prices for both new and used cars, compare brands, analyze mileage and depreciation — all powered by GitHub Actions and GitHub Pages.

<p align="center">
  <a href="https://alabenkhlifa.github.io/automobile-tn-scrapper/">
    <img src="https://img.shields.io/badge/🚀_NEW_CARS_DASHBOARD-blue?style=for-the-badge" alt="New Cars Dashboard">
  </a>
  &nbsp;&nbsp;
  <a href="https://alabenkhlifa.github.io/automobile-tn-scrapper/used_cars_dashboard.html">
    <img src="https://img.shields.io/badge/🚗_USED_CARS_DASHBOARD-orange?style=for-the-badge" alt="Used Cars Dashboard">
  </a>
</p>

---

## ✨ Features

### New Cars Dashboard
- **📊 Interactive Charts** — Price distributions, brand comparisons, fuel type breakdowns
- **🔍 Smart Filtering** — Filter by brand, price range, fuel type, transmission
- **📱 Fully Responsive** — Works on desktop, tablet, and mobile
- **🤖 Auto-Updated** — GitHub Actions scrapes fresh data daily
- **⚡ Zero Backend** — 100% static, hosted free on GitHub Pages
- **🌙 Clean UI** — Modern design with smooth animations

### Used Cars Dashboard
- **📈 Market Analytics** — Price trends by mileage, age, and condition
- **🗺️ Geographic Distribution** — Listings breakdown by governorate
- **🔧 Equipment Analysis** — Track common features and options
- **👤 Ownership Insights** — First-hand vs second-hand ownership data
- **📅 Age & Mileage** — Depreciation analysis and value tracking

## 📈 What's Inside

| Metric | New Cars | Used Cars |
|--------|----------|-----------|
| Total Listings | 543+ | 1000+ |
| Brands | 30+ | 40+ |
| Data Points per Car | 40+ | 25+ |
| Update Frequency | Daily | Daily |

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Vanilla JS + [Chart.js](https://www.chartjs.org/) |
| Scraper | Python + [httpx](https://www.python-httpx.org/) + [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) |
| Automation | GitHub Actions (cron) |
| Hosting | GitHub Pages |
| Data Format | JSON + CSV |

## 🚀 How It Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Actions │────▶│  Python Scraper │────▶│   JSON Data     │
│  (Daily Cron)   │     │  (automobile.tn)│     │   (Auto-commit) │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Dashboard    │◀────│  GitHub Pages   │◀────│   index.html    │
│   (Live Site)   │     │  (Free Hosting) │     │   (Chart.js)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 📦 Project Structure

```
├── index.html                      # New cars dashboard
├── used_cars_dashboard.html        # Used cars dashboard
├── automobile_tn_new_cars.json     # New cars data (auto-updated)
├── automobile_tn_used_cars.json    # Used cars data (auto-updated)
├── automobile_tn_new_cars.csv      # New cars CSV export
├── automobile_tn_used_cars.csv     # Used cars CSV export
├── automobile_scraper.py           # New cars scraper
├── used_cars_scraper.py            # Used cars scraper
├── requirements.txt                # Python dependencies
└── .github/workflows/scrape.yml    # Daily automation
```

## 🏃 Run Locally

```bash
# Clone the repo
git clone https://github.com/alabenkhlifa/automobile-tn-scrapper.git
cd YOUR_REPO

# Open dashboards (no server needed!)
open index.html                    # New cars dashboard
open used_cars_dashboard.html      # Used cars dashboard

# Or run the scrapers manually
pip install -r requirements.txt
python automobile_scraper.py       # Scrape new cars
python used_cars_scraper.py        # Scrape used cars
```

## 🔧 Deploy Your Own

1. **Fork** this repository
2. Go to **Settings** → **Pages** → Set source to `main` branch
3. Your dashboard is live at `https://alabenkhlifa.github.io/automobile-tn-scrapper/`
4. GitHub Actions will auto-update data daily at 2 AM UTC

## 📊 Data Fields

### New Cars

| Field | Description |
|-------|-------------|
| `brand` | Manufacturer (e.g., Toyota, BMW) |
| `model` | Model name |
| `trim` | Trim level / version |
| `price_tnd` | Price in Tunisian Dinars |
| `fuel_type` | Essence, Diesel, Hybrid, Electric |
| `transmission` | Manual / Automatic |
| `engine_cc` | Engine displacement |
| `horsepower` | Power output |
| `cv_fiscal` | Fiscal horsepower (tax rating) |
| ... | 30+ more fields |

### Used Cars

| Field | Description |
|-------|-------------|
| `brand` | Manufacturer |
| `model` | Model name |
| `price_tnd` | Asking price in Tunisian Dinars |
| `year` | Year of manufacture |
| `mileage_km` | Odometer reading in kilometers |
| `fuel_type` | Essence, Diesel, GPL, Hybrid, Electric |
| `transmission` | Manual / Automatic |
| `cv_fiscal` | Fiscal horsepower |
| `governorate` | Seller location (e.g., Tunis, Sfax) |
| `ownership` | First-hand / Second-hand |
| `condition` | Vehicle condition |
| `equipment` | List of features and options |
| ... | 15+ more fields |

## 🤝 Contributing

Contributions are welcome! Feel free to:

- 🐛 Report bugs
- 💡 Suggest features
- 🔧 Submit PRs

## 📜 License

MIT © 2025

---

<p align="center">
  <b>If you found this useful, please ⭐ star the repo!</b>
</p>

<p align="center">
  Made with ❤️ for the Tunisian car community
</p>
