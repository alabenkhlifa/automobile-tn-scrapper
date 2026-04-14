"""
9annas.tn Used Cars Scraper
================================
Async scraper for used car listings from 9annas.tn API.

Features:
- JSON API scraping (no HTML parsing needed)
- Cursor-based pagination through /search and /searchmore endpoints
- Image URL extraction via /images/ endpoint
- Incremental mode: only fetches new listings since last run
- 10 concurrent image fetches with 0.2s delay

Run:
    python 9annas_scraper.py                    # incremental (default)
    python 9annas_scraper.py --full             # full scrape
    python 9annas_scraper.py --max-pages 5      # limit pages
    python 9annas_scraper.py --skip-images      # skip image fetching

Requirements:
    pip install httpx
"""

import asyncio
import json
import csv
import re
import os
import random
import argparse
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional, List

import httpx


# =============================================================================
# DATA MODEL
# =============================================================================

@dataclass
class NineannasCar:
    """Used car listing from 9annas.tn"""

    # Identification
    id: str = ""
    brand: str = ""
    model: str = ""
    full_name: str = ""
    url: str = ""

    # Pricing
    price_tnd: Optional[int] = None

    # Vehicle History
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    condition: str = ""  # "Nouveau", "Avec kilométrage"

    # Engine & Performance
    cv_fiscal: Optional[int] = None
    cylindree: str = ""  # "1.6L", "<1.0L"

    # Fuel & Transmission
    fuel_type: str = ""  # Essence, Diesel
    transmission: str = ""  # Manuelle, Automatique

    # Body
    body_type: str = ""  # Berline, Compacte, SUV, Utilitaire
    color_exterior: str = ""

    # Location
    governorate: str = ""
    location: str = ""

    # Images
    thumbnail: str = ""
    images: List[str] = field(default_factory=list)

    # Metadata
    listing_date: str = ""
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()


# =============================================================================
# CURSOR ENCODING (reverse-engineered from 9annas.tn JS)
# =============================================================================

TIMESTAMP_EPOCH_OFFSET = 1420070400


def num_to_letters(n: int) -> str:
    """Convert number to letter string: each digit d -> chr(98 + d) -> uppercase.
    0->B, 1->C, 2->D, ..., 9->K"""
    return ''.join(chr(98 + int(d)).upper() for d in str(n))


def encode_offset(ad_id: int, timestamp: int) -> str:
    """Encode ad ID and timestamp into cursor offset string."""
    return num_to_letters(ad_id + 99) + "A" + num_to_letters(timestamp - TIMESTAMP_EPOCH_OFFSET)


# =============================================================================
# DESCRIPTION PARSING
# =============================================================================

# Regex patterns for extracting specs from description text
SPEC_PATTERNS = {
    'brand': re.compile(r'Marque:\s*(.+?)\s*$', re.MULTILINE),
    'model': re.compile(r'Mod[èe]le:\s*(.+?)\s*$', re.MULTILINE),
    'year': re.compile(r'Ann[ée]e:\s*(\d{4})', re.MULTILINE),
    'mileage_km': re.compile(r'Kilom[ée]trage:\s*([\d\s\u00a0]+)\s*km', re.MULTILINE),
    'cv_fiscal': re.compile(r'Puissance fiscale:\s*(\d+)\s*CV', re.MULTILINE),
    'cylindree': re.compile(r'Cylindr[ée]e:\s*(.+?)\s*$', re.MULTILINE),
    'fuel_type': re.compile(r'Carburant:\s*(.+?)\s*$', re.MULTILINE),
    'transmission': re.compile(r'Boite:\s*(.+?)\s*$', re.MULTILINE),
    'body_type': re.compile(r'Type de carrosserie:\s*(.+?)\s*$', re.MULTILINE),
    'color_exterior': re.compile(r'Couleur du v[ée]hicule:\s*(.+?)\s*$', re.MULTILINE),
    'condition': re.compile(r'Etat du v[ée]hicule:\s*(.+?)\s*$', re.MULTILINE),
}


def parse_description(text: str) -> dict:
    """Extract car specs from description text."""
    specs = {}
    for key, pattern in SPEC_PATTERNS.items():
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            if key == 'year':
                specs[key] = int(value)
            elif key == 'mileage_km':
                km_str = value.replace(' ', '').replace('\u00a0', '')
                try:
                    specs[key] = int(km_str)
                except ValueError:
                    pass
            elif key == 'cv_fiscal':
                specs[key] = int(value)
            else:
                specs[key] = value
    return specs


MIN_PLAUSIBLE_PRICE = 2000   # TND — below this, API price is likely junk
MAX_PLAUSIBLE_PRICE = 300000  # TND — above this in title extraction, likely a phone number
MAX_PLAUSIBLE_MILEAGE = 500000  # km — above this, mileage is likely a typo
MIN_PLAUSIBLE_MILEAGE = 10  # km — below this, likely default/wrong
LOW_MILEAGE_THRESHOLD = 100  # km — suspicious if car is older than 2 years
CURRENT_YEAR = datetime.now().year

# French number patterns in titles: "28.500", "28 500"
TITLE_PRICE_RE = re.compile(r'(\d{2,3})[.\s\u00a0](\d{3})\b')


def extract_price_from_text(text: str) -> Optional[int]:
    """Try to extract a plausible price from title/description text.
    Only matches French thousands format (e.g. '28.500', '28 500').
    Skips bare numbers to avoid matching years or phone numbers."""
    for m in TITLE_PRICE_RE.finditer(text):
        val = int(m.group(1)) * 1000 + int(m.group(2))
        if MIN_PLAUSIBLE_PRICE <= val <= MAX_PLAUSIBLE_PRICE:
            return val
    return None


def parse_location(location_str: str) -> str:
    """Extract governorate from location string like 'Hammamet, Nabeul' -> 'Nabeul'."""
    if not location_str:
        return ""
    # Remove RTL marks
    location_str = location_str.replace('\u200e', '').strip()
    parts = [p.strip() for p in location_str.split(',')]
    # Last part is the governorate
    return parts[-1] if parts else ""


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class NineannasScraper:
    """Async scraper for 9annas.tn used cars API"""

    API_URL = "https://api.9annas.tn"
    SITE_URL = "https://9annas.tn"

    # Rate limiting
    MAX_CONCURRENT_IMAGES = 10
    DELAY_BETWEEN_SEARCHES = 0.3
    DELAY_BETWEEN_IMAGES = 0.2

    # Retry settings
    MAX_RETRIES = 3
    BACKOFF_BASE = 2  # seconds

    HEADERS = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://9annas.tn',
        'Referer': 'https://9annas.tn/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                      'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Safari/605.1.15',
    }

    SEARCH_BODY = {
        "query": "voiture",
        "location": {"id": None, "name": "", "radius": 10},
        "filter": {
            "categoryId": 1,
            "priceMin": None,
            "priceMax": None,
            "onlyWithPrice": False,
        },
        "isUserSearch": True,
        "isFilterSearch": True,
    }

    def __init__(self, max_pages: int = None, skip_images: bool = False, full: bool = False):
        self.cars: List[NineannasCar] = []
        self.max_pages = max_pages
        self.skip_images = skip_images
        self.full = full
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_IMAGES)
        self.stats = {
            "pages_fetched": 0,
            "ads_found": 0,
            "new_ads": 0,
            "images_fetched": 0,
            "with_price": 0,
            "with_images": 0,
            "errors": 0,
        }

    async def _request_with_retry(self, client: httpx.AsyncClient, method: str,
                                   url: str, **kwargs) -> Optional[httpx.Response]:
        """Make HTTP request with exponential backoff on 429/403."""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.request(method, url, **kwargs)
                if response.status_code in (429, 403):
                    wait = self.BACKOFF_BASE ** (attempt + 1) + random.uniform(0, 1)
                    print(f"    Rate limited ({response.status_code}), waiting {wait:.1f}s...")
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                if attempt == self.MAX_RETRIES - 1:
                    print(f"    Error: {e}")
                    self.stats["errors"] += 1
                    return None
                wait = self.BACKOFF_BASE ** (attempt + 1)
                await asyncio.sleep(wait)
        return None

    async def search(self, client: httpx.AsyncClient) -> tuple:
        """Initial search. Returns (ads_list, total_hits)."""
        response = await self._request_with_retry(
            client, "POST", f"{self.API_URL}/search", json=self.SEARCH_BODY
        )
        if not response:
            return [], 0

        data = response.json()
        return data.get("ads", []), data.get("hits", 0)

    async def search_more(self, client: httpx.AsyncClient, offset: str) -> list:
        """Fetch next page of results."""
        body = {
            "searchQuery": self.SEARCH_BODY,
            "offset": offset,
        }
        response = await self._request_with_retry(
            client, "POST", f"{self.API_URL}/searchmore", json=body
        )
        if not response:
            return []

        data = response.json()
        return data if isinstance(data, list) else []

    async def fetch_images(self, client: httpx.AsyncClient, ad_id: int) -> List[str]:
        """Fetch image URLs for an ad."""
        async with self.semaphore:
            await asyncio.sleep(self.DELAY_BETWEEN_IMAGES + random.uniform(0, 0.1))
            response = await self._request_with_retry(
                client, "GET", f"{self.API_URL}/images/", params={"ad": ad_id}
            )
            if not response:
                return []

            data = response.json()
            if isinstance(data, list):
                self.stats["images_fetched"] += 1
                return data
            return []

    def _ad_to_car(self, ad: dict) -> NineannasCar:
        """Convert API ad object to NineannasCar dataclass."""
        ad_id = ad.get("id", 0)
        description = ad.get("description", "")
        price = ad.get("price", 0)
        timestamp = ad.get("timestamp", 0)
        location_str = ad.get("location") or ""

        # Parse specs from description
        specs = parse_description(description)

        title = ad.get("title", "").strip()

        # Price: use API value, fallback to title/description if implausible
        price_tnd = price if price >= MIN_PLAUSIBLE_PRICE else None
        if not price_tnd:
            price_tnd = extract_price_from_text(title) or extract_price_from_text(description)

        # Mileage: discard implausible values
        mileage = specs.get("mileage_km")
        year = specs.get("year")
        if mileage is not None:
            if mileage < MIN_PLAUSIBLE_MILEAGE or mileage > MAX_PLAUSIBLE_MILEAGE:
                mileage = None
            elif mileage < LOW_MILEAGE_THRESHOLD and year and (CURRENT_YEAR - year) >= 2:
                # < 100 km on a car 2+ years old is almost certainly wrong
                mileage = None

        car = NineannasCar(
            id=str(ad_id),
            brand=specs.get("brand", ""),
            model=specs.get("model", ""),
            full_name=title,
            url=f"{self.SITE_URL}/ad/{ad_id}",
            price_tnd=price_tnd,
            year=specs.get("year"),
            mileage_km=mileage,
            condition=specs.get("condition", ""),
            cv_fiscal=specs.get("cv_fiscal"),
            cylindree=specs.get("cylindree", ""),
            fuel_type=specs.get("fuel_type", ""),
            transmission=specs.get("transmission", ""),
            body_type=specs.get("body_type", ""),
            color_exterior=specs.get("color_exterior", ""),
            governorate=parse_location(location_str),
            location=location_str.replace('\u200e', '').strip(),
            thumbnail=ad.get("thumbnail", ""),
            listing_date=datetime.fromtimestamp(timestamp).isoformat() if timestamp else "",
        )

        return car

    def _load_existing(self) -> set:
        """Load existing JSON data and return set of known IDs."""
        filename = "9annas_tn_used_cars.json"
        if not os.path.exists(filename):
            return set()

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            existing_cars = data.get("cars", [])
            # Rebuild car objects from existing data
            for car_dict in existing_cars:
                car = NineannasCar(**{
                    k: v for k, v in car_dict.items()
                    if k in NineannasCar.__dataclass_fields__
                })
                self.cars.append(car)
            known_ids = {c.id for c in self.cars}
            print(f"   Loaded {len(known_ids)} existing listings from {filename}")
            return known_ids
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"   Warning: could not load existing data: {e}")
            return set()

    async def scrape_all(self):
        """Main scraping function."""
        print("=" * 70)
        print("9ANNAS.TN USED CARS SCRAPER")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.max_pages:
            print(f"Max pages: {self.max_pages}")
        if self.skip_images:
            print("Skipping image fetches")
        mode = "full" if self.full else "incremental"
        print(f"Mode: {mode}")

        # Load existing data for incremental mode
        known_ids = set()
        if not self.full:
            print("\n[Step 1] Loading existing data...")
            known_ids = self._load_existing()
        else:
            print("\n[Step 1] Full mode — skipping existing data")

        async with httpx.AsyncClient(
            timeout=30.0,
            headers=self.HEADERS,
        ) as client:

            # Step 2: Initial search
            print("\n[Step 2] Searching for car listings...")
            ads, total_hits = await self.search(client)
            if not ads:
                print("   No results found!")
                return

            print(f"   Total hits: {total_hits:,}")
            print(f"   First page: {len(ads)} ads")
            self.stats["pages_fetched"] += 1

            # Step 3: Paginate and collect all new ads
            print("\n[Step 3] Paginating through results...")
            all_new_ads = []
            stop = False
            page = 1

            while True:
                new_in_batch = 0
                for ad in ads:
                    ad_id = str(ad.get("id", ""))
                    if ad_id in known_ids:
                        # Found a known listing — stop pagination
                        print(f"   Page {page}: hit known listing (id={ad_id}), stopping")
                        stop = True
                        break
                    all_new_ads.append(ad)
                    new_in_batch += 1

                self.stats["ads_found"] += len(ads)

                if stop:
                    break

                print(f"   Page {page}: {new_in_batch} new ads")

                # Check max pages
                if self.max_pages and page >= self.max_pages:
                    print(f"   Reached max pages ({self.max_pages})")
                    break

                # Compute offset from last ad
                last_ad = ads[-1]
                offset = encode_offset(last_ad["id"], last_ad["timestamp"])

                # Fetch next page
                await asyncio.sleep(self.DELAY_BETWEEN_SEARCHES)
                ads = await self.search_more(client, offset)
                if not ads:
                    print(f"   No more results after page {page}")
                    break

                page += 1
                self.stats["pages_fetched"] += 1

            self.stats["new_ads"] = len(all_new_ads)
            print(f"\n   New ads collected: {len(all_new_ads)}")

            # Step 4: Process new ads — parse descriptions and fetch images
            if all_new_ads:
                print(f"\n[Step 4] Processing {len(all_new_ads)} new ads...")
                new_cars = []

                filtered = 0
                for i, ad in enumerate(all_new_ads):
                    car = self._ad_to_car(ad)

                    # Filter out junk: no brand, brand is "Autres", or fully Arabic title
                    if not car.brand or car.brand.lower() == "autres":
                        filtered += 1
                        continue
                    if car.full_name and not re.search(r'[a-zA-Z0-9]', car.full_name):
                        filtered += 1
                        continue

                    new_cars.append(car)

                    if car.price_tnd:
                        self.stats["with_price"] += 1

                    if (i + 1) % 100 == 0:
                        print(f"   Parsed {i + 1}/{len(all_new_ads)} ads")

                if filtered:
                    print(f"   Filtered out {filtered} ads (no brand or 'Autres')")

                # Fetch images concurrently
                if not self.skip_images:
                    print(f"\n[Step 5] Fetching images for {len(new_cars)} ads...")
                    image_tasks = [
                        self.fetch_images(client, int(car.id)) for car in new_cars
                    ]
                    image_results = await asyncio.gather(*image_tasks, return_exceptions=True)

                    for car, result in zip(new_cars, image_results):
                        if isinstance(result, list):
                            car.images = result
                            if result:
                                self.stats["with_images"] += 1
                        elif isinstance(result, Exception):
                            self.stats["errors"] += 1

                    print(f"   Fetched images for {self.stats['images_fetched']} ads")

                # Prepend new cars (most recent first) to existing
                self.cars = new_cars + self.cars

        # Deduplicate by ID, then by title+brand (catch reposts with different IDs)
        seen_ids = set()
        seen_titles = set()
        deduped = []
        for car in self.cars:
            if car.id in seen_ids:
                continue
            title_key = (car.full_name.strip().lower(), car.brand.lower())
            if title_key in seen_titles:
                continue
            seen_ids.add(car.id)
            seen_titles.add(title_key)
            deduped.append(car)
        self.cars = deduped

        print(f"\n   Total cars after merge: {len(self.cars)}")

    def save_to_json(self, filename: str = "9annas_tn_used_cars.json"):
        """Save to JSON with metadata and stats."""
        # Compute stats
        prices = [c.price_tnd for c in self.cars if c.price_tnd]
        brand_counts = {}
        for c in self.cars:
            if c.brand:
                brand_counts[c.brand] = brand_counts.get(c.brand, 0) + 1

        top_brands = dict(sorted(brand_counts.items(), key=lambda x: -x[1])[:20])

        data = {
            "scraped_at": datetime.now().isoformat(),
            "source": "9annas.tn",
            "total": len(self.cars),
            "stats": {
                "with_price": len(prices),
                "with_images": sum(1 for c in self.cars if c.images),
                "top_brands": top_brands,
                "avg_price": sum(prices) // len(prices) if prices else 0,
                "price_range": [min(prices), max(prices)] if prices else [],
            },
            "cars": [asdict(c) for c in self.cars],
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved to {filename}")

    def save_to_csv(self, filename: str = "9annas_tn_used_cars.csv"):
        """Save to CSV with images as semicolon-separated URLs."""
        if not self.cars:
            print("No cars to save")
            return

        fieldnames = list(NineannasCar.__dataclass_fields__.keys())

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for car in self.cars:
                row = asdict(car)
                row['images'] = '; '.join(row['images']) if row['images'] else ''
                writer.writerow(row)

        print(f"Saved {len(self.cars)} cars to {filename}")

    def print_summary(self):
        """Print scraping summary."""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        print(f"\nScraping stats:")
        print(f"   Pages fetched: {self.stats['pages_fetched']}")
        print(f"   Ads found: {self.stats['ads_found']}")
        print(f"   New ads: {self.stats['new_ads']}")
        print(f"   Images fetched: {self.stats['images_fetched']}")
        print(f"   Errors: {self.stats['errors']}")

        if self.cars:
            prices = [c.price_tnd for c in self.cars if c.price_tnd]
            if prices:
                print(f"\nPrices: {min(prices):,} - {max(prices):,} TND "
                      f"(avg: {sum(prices)//len(prices):,})")

            years = [c.year for c in self.cars if c.year]
            if years:
                print(f"Years: {min(years)} - {max(years)}")

            mileages = [c.mileage_km for c in self.cars if c.mileage_km]
            if mileages:
                print(f"Mileage: {min(mileages):,} - {max(mileages):,} km")

            # Top brands
            brand_counts = {}
            for c in self.cars:
                if c.brand:
                    brand_counts[c.brand] = brand_counts.get(c.brand, 0) + 1

            print(f"\nTop brands:")
            for brand, count in sorted(brand_counts.items(), key=lambda x: -x[1])[:10]:
                print(f"   {brand}: {count}")

            # Fuel types
            fuel_counts = {}
            for c in self.cars:
                if c.fuel_type:
                    fuel_counts[c.fuel_type] = fuel_counts.get(c.fuel_type, 0) + 1

            if fuel_counts:
                print(f"\nFuel types:")
                for fuel, count in sorted(fuel_counts.items(), key=lambda x: -x[1]):
                    print(f"   {fuel}: {count}")

            # Governorates
            gov_counts = {}
            for c in self.cars:
                if c.governorate:
                    gov_counts[c.governorate] = gov_counts.get(c.governorate, 0) + 1

            if gov_counts:
                print(f"\nTop governorates:")
                for gov, count in sorted(gov_counts.items(), key=lambda x: -x[1])[:5]:
                    print(f"   {gov}: {count}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description='Scrape 9annas.tn used cars')
    parser.add_argument('--full', action='store_true',
                        help='Full scrape (ignore existing data)')
    parser.add_argument('--max-pages', type=int,
                        help='Maximum number of pages to scrape')
    parser.add_argument('--skip-images', action='store_true',
                        help='Skip fetching image URLs')
    args = parser.parse_args()

    scraper = NineannasScraper(
        max_pages=args.max_pages,
        skip_images=args.skip_images,
        full=args.full,
    )
    await scraper.scrape_all()

    scraper.save_to_json()
    scraper.save_to_csv()
    scraper.print_summary()

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
