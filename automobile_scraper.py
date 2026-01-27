"""
automobile.tn New Cars Scraper (Lightweight)
=============================================
Fast async scraper using httpx + BeautifulSoup instead of crawl4ai.

Features:
- Extracts JSON-LD schema data from car detail pages
- Handles multi-trim model pages
- Detects "Nouveau" badge and "Populaire" cars
- 10 concurrent requests with 0.2s delay

Run:
    python automobile_scraper.py
    python automobile_scraper.py --brands alfa-romeo,citroen,chery

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
class CarTrim:
    """Complete car trim/version with all specs"""

    # Identification
    id: str = ""
    brand: str = ""
    model: str = ""
    trim: str = ""
    full_name: str = ""

    # URLs
    url: str = ""

    # Pricing
    price_tnd: Optional[int] = None
    price_original: Optional[int] = None
    discount_tnd: Optional[int] = None
    has_discount: bool = False

    # Engine & Performance
    engine_cc: Optional[int] = None
    cv_fiscal: Optional[int] = None
    cv_din: Optional[int] = None
    torque_nm: Optional[int] = None
    top_speed_kmh: Optional[int] = None
    acceleration_0_100: Optional[float] = None

    # Fuel & Consumption
    fuel_type: str = ""
    consumption_mixed: Optional[float] = None
    consumption_city: Optional[float] = None
    consumption_highway: Optional[float] = None
    co2_emissions: Optional[int] = None
    fuel_tank_liters: Optional[int] = None

    # Transmission & Drivetrain
    transmission: str = ""
    gearbox_speeds: Optional[int] = None
    drivetrain: str = ""

    # Dimensions
    length_mm: Optional[int] = None
    width_mm: Optional[int] = None
    height_mm: Optional[int] = None
    wheelbase_mm: Optional[int] = None
    trunk_liters: Optional[int] = None
    weight_kg: Optional[int] = None

    # Other specs
    body_type: str = ""
    doors: Optional[int] = None
    seats: Optional[int] = None
    warranty_years: Optional[int] = None

    # Electric specific
    is_electric: bool = False
    is_hybrid: bool = False
    battery_kwh: Optional[float] = None
    range_km: Optional[int] = None

    # New fields
    is_new: bool = False  # Has "Nouveau" badge
    is_populaire: bool = False  # Government-subsidized car

    # Dealer
    concessionnaire: str = ""

    # Metadata
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class AutomobileScraper:
    """Fast async scraper for automobile.tn new cars"""

    BASE_URL = "https://www.automobile.tn"
    NEUF_URL = "https://www.automobile.tn/fr/neuf"

    # Rate limiting
    MAX_CONCURRENT = 10
    DELAY_BETWEEN_REQUESTS = 0.2

    # Slugs to skip
    SKIP_BRAND_SLUGS = {'electrique', 'comparateur', 'concessionnaires'}
    SKIP_MODEL_SLUGS = {'devis', 'comparateur'}

    def __init__(self, specific_brands: List[str] = None):
        self.cars: List[CarTrim] = []
        self.specific_brands = specific_brands
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        self.stats = {
            "brands": 0,
            "models": 0,
            "trims": 0,
            "with_price": 0,
            "with_discount": 0,
            "populaire": 0,
            "nouveau": 0
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

    async def fetch_brands(self, client: httpx.AsyncClient) -> List[dict]:
        """Get all brands from /fr/neuf"""
        print("\n[Step 1] Fetching brands...")

        html = await self.fetch(client, self.NEUF_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        brands = []
        seen = set()

        # Find brand links: /fr/neuf/{brand}
        for link in soup.find_all('a', href=re.compile(r'^/fr/neuf/[a-z0-9-]+$')):
            href = link.get('href', '')
            slug = href.split('/')[-1]

            if href in seen or slug in self.SKIP_BRAND_SLUGS:
                continue
            seen.add(href)

            # Filter specific brands if provided
            if self.specific_brands and slug not in self.specific_brands:
                continue

            # Get brand name from img alt or link text
            img = link.find('img')
            name = img.get('alt', '') if img else link.get_text(strip=True)
            if not name or len(name) > 50:
                name = slug.replace('-', ' ').title()

            brands.append({
                "name": name,
                "slug": slug,
                "url": f"{self.BASE_URL}{href}"
            })

        self.stats["brands"] = len(brands)
        print(f"   Found {len(brands)} brands")
        return brands

    async def fetch_brand_page(self, client: httpx.AsyncClient, brand: dict) -> List[dict]:
        """Get all car URLs from a brand page, handling both single-trim and multi-trim pages.
        Returns list of dicts with 'url' and 'is_new' keys."""
        html = await self.fetch(client, brand["url"])
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')
        car_info = []  # List of {'url': ..., 'is_new': ...}
        model_pages = []  # Pages that list multiple trims

        # Find all links to car/model pages - match any depth
        # Note: slugs can contain dots (e.g., "2.0-turbo-bva-super")
        pattern = re.compile(rf'^/fr/neuf/{re.escape(brand["slug"])}/[a-z0-9.-]+(?:/[a-z0-9.-]+)*$')

        for link in soup.find_all('a', href=pattern):
            href = link.get('href', '')
            parts = href.split('/')

            # Skip special pages
            if len(parts) >= 5 and parts[4] in self.SKIP_MODEL_SLUGS:
                continue

            full_url = f"{self.BASE_URL}{href}"

            if len(parts) >= 6:
                # Direct car page: /fr/neuf/{brand}/{model}/{trim}
                if not any(c['url'] == full_url for c in car_info):
                    car_info.append({'url': full_url, 'is_new': False})
            elif len(parts) == 5:
                # Could be model page with multiple trims: /fr/neuf/{brand}/{model}
                if full_url not in model_pages:
                    model_pages.append(full_url)

        # For model pages, fetch them to find trim links or parse version table
        for model_url in model_pages:
            trim_info = await self._fetch_model_trims(client, model_url, brand["slug"])
            for info in trim_info:
                if not any(c['url'] == info['url'] for c in car_info):
                    car_info.append(info)

        return car_info

    async def _fetch_model_trims(self, client: httpx.AsyncClient, model_url: str, brand_slug: str) -> List[dict]:
        """Fetch a model page and extract individual trim URLs from version table.
        Returns list of dicts with 'url' and 'is_new' keys."""
        html = await self.fetch(client, model_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'lxml')

        # Check if this is actually a car detail page (has JSON-LD Car schema)
        json_ld = self._extract_json_ld(soup)
        if json_ld and json_ld.get('@type') == 'Car':
            # This is a car page, not a model listing page
            return [{'url': model_url, 'is_new': False}]

        # This is a model page - find all trim links in tables or anywhere
        trim_info = []
        model_slug = model_url.rstrip('/').split('/')[-1]
        pattern = re.compile(rf'^/fr/neuf/{re.escape(brand_slug)}/{re.escape(model_slug)}/[a-z0-9.-]+$')

        # Look for links in version tables and elsewhere
        for link in soup.find_all('a', href=pattern):
            href = link.get('href', '')
            # Skip "Fiche technique" links that just go back to same page
            link_text = link.get_text(strip=True).lower()
            if 'fiche technique' in link_text or 'devis' in link_text:
                continue
            full_url = f"{self.BASE_URL}{href}"

            # Check if this version has the "Nouveau" badge
            # Look for span.nouveau in the parent row/container
            is_new = False
            parent = link.parent
            for _ in range(5):  # Walk up to 5 levels
                if parent is None:
                    break
                if parent.find(class_='nouveau'):
                    is_new = True
                    break
                parent = parent.parent

            if not any(t['url'] == full_url for t in trim_info):
                trim_info.append({'url': full_url, 'is_new': is_new})

        # If no trim links found, this model page itself may have the data
        return trim_info if trim_info else [{'url': model_url, 'is_new': False}]

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

    async def fetch_car_details(self, client: httpx.AsyncClient, url: str, is_new_from_listing: bool = False) -> Optional[CarTrim]:
        """Fetch and parse a car detail page"""
        html = await self.fetch(client, url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')
        page_text = soup.get_text(separator=' ', strip=True)

        # Extract URL parts for brand/model/trim
        # URL: https://www.automobile.tn/fr/neuf/{brand}/{model}/{trim}
        # parts[0]=https:, [1]='', [2]=www.automobile.tn, [3]=fr, [4]=neuf, [5]=brand, [6]=model, [7]=trim
        parts = url.rstrip('/').split('/')
        brand_slug = parts[5] if len(parts) > 5 else ""
        model_slug = parts[6] if len(parts) > 6 else ""
        trim_slug = parts[7] if len(parts) > 7 else ""

        car = CarTrim(url=url)
        car.is_new = is_new_from_listing  # Set from listing page badge

        # Priority 1: Extract from JSON-LD (detail pages have @type: Car)
        json_ld = self._extract_json_ld(soup)
        if json_ld:
            self._parse_json_ld(car, json_ld)

        # Set brand from URL (more reliable than JSON-LD model field)
        car.brand = brand_slug.replace('-', ' ').title()

        # Priority 2: Parse page title to clean up full name
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Extract car name from title like "Prix Alfa Romeo Giulia 2.0 Turbo Super BVA neuve - 198 000 DT"
            title_match = re.match(r'Prix\s+(.+?)\s+neuve', title, re.I)
            if title_match:
                car.full_name = title_match.group(1).strip()

        # Parse model/trim from URL if not fully set from JSON-LD
        if not car.model or car.model == car.brand:
            car.model = model_slug.replace('-', ' ').title()
        if not car.trim:
            car.trim = trim_slug.replace('-', ' ').title() if trim_slug else "Base"

        # If full_name not set, build from parts
        if not car.full_name:
            car.full_name = f"{car.brand} {car.model} {car.trim}".strip()

        # Priority 3: Parse spec table (Fiche technique)
        self._parse_spec_table(car, soup)

        # Priority 4: Fallback regex extraction from page text
        self._extract_from_text(car, page_text)

        # Detect special flags
        car.is_populaire = 'populaire' in url.lower() or 'populaire' in car.full_name.lower()
        # is_new is already set from the listing page badge

        # Determine fuel type and body type
        self._determine_fuel_type(car)
        self._determine_body_type(car)

        # Generate ID
        self._generate_id(car)

        # Update stats
        if car.price_tnd:
            self.stats["with_price"] += 1
        if car.has_discount:
            self.stats["with_discount"] += 1
        if car.is_populaire:
            self.stats["populaire"] += 1
        if car.is_new:
            self.stats["nouveau"] += 1

        return car

    def _parse_json_ld(self, car: CarTrim, data: dict):
        """Parse JSON-LD schema data into CarTrim"""
        car.full_name = data.get('name', '')

        # Extract brand from brand object or name
        brand_data = data.get('brand', {})
        if isinstance(brand_data, dict):
            car.brand = brand_data.get('name', '')

        # Extract model - JSON-LD "model" field often contains "Brand Model"
        model_field = data.get('model', '')
        if model_field:
            # Remove brand prefix if present
            if car.brand and model_field.startswith(car.brand):
                car.model = model_field[len(car.brand):].strip()
            else:
                car.model = model_field

        # Extract trim from full name (after brand and model)
        if car.full_name and car.brand and car.model:
            prefix = f"{car.brand} {car.model}"
            if car.full_name.startswith(prefix):
                car.trim = car.full_name[len(prefix):].strip() or "Base"

        # Price from offers
        offers = data.get('offers', {})
        if isinstance(offers, dict):
            price = offers.get('price')
            if price:
                try:
                    car.price_tnd = int(float(price))
                except (ValueError, TypeError):
                    pass

        # Body and fuel type
        car.body_type = data.get('bodyType', '')
        fuel = data.get('fuelType', '').lower()
        if fuel:
            car.fuel_type = fuel

        # Additional specs from JSON-LD
        if data.get('accelerationTime'):
            try:
                car.acceleration_0_100 = float(data['accelerationTime'])
            except (ValueError, TypeError):
                pass

        if data.get('cargoVolume'):
            try:
                car.trunk_liters = int(float(data['cargoVolume']))
            except (ValueError, TypeError):
                pass

        if data.get('depth'):  # length
            try:
                car.length_mm = int(float(data['depth']))
            except (ValueError, TypeError):
                pass

        if data.get('width'):
            try:
                car.width_mm = int(float(data['width']))
            except (ValueError, TypeError):
                pass

        if data.get('height'):
            try:
                car.height_mm = int(float(data['height']))
            except (ValueError, TypeError):
                pass

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

        # Drivetrain from vehicleTransmission (in French, this often contains drivetrain info)
        transmission = data.get('vehicleTransmission', '').lower()
        if transmission:
            if transmission == 'propulsion':
                car.drivetrain = 'RWD'
            elif transmission == 'traction':
                car.drivetrain = 'FWD'
            elif transmission in ['awd', '4wd', '4x4', 'intégrale']:
                car.drivetrain = 'AWD'

    def _parse_spec_table(self, car: CarTrim, soup: BeautifulSoup):
        """Parse technical specifications from tables"""

        # Spec label to attribute mapping
        spec_map = {
            'cylindrée': ('engine_cc', r'(\d{3,4})'),
            'puissance fiscale': ('cv_fiscal', r'(\d{1,2})'),
            'cv fiscaux': ('cv_fiscal', r'(\d{1,2})'),
            'puissance': ('cv_din', r'(\d{2,3})'),
            'couple': ('torque_nm', r'(\d{2,3})'),
            'vitesse max': ('top_speed_kmh', r'(\d{3})'),
            '0-100': ('acceleration_0_100', r'(\d+[.,]?\d*)'),
            '0 à 100': ('acceleration_0_100', r'(\d+[.,]?\d*)'),
            'consommation mixte': ('consumption_mixed', r'(\d+[.,]?\d*)'),
            'consommation urbaine': ('consumption_city', r'(\d+[.,]?\d*)'),
            'consommation extra': ('consumption_highway', r'(\d+[.,]?\d*)'),
            'co2': ('co2_emissions', r'(\d{2,3})'),
            'émission': ('co2_emissions', r'(\d{2,3})'),
            'réservoir': ('fuel_tank_liters', r'(\d{2,3})'),
            'boîte': ('transmission', None),
            'longueur': ('length_mm', r'(\d{4,5})'),
            'largeur': ('width_mm', r'(\d{4,5})'),
            'hauteur': ('height_mm', r'(\d{4,5})'),
            'empattement': ('wheelbase_mm', r'(\d{4,5})'),
            'coffre': ('trunk_liters', r'(\d{2,4})'),
            'poids': ('weight_kg', r'(\d{3,4})'),
            'masse': ('weight_kg', r'(\d{3,4})'),
            'places': ('seats', r'(\d)'),
            'portes': ('doors', r'(\d)'),
            'garantie': ('warranty_years', r'(\d)'),
            'batterie': ('battery_kwh', r'(\d+[.,]?\d*)'),
            'autonomie': ('range_km', r'(\d{2,4})'),
        }

        # Parse tables
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    self._apply_spec(car, label, value, spec_map)

        # Parse definition lists (dl/dt/dd)
        for dl in soup.find_all('dl'):
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)
                self._apply_spec(car, label, value, spec_map)

    def _apply_spec(self, car: CarTrim, label: str, value: str, spec_map: dict):
        """Apply a single spec value to car"""
        for key, (attr, pattern) in spec_map.items():
            if key in label:
                current = getattr(car, attr, None)
                if current is not None and current != "" and current != 0:
                    continue  # Don't overwrite existing values

                if attr == 'transmission':
                    if 'auto' in value.lower():
                        car.transmission = 'automatic'
                    elif 'manuel' in value.lower():
                        car.transmission = 'manual'
                    # Extract gearbox speeds
                    speed_match = re.search(r'(\d)', value)
                    if speed_match:
                        car.gearbox_speeds = int(speed_match.group(1))
                elif pattern:
                    match = re.search(pattern, value)
                    if match:
                        val = match.group(1).replace(',', '.')
                        if attr in ('acceleration_0_100', 'consumption_mixed', 'consumption_city',
                                   'consumption_highway', 'battery_kwh'):
                            setattr(car, attr, float(val))
                        else:
                            setattr(car, attr, int(float(val)))
                break

    def _extract_from_text(self, car: CarTrim, text: str):
        """Fallback regex extraction from page text"""

        # Price (if not already set)
        if not car.price_tnd:
            price_match = re.search(r'(\d{2,3}[\s\u00a0]?\d{3})\s*(?:DT|TND)', text)
            if price_match:
                price_str = price_match.group(1).replace(' ', '').replace('\u00a0', '')
                try:
                    car.price_tnd = int(price_str)
                except ValueError:
                    pass

        # Check for discount
        discount_patterns = [
            r'au\s*lieu\s*de\s*(\d{2,3}[\s\u00a0]?\d{3})',
            r'était\s*(\d{2,3}[\s\u00a0]?\d{3})',
            r'prix\s*barré\s*:?\s*(\d{2,3}[\s\u00a0]?\d{3})',
        ]
        for pattern in discount_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                old_price_str = match.group(1).replace(' ', '').replace('\u00a0', '')
                try:
                    car.price_original = int(old_price_str)
                    if car.price_tnd and car.price_original > car.price_tnd:
                        car.discount_tnd = car.price_original - car.price_tnd
                        car.has_discount = True
                except ValueError:
                    pass
                break

        # CV fiscal (if not set)
        if not car.cv_fiscal:
            cv_match = re.search(r'(\d{1,2})\s*(?:CV|cv)\s*(?:fiscaux|fiscal)?', text)
            if cv_match:
                car.cv_fiscal = int(cv_match.group(1))

        # Engine CC (if not set)
        if not car.engine_cc:
            cc_match = re.search(r'(\d{3,4})\s*(?:cc|cm3|cm³)', text, re.I)
            if cc_match:
                car.engine_cc = int(cc_match.group(1))

        # Transmission (if not set)
        if not car.transmission:
            text_lower = text.lower()
            if any(x in text_lower for x in ['automatique', 'bva', 'dsg', 'dct', 'cvt', 'eat']):
                car.transmission = 'automatic'
            elif any(x in text_lower for x in ['manuelle', 'bvm']):
                car.transmission = 'manual'

        # Drivetrain
        if not car.drivetrain:
            text_lower = text.lower()
            if any(x in text_lower for x in ['4x4', 'awd', '4motion', 'quattro', 'xdrive', '4wd', 'q4', '4matic']):
                car.drivetrain = 'AWD'
            elif any(x in text_lower for x in ['propulsion', 'rwd']):
                car.drivetrain = 'RWD'
            else:
                car.drivetrain = 'FWD'

        # Concessionnaire - look for specific patterns
        if not car.concessionnaire:
            # Look for dealer name after label
            dealer_match = re.search(r'(?:concessionnaire|distributeur|importateur|représentant)\s*:?\s*([A-Za-zÀ-ÿ0-9\s&-]{3,50}?)(?:\s*[|\n]|$)', text, re.I)
            if dealer_match:
                dealer = dealer_match.group(1).strip()
                # Filter out generic/garbage text
                noise_words = ['comparateur', 'occasions', 'recherche', 'annonces', 'jour', 'fiche', 'technique']
                if not any(word in dealer.lower() for word in noise_words) and len(dealer) > 2:
                    car.concessionnaire = dealer

    def _determine_fuel_type(self, car: CarTrim):
        """Determine fuel type from car details"""
        if car.fuel_type:
            # Normalize existing fuel type
            fuel_lower = car.fuel_type.lower()
            if 'electr' in fuel_lower or fuel_lower == 'ev':
                car.fuel_type = 'electric'
                car.is_electric = True
            elif 'hybrid' in fuel_lower or 'hybride' in fuel_lower:
                if 'plug' in fuel_lower or 'rechargeable' in fuel_lower:
                    car.fuel_type = 'hybrid_rechargeable'
                else:
                    car.fuel_type = 'hybrid'
                car.is_hybrid = True
            elif 'diesel' in fuel_lower:
                car.fuel_type = 'diesel'
            elif 'essence' in fuel_lower or 'gasoline' in fuel_lower or 'petrol' in fuel_lower:
                car.fuel_type = 'essence'
            return

        # Infer from name
        name_lower = car.full_name.lower()
        if any(x in name_lower for x in ['électrique', 'electric', 'ev', 'e-tron', 'id.', 'bev']):
            car.fuel_type = 'electric'
            car.is_electric = True
        elif any(x in name_lower for x in ['plug-in', 'phev', 'rechargeable', 'e-hybrid']):
            car.fuel_type = 'hybrid_rechargeable'
            car.is_hybrid = True
        elif any(x in name_lower for x in ['hybrid', 'hybride', 'mhev']):
            car.fuel_type = 'hybrid'
            car.is_hybrid = True
        elif any(x in name_lower for x in ['diesel', 'tdi', 'hdi', 'dci', 'cdti', 'bluehdi']):
            car.fuel_type = 'diesel'
        else:
            car.fuel_type = 'essence'

    def _determine_body_type(self, car: CarTrim):
        """Determine body type from car details"""
        if car.body_type:
            return

        name_lower = car.full_name.lower()

        if any(x in name_lower for x in ['suv', 'crossover']):
            car.body_type = 'SUV'
        elif any(x in name_lower for x in ['berline', 'sedan']):
            car.body_type = 'Berline'
        elif any(x in name_lower for x in ['citadine']):
            car.body_type = 'Citadine'
        elif any(x in name_lower for x in ['break', 'touring', 'avant', 'sw']):
            car.body_type = 'Break'
        elif any(x in name_lower for x in ['coupé', 'coupe']):
            car.body_type = 'Coupe'
        elif any(x in name_lower for x in ['pick-up', 'pickup']):
            car.body_type = 'Pick-up'
        elif any(x in name_lower for x in ['monospace', 'mpv']):
            car.body_type = 'Monospace'
        else:
            car.body_type = 'Compacte'

    def _generate_id(self, car: CarTrim):
        """Generate unique ID from brand/model/trim"""
        clean = lambda s: re.sub(r'[^a-z0-9]', '_', s.lower())
        car.id = f"{clean(car.brand)}_{clean(car.model)}_{clean(car.trim)}"

    async def scrape_all(self):
        """Main scraping function"""
        print("=" * 70)
        print("AUTOMOBILE.TN NEW CARS SCRAPER (Lightweight)")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.specific_brands:
            print(f"Filtering brands: {', '.join(self.specific_brands)}")

        async with httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            }
        ) as client:

            # Step 1: Get all brands
            brands = await self.fetch_brands(client)
            if not brands:
                print("No brands found!")
                return

            # Step 2: Get all car URLs from each brand
            print(f"\n[Step 2] Fetching models from {len(brands)} brands...")
            all_car_info = []  # List of {'url': ..., 'is_new': ...}

            for i, brand in enumerate(brands, 1):
                print(f"   [{i}/{len(brands)}] {brand['name']}...", end=" ")
                car_info = await self.fetch_brand_page(client, brand)
                print(f"{len(car_info)} cars")
                all_car_info.extend(car_info)
                self.stats["models"] += len(car_info)

            # Deduplicate by URL
            seen_urls = set()
            unique_car_info = []
            for info in all_car_info:
                if info['url'] not in seen_urls:
                    seen_urls.add(info['url'])
                    unique_car_info.append(info)
            all_car_info = unique_car_info
            print(f"\n   Total unique car URLs: {len(all_car_info)}")

            # Step 3: Fetch all car details concurrently
            print(f"\n[Step 3] Fetching car details...")

            tasks = [self.fetch_car_details(client, info['url'], info.get('is_new', False))
                     for info in all_car_info]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, CarTrim) and result.price_tnd:
                    self.cars.append(result)
                    self.stats["trims"] += 1

            print(f"\n   Scraped {len(self.cars)} cars with prices")

    def save_to_json(self, filename: str = "automobile_tn_new_cars.json"):
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

    def save_to_csv(self, filename: str = "automobile_tn_new_cars.csv"):
        """Save to CSV"""
        if not self.cars:
            print("No cars to save")
            return

        fieldnames = list(CarTrim.__dataclass_fields__.keys())

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for car in self.cars:
                writer.writerow(asdict(car))

        print(f"Saved {len(self.cars)} cars to {filename}")

    def print_summary(self):
        """Print scraping summary"""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        print(f"\nStats:")
        print(f"   Brands: {self.stats['brands']}")
        print(f"   Car URLs: {self.stats['models']}")
        print(f"   Cars scraped: {self.stats['trims']}")
        print(f"   With prices: {self.stats['with_price']}")
        print(f"   With discounts: {self.stats['with_discount']}")
        print(f"   Populaire cars: {self.stats['populaire']}")
        print(f"   Nouveau badge: {self.stats['nouveau']}")

        if self.cars:
            prices = [c.price_tnd for c in self.cars if c.price_tnd]
            if prices:
                print(f"\nPrices: {min(prices):,} - {max(prices):,} TND (avg: {sum(prices)//len(prices):,})")

            # Top brands
            brand_counts = {}
            for c in self.cars:
                brand_counts[c.brand] = brand_counts.get(c.brand, 0) + 1

            print(f"\nTop brands:")
            for brand, count in sorted(brand_counts.items(), key=lambda x: -x[1])[:10]:
                brand_prices = [c.price_tnd for c in self.cars if c.brand == brand and c.price_tnd]
                if brand_prices:
                    print(f"   {brand}: {count} cars ({min(brand_prices):,} - {max(brand_prices):,} TND)")

            # Show populaire cars
            populaire = [c for c in self.cars if c.is_populaire]
            if populaire:
                print(f"\nPopulaire cars ({len(populaire)}):")
                for c in populaire[:5]:
                    print(f"   {c.full_name}: {c.price_tnd:,} TND")

            # Show nouveau cars
            nouveau = [c for c in self.cars if c.is_new]
            if nouveau:
                print(f"\nNouveau badge ({len(nouveau)}):")
                for c in nouveau[:5]:
                    print(f"   {c.full_name}: {c.price_tnd:,} TND")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description='Scrape automobile.tn new cars')
    parser.add_argument('--brands', type=str, help='Comma-separated brand slugs (e.g., alfa-romeo,citroen,chery)')
    args = parser.parse_args()

    specific_brands = None
    if args.brands:
        specific_brands = [b.strip() for b in args.brands.split(',')]

    scraper = AutomobileScraper(specific_brands=specific_brands)
    await scraper.scrape_all()

    scraper.save_to_json()
    scraper.save_to_csv()
    scraper.print_summary()

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
