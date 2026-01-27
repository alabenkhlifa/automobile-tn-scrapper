# 🚗 Tunisia Car Market Dashboard

[![Scraper](https://github.com/alabenkhlifa/automobile-tn-scrapper/actions/workflows/scrape.yml/badge.svg)](https://github.com/alabenkhlifa/automobile-tn-scrapper/actions/workflows/scrape.yml)
[![GitHub Pages](https://img.shields.io/badge/demo-live-brightgreen)](https://alabenkhlifa.github.io/automobile-tn-scrapper/)
[![Data](https://img.shields.io/badge/cars-543+-blue)](automobile_tn_new_cars.json)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> **Live, auto-updating dashboard tracking new car prices in Tunisia** 🇹🇳

An interactive dashboard that visualizes the Tunisian new car market with **weekly automated data updates**. Explore prices, compare brands, and analyze the market — all powered by GitHub Actions and GitHub Pages.

<p align="center">
  <a href="https://alabenkhlifa.github.io/automobile-tn-scrapper/">
    <img src="https://img.shields.io/badge/🚀_VIEW_LIVE_DEMO-blue?style=for-the-badge" alt="Live Demo">
  </a>
</p>

---

## ✨ Features

- **📊 Interactive Charts** — Price distributions, brand comparisons, fuel type breakdowns
- **🔍 Smart Filtering** — Filter by brand, price range, fuel type, transmission
- **📱 Fully Responsive** — Works on desktop, tablet, and mobile
- **🤖 Auto-Updated** — GitHub Actions scrapes fresh data every week
- **⚡ Zero Backend** — 100% static, hosted free on GitHub Pages
- **🌙 Clean UI** — Modern design with smooth animations

## 📈 What's Inside

| Metric | Value |
|--------|-------|
| Total Cars | 543+ |
| Brands | 30+ |
| Data Points per Car | 40+ |
| Update Frequency | Weekly |

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
│  (Weekly Cron)  │     │  (automobile.tn)│     │   (Auto-commit) │
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
├── index.html                    # Interactive dashboard
├── automobile_tn_new_cars.json   # Car data (auto-updated)
├── automobile_tn_new_cars.csv    # CSV export
├── automobile_scraper.py         # Lightweight scraper
├── requirements.txt              # Python dependencies
└── .github/workflows/scrape.yml  # Weekly automation
```

## 🏃 Run Locally

```bash
# Clone the repo
git clone https://github.com/alabenkhlifa/automobile-tn-scrapper.git
cd YOUR_REPO

# Open dashboard (no server needed!)
open index.html

# Or run the scraper manually
pip install -r requirements.txt
python automobile_scraper.py
```

## 🔧 Deploy Your Own

1. **Fork** this repository
2. Go to **Settings** → **Pages** → Set source to `main` branch
3. Your dashboard is live at `https://alabenkhlifa.github.io/automobile-tn-scrapper/`
4. GitHub Actions will auto-update data every Sunday at 2 AM UTC

## 📊 Data Fields

Each car entry includes:

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
