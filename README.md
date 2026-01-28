# 🚗 Car Market Dashboard — Tunisia & Europe

[![Scraper](https://github.com/alabenkhlifa/automobile-tn-scrapper/actions/workflows/scrape.yml/badge.svg)](https://github.com/alabenkhlifa/automobile-tn-scrapper/actions/workflows/scrape.yml)
[![GitHub Pages](https://img.shields.io/badge/demo-live-brightgreen)](https://alabenkhlifa.github.io/automobile-tn-scrapper/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> **Live, auto-updating dashboards tracking car prices in Tunisia 🇹🇳 and across Europe 🇪🇺**

Interactive dashboards that visualize car markets with **daily automated data updates**. Explore prices for new and used cars, compare brands, analyze mileage and depreciation — powered by GitHub Actions and GitHub Pages.

<p align="center">
  <a href="https://alabenkhlifa.github.io/automobile-tn-scrapper/">
    <img src="https://img.shields.io/badge/🚀_NEW_CARS_(TN)-blue?style=for-the-badge" alt="New Cars Dashboard">
  </a>
  &nbsp;&nbsp;
  <a href="https://alabenkhlifa.github.io/automobile-tn-scrapper/used_cars_dashboard.html">
    <img src="https://img.shields.io/badge/🚗_USED_CARS_(TN)-orange?style=for-the-badge" alt="Used Cars Dashboard">
  </a>
  &nbsp;&nbsp;
  <a href="https://alabenkhlifa.github.io/automobile-tn-scrapper/autoscout24_dashboard.html">
    <img src="https://img.shields.io/badge/🇪🇺_AUTOSCOUT24_(EU)-green?style=for-the-badge" alt="AutoScout24 Dashboard">
  </a>
</p>

---

## ✨ Features

### Tunisia — New Cars Dashboard
- **📊 Interactive Charts** — Price distributions, brand comparisons, fuel type breakdowns
- **🔍 Smart Filtering** — Filter by brand, price range, fuel type, transmission
- **📱 Fully Responsive** — Works on desktop, tablet, and mobile
- **🤖 Auto-Updated** — GitHub Actions scrapes fresh data daily

### Tunisia — Used Cars Dashboard
- **📈 Market Analytics** — Price trends by mileage, age, and condition
- **🗺️ Geographic Distribution** — Listings breakdown by governorate
- **🔧 Equipment Analysis** — Track common features and options
- **👤 Ownership Insights** — First-hand vs second-hand ownership data

### Europe — AutoScout24 Dashboard
- **🌍 Multi-Country** — DE, FR, IT, BE markets in a single view
- **🔗 Clickable Listings** — Click any row to open the listing on AutoScout24
- **🌐 Bilingual** — Full French/English UI toggle
- **📊 Cross-Market Comparison** — Compare prices across European markets
- **⚡ Rate-Limit Monitoring** — Built-in request metrics and tuning suggestions

## 📈 What's Inside

| Metric | TN New Cars | TN Used Cars | EU AutoScout24 |
|--------|-------------|--------------|----------------|
| Total Listings | 543+ | 1000+ | 500+ per country |
| Brands | 30+ | 40+ | All makes |
| Data Points per Car | 40+ | 25+ | 35+ |
| Update Frequency | Weekly | Daily | Daily |

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Vanilla JS + [Chart.js](https://www.chartjs.org/) |
| Scrapers | Python + [httpx](https://www.python-httpx.org/) (async) + [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) |
| Automation | GitHub Actions (cron) |
| Hosting | GitHub Pages |
| Data Format | JSON + CSV |

## 🚀 How It Works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Actions  │────▶│  Python Scraper  │────▶│   JSON Data     │
│  (Daily Cron)    │     │  (async httpx)   │     │   (Auto-commit) │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Dashboard     │◀────│  GitHub Pages    │◀────│   HTML + JS     │
│   (Live Site)    │     │  (Free Hosting)  │     │   (Chart.js)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 📦 Project Structure

```
├── index.html                      # New cars dashboard (TN)
├── used_cars_dashboard.html        # Used cars dashboard (TN)
├── autoscout24_dashboard.html      # AutoScout24 dashboard (EU)
├── automobile_tn_new_cars.json     # New cars data (auto-updated)
├── automobile_tn_used_cars.json    # Used cars data (auto-updated)
├── autoscout24_de.json             # AutoScout24 DE data
├── automobile_scraper.py           # New cars scraper (automobile.tn)
├── used_cars_scraper.py            # Used cars scraper (automobile.tn)
├── autoscout24_scraper.py          # AutoScout24 multi-country scraper
├── requirements.txt                # Python dependencies
└── .github/workflows/scrape.yml    # Daily automation
```

## 🏃 Run Locally

```bash
# Clone the repo
git clone https://github.com/alabenkhlifa/automobile-tn-scrapper.git
cd automobile-tn-scrapper

# Install dependencies
pip install -r requirements.txt

# Open dashboards (no server needed!)
open index.html                    # New cars (TN)
open used_cars_dashboard.html      # Used cars (TN)
open autoscout24_dashboard.html    # AutoScout24 (EU)

# Run scrapers manually
python automobile_scraper.py                           # TN new cars
python used_cars_scraper.py                            # TN used cars
python autoscout24_scraper.py --countries de --max-listings 100  # AutoScout24 DE
python autoscout24_scraper.py --countries de,fr,it,be --max-listings 200  # Multi-country
python autoscout24_scraper.py --makes bmw,audi --max-price 30000         # Filtered
```

## 🔧 Deploy Your Own

1. **Fork** this repository
2. Go to **Settings** → **Pages** → Set source to `main` branch
3. Your dashboard is live at `https://YOUR_USERNAME.github.io/automobile-tn-scrapper/`
4. GitHub Actions will auto-update data daily at 2 AM UTC

## 📊 Data Fields

### New Cars (TN)

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

### Used Cars (TN)

| Field | Description |
|-------|-------------|
| `brand` | Manufacturer |
| `model` | Model name |
| `price_tnd` | Asking price in Tunisian Dinars |
| `year` | Year of manufacture |
| `mileage_km` | Odometer reading in kilometers |
| `fuel_type` | Essence, Diesel, GPL, Hybrid, Electric |
| `governorate` | Seller location (e.g., Tunis, Sfax) |
| ... | 15+ more fields |

### AutoScout24 (EU)

| Field | Description |
|-------|-------------|
| `make` | Manufacturer |
| `model` | Model name |
| `price_eur` | Price in EUR |
| `year` | Year / first registration |
| `mileage_km` | Odometer in km |
| `fuel_type` | Petrol, Diesel, Electric, Hybrid, etc. |
| `power_kw` / `power_hp` | Engine power |
| `transmission` | Manual / Automatic |
| `country` | Market (DE, FR, IT, BE) |
| `listing_url` | Direct link to the listing |
| ... | 25+ more fields |

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
