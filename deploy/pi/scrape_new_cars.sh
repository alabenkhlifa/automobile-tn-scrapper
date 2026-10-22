#!/usr/bin/env bash
# Scrape automobile.tn new cars on the Pi, rebuild the dashboard data and push both.
#
# automobile.tn (Cloudflare) returns 403 to GitHub runner IPs since 2026-05,
# so this runs from the home IP via cron on the 1st and 15th of each month,
# before the daily GitHub workflow rebuilds the dashboard data.
#
# One-time setup on the Pi (deploy key behind the github-automobile-tn ssh alias):
#   git clone --filter=blob:none git@github-automobile-tn:alabenkhlifa/automobile-tn-scrapper.git
#   python3 -m venv venv && venv/bin/pip install httpx beautifulsoup4 lxml
set -euo pipefail

# Wrapped in a function so bash parses it fully before git reset rewrites this file
main() {
  cd "$(dirname "$0")/../.."
  local files=(automobile_tn_new_cars.json automobile_tn_new_cars.csv new_cars_history.json data/)

  git rebase --abort 2>/dev/null || true
  git fetch --quiet origin main
  git reset --quiet --hard origin/main

  cp automobile_tn_new_cars.json automobile_tn_new_cars_previous.json
  venv/bin/python -u automobile_scraper.py
  venv/bin/python -u generate_history.py
  # The dashboard reads data/, not the raw files; the push redeploys GitHub Pages
  venv/bin/python -u build_dashboard_data.py

  git add "${files[@]}"
  if git diff --staged --quiet; then
    echo "No data changes"
    return
  fi
  git commit --quiet -m "Update new car data - $(date -u +%Y-%m-%d)"

  local attempt
  for attempt in 1 2 3; do
    if git pull --quiet --rebase origin main && git push --quiet origin HEAD:main; then
      echo "Pushed new car data"
      return
    fi
    git rebase --abort 2>/dev/null || true
    sleep 30
  done
  echo "Push failed after 3 attempts" >&2
  return 1
}

main "$@"
