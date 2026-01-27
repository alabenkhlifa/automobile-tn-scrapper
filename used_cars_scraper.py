"""
automobile.tn Used Cars Scraper
================================
Async scraper for used car listings from automobile.tn/fr/occasion.

Features:
- Pagination support (10 cars per page)
- Extracts JSON-LD schema data + HTML specs
- Equipment lists by category (safety, interior, exterior, functional)
- Seller phone extraction
- 10 concurrent requests with 0.2s delay

Run:
    python used_cars_scraper.py
    python used_cars_scraper.py --max-pages 5
    python used_cars_scraper.py --brands bmw,audi,mercedes-benz

Requirements:
    pip install httpx beautifulsoup4 lxml
"""

import asyncio
import json
import csv
import re
import argparse
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional, List
from bs4 import BeautifulSoup

import httpx


# =============================================================================
# DATA MODEL
# =============================================================================

@dataclass
class UsedCar:
    """Used car listing with all specs and equipment"""

    # Identification
    id: str = ""
    brand: str = ""
    model: str = ""
    full_name: str = ""
    url: str = ""

    # Pricing
    price_tnd: Optional[int] = None
    price_evaluation: str = ""  # "Prix élevé", "Bon prix", etc.

    # Vehicle History
    registration_date: str = ""  # ISO format: "2015-08-01"
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    ownership: str = ""  # "2ème main", "1ère main"
    condition: str = ""  # "Normal", "Bon", "Très bon"

    # Engine & Performance
    cv_fiscal: Optional[int] = None
    cv_din: Optional[int] = None

    # Fuel & Transmission
    fuel_type: str = ""  # Essence, Diesel, Électrique, Hybride rechargeable
    transmission: str = ""  # Manuelle, Automatique
    drivetrain: str = ""  # Traction, Propulsion

    # Body & Interior
    body_type: str = ""  # Citadine, Berline, SUV
    color_exterior: str = ""
    color_interior: str = ""
    upholstery: str = ""  # Tissu, Cuir
    doors: Optional[int] = None
    seats: Optional[int] = None

    # Equipment (4 category lists)
    equipment_safety: List[str] = field(default_factory=list)
    equipment_interior: List[str] = field(default_factory=list)
    equipment_exterior: List[str] = field(default_factory=list)
    equipment_functional: List[str] = field(default_factory=list)

    # Location & Seller
    governorate: str = ""  # Ariana, Tunis
    seller_phone: str = ""

    # Metadata
    listing_date: str = ""
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class UsedCarsScraper:
    """Async scraper for automobile.tn used cars"""

    BASE_URL = "https://www.automobile.tn"
    OCCASION_URL = "https://www.automobile.tn/fr/occasion"

    # Rate limiting
    MAX_CONCURRENT = 10
    DELAY_BETWEEN_REQUESTS = 0.2

    def __init__(self, max_pages: int = None, specific_brands: List[str] = None):
        self.cars: List[UsedCar] = []
        self.max_pages = max_pages
        self.specific_brands = [b.lower() for b in specific_brands] if specific_brands else None
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        self.stats = {
            "pages_scraped": 0,
            "listings_found": 0,
            "cars_scraped": 0,
            "with_price": 0,
            "with_equipment": 0,
            "with_phone": 0,
        }

    async def fetch(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        """Fetch URL with rate limiting"""
        async with self.semaphore:
            try:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                await asyncio.sleep(self.DELAY_BETWEEN_REQUESTS)
                return response.text
            except httpx.HTTPError as e:
                print(f"    Error fetching {url}: {e}")
                return None

    async def get_total_pages(self, client: httpx.AsyncClient) -> int:
        """Get total number of pages from listing count"""
        html = await self.fetch(client, self.OCCASION_URL)
        if not html:
            return 0

        soup = BeautifulSoup(html, 'lxml')

        # Look for "Afficher X annonces" text
        text = soup.get_text()
        match = re.search(r'Afficher\s+([\d\s\u00a0]+)\s*annonces?', text, re.I)
        if match:
            count_str = match.group(1).replace(' ', '').replace('\u00a0', '')
            try:
                total_listings = int(count_str)
                total_pages = (total_listings + 9) // 10  # 10 per page, round up
                print(f"   Total listings: {total_listings:,} ({total_pages} pages)")
                return total_pages
            except ValueError:
                pass

        # Fallback: try to find pagination
        pagination = soup.find_all('a', href=re.compile(r'/fr/occasion/\d+$'))
        if pagination:
            max_page = 1
            for link in pagination:
                href = link.get('href', '')
                page_match = re.search(r'/fr/occasion/(\d+)$', href)
                if page_match:
                    max_page = max(max_page, int(page_match.group(1)))
            print(f"   Estimated pages from pagination: {max_page}")
            return max_page

        print("   Could not determine page count, defaulting to 1")
        return 1

    async def fetch_listing_page(self, client: httpx.AsyncClient, page: int) -> List[str]:
        """Fetch a listing page and extract car detail URLs"""
        url = self.OCCASION_URL if page == 1 else f"{self.OCCASION_URL}/{page}"

        html = await self.fetch(client, url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        car_urls = []

        # Find links matching /fr/occasion/{brand}/{model}/{id}
        pattern = re.compile(r'^/fr/occasion/([a-z0-9-]+)/([a-z0-9-]+)/(\d+)$')

        for link in soup.find_all('a', href=pattern):
            href = link.get('href', '')
            match = pattern.match(href)
            if match:
                brand_slug = match.group(1)

                # Filter by brand if specified
                if self.specific_brands and brand_slug not in self.specific_brands:
                    continue

                full_url = f"{self.BASE_URL}{href}"
                if full_url not in car_urls:
                    car_urls.append(full_url)

        return car_urls

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract JSON-LD schema data from page"""
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                # Handle array or single object
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Car':
                            return item
                elif data.get('@type') == 'Car':
                    return data
            except (json.JSONDecodeError, AttributeError):
                continue
        return None

    async def fetch_car_details(self, client: httpx.AsyncClient, url: str) -> Optional[UsedCar]:
        """Fetch and parse a car detail page"""
        html = await self.fetch(client, url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text(separator=' ', strip=True)

        # Extract URL parts: /fr/occasion/{brand}/{model}/{id}
        parts = url.rstrip('/').split('/')
        brand_slug = parts[-3] if len(parts) >= 3 else ""
        model_slug = parts[-2] if len(parts) >= 2 else ""
        car_id = parts[-1] if len(parts) >= 1 else ""

        car = UsedCar(
            url=url,
            id=car_id,
            brand=brand_slug.replace('-', ' ').title(),
            model=model_slug.replace('-', ' ').title(),
        )

        # Priority 1: Extract from JSON-LD
        json_ld = self._extract_json_ld(soup)
        if json_ld:
            self._parse_json_ld(car, json_ld)

        # Priority 2: Parse HTML specs
        self._parse_html_specs(car, soup)

        # Priority 3: Extract price from page
        self._extract_price(car, soup, page_text)

        # Priority 4: Extract equipment sections
        self._extract_equipment(car, soup)

        # Priority 5: Extract seller phone
        self._extract_phone(car, soup)

        # Build full name if not set
        if not car.full_name:
            car.full_name = f"{car.brand} {car.model}".strip()

        # Extract year from registration_date
        if car.registration_date and not car.year:
            year_match = re.search(r'(\d{4})', car.registration_date)
            if year_match:
                car.year = int(year_match.group(1))

        # Update stats
        if car.price_tnd:
            self.stats["with_price"] += 1
        if any([car.equipment_safety, car.equipment_interior,
                car.equipment_exterior, car.equipment_functional]):
            self.stats["with_equipment"] += 1
        if car.seller_phone:
            self.stats["with_phone"] += 1

        return car

    def _parse_json_ld(self, car: UsedCar, data: dict):
        """Parse JSON-LD schema data into UsedCar"""
        # Brand
        brand_data = data.get('brand', {})
        if isinstance(brand_data, dict):
            brand_name = brand_data.get('name', '')
            if brand_name:
                car.brand = brand_name
        elif isinstance(brand_data, str):
            car.brand = brand_data

        # Model and full name
        car.model = data.get('model', '') or car.model
        car.full_name = data.get('name', '') or f"{car.brand} {car.model}"

        # Price from offers
        offers = data.get('offers', {})
        if isinstance(offers, dict):
            price = offers.get('price')
            if price:
                try:
                    car.price_tnd = int(float(price))
                except (ValueError, TypeError):
                    pass

        # Mileage
        mileage = data.get('mileageFromOdometer')
        if mileage:
            try:
                car.mileage_km = int(float(mileage))
            except (ValueError, TypeError):
                pass

        # Fuel type
        fuel = data.get('fuelType', '')
        if fuel:
            car.fuel_type = fuel

        # Body type
        body = data.get('bodyType', '')
        if body:
            car.body_type = body

        # Other JSON-LD fields
        if data.get('numberOfDoors'):
            try:
                car.doors = int(data['numberOfDoors'])
            except (ValueError, TypeError):
                pass

        if data.get('seatingCapacity'):
            try:
                car.seats = int(data['seatingCapacity'])
            except (ValueError, TypeError):
                pass

    def _parse_html_specs(self, car: UsedCar, soup: BeautifulSoup):
        """Parse specification fields from HTML"""

        # Spec mapping: French label -> (attribute, handler type)
        spec_map = {
            'kilométrage': ('mileage_km', 'km'),
            'mise en circulation': ('registration_date', 'date'),
            'puissance fiscale': ('cv_fiscal', 'cv'),
            'puissance din': ('cv_din', 'number'),
            'boite': ('transmission', 'transmission'),
            'énergie': ('fuel_type', 'text'),
            'carrosserie': ('body_type', 'text'),
            'état': ('condition', 'text'),
            'anciens propriétaires': ('ownership', 'text'),
            'gouvernorat': ('governorate', 'text'),
            'portes': ('doors', 'digit'),
            'places': ('seats', 'digit'),
            'couleur extérieure': ('color_exterior', 'text'),
            'couleur intérieure': ('color_interior', 'text'),
            'sellerie': ('upholstery', 'text'),
        }

        # Also check for "transmission" label for drivetrain (not boite)
        drivetrain_keywords = ['propulsion', 'traction', '4x4', 'intégrale']

        # Find all li elements with spec-name and spec-value structure
        for li in soup.find_all('li'):
            spec_name = li.find('span', class_='spec-name')
            spec_value = li.find('span', class_='spec-value')

            if not spec_name or not spec_value:
                continue

            label = spec_name.get_text(strip=True).lower()
            value_text = spec_value.get_text(separator=' ', strip=True)

            # Check for drivetrain (labeled as "Transmission" in the car detail section)
            if 'transmission' in label:
                value_lower = value_text.lower()
                for kw in drivetrain_keywords:
                    if kw in value_lower:
                        car.drivetrain = value_text.title()
                        break
                continue

            for label_key, (attr, handler) in spec_map.items():
                if label_key not in label:
                    continue

                # Skip if already set
                current = getattr(car, attr, None)
                if current is not None and current != "" and current != 0:
                    continue

                if handler == 'km':
                    match = re.search(r'([\d\s\u00a0]+)', value_text)
                    if match:
                        km_str = match.group(1).replace(' ', '').replace('\u00a0', '')
                        try:
                            car.mileage_km = int(km_str)
                        except ValueError:
                            pass

                elif handler == 'date':
                    # Format: 09.2015 -> 2015-09-01
                    match = re.search(r'(\d{2})\.(\d{4})', value_text)
                    if match:
                        month, year = match.groups()
                        car.registration_date = f"{year}-{month}-01"
                        car.year = int(year)

                elif handler == 'cv':
                    match = re.search(r'(\d{1,2})', value_text)
                    if match:
                        car.cv_fiscal = int(match.group(1))

                elif handler == 'number':
                    match = re.search(r'(\d{2,3})', value_text)
                    if match:
                        car.cv_din = int(match.group(1))

                elif handler == 'digit':
                    match = re.search(r'(\d)', value_text)
                    if match:
                        setattr(car, attr, int(match.group(1)))

                elif handler == 'transmission':
                    value_lower = value_text.lower()
                    if 'automatique' in value_lower or 'auto' in value_lower:
                        car.transmission = 'Automatique'
                    elif 'manuelle' in value_lower or 'manuel' in value_lower:
                        car.transmission = 'Manuelle'

                elif handler == 'text':
                    # Clean up the value
                    value = value_text.strip()
                    if value:
                        setattr(car, attr, value)

                break

    def _extract_price(self, car: UsedCar, soup: BeautifulSoup, page_text: str):
        """Extract price from page"""
        if car.price_tnd:
            return

        # Look for price in h2 containing "Prix demandé"
        for h2 in soup.find_all('h2'):
            text = h2.get_text(strip=True)
            if 'prix' in text.lower():
                match = re.search(r'([\d\s\u00a0]+)\s*(?:DT|TND)', text)
                if match:
                    price_str = match.group(1).replace(' ', '').replace('\u00a0', '')
                    try:
                        car.price_tnd = int(price_str)
                        return
                    except ValueError:
                        pass

        # Fallback: regex on page text
        match = re.search(r'(\d{2,3}[\s\u00a0]?\d{3})\s*(?:DT|TND)', page_text)
        if match:
            price_str = match.group(1).replace(' ', '').replace('\u00a0', '')
            try:
                car.price_tnd = int(price_str)
            except ValueError:
                pass

        # Look for price evaluation (Bon prix, Prix élevé, etc.)
        eval_patterns = ['bon prix', 'prix élevé', 'très bon prix', 'prix correct', 'bonne affaire']
        text_lower = page_text.lower()
        for pattern in eval_patterns:
            if pattern in text_lower:
                car.price_evaluation = pattern.title()
                break

    def _extract_equipment(self, car: UsedCar, soup: BeautifulSoup):
        """Extract equipment lists by category"""

        equipment_categories = {
            'sécurité': 'equipment_safety',
            'securité': 'equipment_safety',
            'intérieur': 'equipment_interior',
            'interieur': 'equipment_interior',
            'intérieurs': 'equipment_interior',
            'interieurs': 'equipment_interior',
            'extérieur': 'equipment_exterior',
            'exterieur': 'equipment_exterior',
            'extérieurs': 'equipment_exterior',
            'exterieurs': 'equipment_exterior',
            'fonctionnel': 'equipment_functional',
            'fonctionnels': 'equipment_functional',
        }

        # Look for box-inner-title divs followed by checked-specs
        for box in soup.find_all('div', class_='box'):
            title_div = box.find('div', class_='box-inner-title')
            if not title_div:
                continue

            title_text = title_div.get_text(strip=True).lower()

            for category_key, attr in equipment_categories.items():
                if category_key in title_text:
                    # Find the checked-specs div
                    specs_div = box.find('div', class_='checked-specs')
                    if specs_div:
                        ul = specs_div.find('ul')
                        if ul:
                            items = []
                            for li in ul.find_all('li'):
                                # Get text from spec-value span
                                spec_span = li.find('span', class_='spec-value')
                                if spec_span:
                                    item = spec_span.get_text(strip=True)
                                else:
                                    item = li.get_text(strip=True)
                                if item and len(item) > 1:
                                    items.append(item)

                            if items:
                                setattr(car, attr, items)
                    break

    def _extract_phone(self, car: UsedCar, soup: BeautifulSoup):
        """Extract seller phone number"""

        # Look for phone patterns in CTA elements, links, or spans
        phone_pattern = re.compile(r'(\d{2}[\s.-]?\d{3}[\s.-]?\d{3})')

        # Check tel: links
        for link in soup.find_all('a', href=re.compile(r'^tel:')):
            href = link.get('href', '')
            phone = href.replace('tel:', '').replace('+216', '').strip()
            phone = re.sub(r'[\s.-]+', ' ', phone)
            if phone:
                car.seller_phone = phone
                return

        # Check buttons and CTAs
        for elem in soup.find_all(['button', 'a', 'span', 'div'], class_=re.compile(r'phone|tel|contact|cta', re.I)):
            text = elem.get_text(strip=True)
            match = phone_pattern.search(text)
            if match:
                phone = match.group(1)
                phone = re.sub(r'[\s.-]+', ' ', phone)
                car.seller_phone = phone
                return

        # Fallback: look for phone pattern anywhere with "appeler" context
        page_text = soup.get_text()
        if 'appeler' in page_text.lower():
            for match in phone_pattern.finditer(page_text):
                phone = match.group(1)
                phone = re.sub(r'[\s.-]+', ' ', phone)
                if len(phone.replace(' ', '')) >= 8:
                    car.seller_phone = phone
                    return

    async def scrape_all(self):
        """Main scraping function"""
        print("=" * 70)
        print("AUTOMOBILE.TN USED CARS SCRAPER")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.specific_brands:
            print(f"Filtering brands: {', '.join(self.specific_brands)}")
        if self.max_pages:
            print(f"Max pages: {self.max_pages}")

        async with httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            }
        ) as client:

            # Step 1: Get total pages
            print("\n[Step 1] Getting total pages...")
            total_pages = await self.get_total_pages(client)
            if not total_pages:
                print("Could not determine total pages!")
                return

            if self.max_pages:
                total_pages = min(total_pages, self.max_pages)
                print(f"   Limited to {total_pages} pages")

            # Step 2: Fetch all listing pages and collect car URLs
            print(f"\n[Step 2] Fetching {total_pages} listing pages...")
            all_car_urls = []
            seen_ids = set()

            for page in range(1, total_pages + 1):
                print(f"   Page {page}/{total_pages}...", end=" ")
                urls = await self.fetch_listing_page(client, page)
                print(f"{len(urls)} cars")

                # Deduplicate by ID
                for url in urls:
                    car_id = url.rstrip('/').split('/')[-1]
                    if car_id not in seen_ids:
                        seen_ids.add(car_id)
                        all_car_urls.append(url)

                self.stats["pages_scraped"] += 1

            self.stats["listings_found"] = len(all_car_urls)
            print(f"\n   Total unique car URLs: {len(all_car_urls)}")

            # Step 3: Fetch all car details concurrently
            print(f"\n[Step 3] Fetching car details...")

            tasks = [self.fetch_car_details(client, url) for url in all_car_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, UsedCar):
                    self.cars.append(result)
                    self.stats["cars_scraped"] += 1

            print(f"\n   Scraped {len(self.cars)} cars")

    def save_to_json(self, filename: str = "automobile_tn_used_cars.json"):
        """Save to JSON"""
        data = {
            "scraped_at": datetime.now().isoformat(),
            "stats": self.stats,
            "total": len(self.cars),
            "cars": [asdict(c) for c in self.cars]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved to {filename}")

    def save_to_csv(self, filename: str = "automobile_tn_used_cars.csv"):
        """Save to CSV"""
        if not self.cars:
            print("No cars to save")
            return

        fieldnames = list(UsedCar.__dataclass_fields__.keys())

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for car in self.cars:
                row = asdict(car)
                # Convert lists to semicolon-separated strings for CSV
                for key in ['equipment_safety', 'equipment_interior',
                            'equipment_exterior', 'equipment_functional']:
                    row[key] = '; '.join(row[key]) if row[key] else ''
                writer.writerow(row)

        print(f"Saved {len(self.cars)} cars to {filename}")

    def print_summary(self):
        """Print scraping summary"""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        print(f"\nStats:")
        print(f"   Pages scraped: {self.stats['pages_scraped']}")
        print(f"   Listings found: {self.stats['listings_found']}")
        print(f"   Cars scraped: {self.stats['cars_scraped']}")
        print(f"   With prices: {self.stats['with_price']}")
        print(f"   With equipment: {self.stats['with_equipment']}")
        print(f"   With phone: {self.stats['with_phone']}")

        if self.cars:
            prices = [c.price_tnd for c in self.cars if c.price_tnd]
            if prices:
                print(f"\nPrices: {min(prices):,} - {max(prices):,} TND (avg: {sum(prices)//len(prices):,})")

            years = [c.year for c in self.cars if c.year]
            if years:
                print(f"Years: {min(years)} - {max(years)}")

            mileages = [c.mileage_km for c in self.cars if c.mileage_km]
            if mileages:
                print(f"Mileage: {min(mileages):,} - {max(mileages):,} km")

            # Top brands
            brand_counts = {}
            for c in self.cars:
                brand_counts[c.brand] = brand_counts.get(c.brand, 0) + 1

            print(f"\nTop brands:")
            for brand, count in sorted(brand_counts.items(), key=lambda x: -x[1])[:10]:
                brand_cars = [c for c in self.cars if c.brand == brand]
                brand_prices = [c.price_tnd for c in brand_cars if c.price_tnd]
                if brand_prices:
                    print(f"   {brand}: {count} cars ({min(brand_prices):,} - {max(brand_prices):,} TND)")

            # Fuel type distribution
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
    parser = argparse.ArgumentParser(description='Scrape automobile.tn used cars')
    parser.add_argument('--max-pages', type=int, help='Maximum number of pages to scrape')
    parser.add_argument('--brands', type=str, help='Comma-separated brand slugs (e.g., bmw,audi,mercedes-benz)')
    args = parser.parse_args()

    specific_brands = None
    if args.brands:
        specific_brands = [b.strip() for b in args.brands.split(',')]

    scraper = UsedCarsScraper(max_pages=args.max_pages, specific_brands=specific_brands)
    await scraper.scrape_all()

    scraper.save_to_json()
    scraper.save_to_csv()
    scraper.print_summary()

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
