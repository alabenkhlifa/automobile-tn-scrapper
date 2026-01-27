"""
automobile.tn COMPLETE New Cars Scraper (FIXED)
===============================================
Crawls ALL brands → models → trims with full specs and prices.

Structure discovered:
  /fr/neuf                              → List of all brands
  /fr/neuf/{brand}                      → Models in "versions-item" divs
  /fr/neuf/{brand}/{model}/{trim}       → Full URL includes trim
  
  Model pages have trim tables with specs

Run:
    python scraper_full.py

Requirements:
    pip install crawl4ai beautifulsoup4 lxml
"""

import asyncio
import json
import csv
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List
from bs4 import BeautifulSoup

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


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
    model_url: str = ""
    
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

class AutomobileTnScraper:
    """Complete scraper for automobile.tn new cars"""

    BASE_URL = "https://www.automobile.tn"
    NEUF_URL = "https://www.automobile.tn/fr/neuf"

    # Slugs to skip when processing brands and models
    SKIP_BRAND_SLUGS = {'electrique', 'comparateur', 'concessionnaires'}
    SKIP_MODEL_SLUGS = {'devis', 'comparateur'}

    # Noise words to filter from trim names (other brands, promo text, etc.)
    NOISE_BRAND_NAMES = {
        'mercedes', 'bmw', 'audi', 'volkswagen', 'toyota', 'honda', 'hyundai',
        'kia', 'nissan', 'ford', 'peugeot', 'renault', 'citroen', 'fiat',
        'jeep', 'land rover', 'range rover', 'jaguar', 'volvo', 'mazda',
        'mitsubishi', 'suzuki', 'subaru', 'lexus', 'infiniti', 'porsche',
        'ferrari', 'lamborghini', 'maserati', 'bentley', 'rolls royce',
        'ssangyong', 'rexton', 'prado', 'civic', 'corolla', 'camry', 'rav4',
        'tiguan', 'golf', 'polo', 'passat', 'evoque', 'defender', 'discovery',
        'byd', 'chery', 'changan', 'haval', 'geely', 'mg', 'opel', 'seat',
        'skoda', 'dacia', 'mini', 'smart', 'tesla', 'rivian', 'lucid',
        # Model names from other brands
        'sportage', 'tucson', 'sorento', 'ceed', 'stonic', 'seltos',
        'qashqai', 'juke', 'x-trail', 'leaf', 'ariya',
        'focus', 'fiesta', 'kuga', 'mustang', 'explorer',
        'clio', 'megane', 'captur', 'kadjar', 'arkana',
        'c3', 'c4', 'c5', 'berlingo', 'picasso'
    }
    NOISE_WORDS = {
        'promo', 'nouveau', 'nouvelle', 'new', 'demander', 'devis', 'comparateur',
        'comparer', 'voir', 'details', 'fiche', 'technique', 'prix', 'tarif',
        'offre', 'special', 'remise', 'reduction', 'economie', 'gratuit',
        # UI elements
        'ouvrir', 'fermer', 'plus', 'moins', 'cliquez', 'click', 'ici', 'here',
        'afficher', 'masquer', 'show', 'hide', 'close', 'open',
        # Generic/promo terms
        'version', 'best', 'deals', 'weeks', 'black', 'friday', 'soldes',
        'promotion', 'limited', 'edition', 'exclusive'
    }
    
    def __init__(self):
        self.cars: List[CarTrim] = []
        self.browser_config = BrowserConfig(headless=True, verbose=False)
        self.stats = {"brands": 0, "models": 0, "trims": 0, "with_price": 0, "with_discount": 0}
    
    async def get_all_brands(self, crawler: AsyncWebCrawler) -> List[dict]:
        """Get all brands from /fr/neuf"""
        
        print("\n📋 STEP 1: Fetching all brands...")
        
        config = CrawlerRunConfig(page_timeout=60000, delay_before_return_html=2.0)
        result = await crawler.arun(url=self.NEUF_URL, config=config)
        
        if not result.success:
            print(f"❌ Failed: {result.error_message}")
            return []
        
        soup = BeautifulSoup(result.html, 'lxml')
        brands = []
        
        # Find brand links: /fr/neuf/{brand} (but not special pages)
        brand_links = soup.find_all('a', href=re.compile(r'^/fr/neuf/[a-z0-9-]+$'))

        seen = set()
        for link in brand_links:
            href = link.get('href', '')
            slug = href.split('/')[-1]

            if href in seen or slug in self.SKIP_BRAND_SLUGS:
                continue
            seen.add(href)
            
            name = link.get_text(strip=True)
            if not name or len(name) > 50:
                name = slug.replace('-', ' ').title()
            
            brands.append({
                "name": name,
                "slug": slug,
                "url": f"{self.BASE_URL}{href}"
            })
        
        self.stats["brands"] = len(brands)
        print(f"✅ Found {len(brands)} brands")
        return brands
    
    async def get_brand_models(self, crawler: AsyncWebCrawler, brand: dict) -> List[dict]:
        """Get all models for a brand from versions-item divs"""
        
        config = CrawlerRunConfig(page_timeout=60000, delay_before_return_html=2.0)
        result = await crawler.arun(url=brand["url"], config=config)
        
        if not result.success:
            return []
        
        soup = BeautifulSoup(result.html, 'lxml')
        models = []
        
        # Method 1: Find "versions-item" divs (discovered from debug)
        version_items = soup.find_all(class_='versions-item')
        
        for item in version_items:
            # Find the link inside
            link = item.find('a', href=re.compile(rf'/fr/neuf/{brand["slug"]}/'))
            if not link:
                continue
            
            href = link.get('href', '')
            
            # Extract model name from URL: /fr/neuf/alfa-romeo/giulia/trim -> giulia
            parts = href.split('/')
            if len(parts) >= 5:
                model_slug = parts[4]  # giulia, stelvio, etc.
                # Skip non-model slugs
                if model_slug in self.SKIP_MODEL_SLUGS:
                    continue
            else:
                continue
            
            # Get display name and price from the item text
            item_text = item.get_text(separator=' ', strip=True)
            
            # Extract model name (e.g., "Alfa Romeo Giulia")
            name_match = re.search(rf'{brand["name"]}\s+(\S+)', item_text, re.I)
            model_name = name_match.group(1) if name_match else model_slug.replace('-', ' ').title()
            
            # Extract starting price
            price_match = re.search(r'(\d{2,3}[\s\u00a0]?\d{3})\s*DT', item_text)
            starting_price = None
            if price_match:
                price_str = price_match.group(1).replace(' ', '').replace('\u00a0', '')
                try:
                    starting_price = int(price_str)
                except:
                    pass
            
            # Build model page URL (without trim)
            model_url = f"{self.BASE_URL}/fr/neuf/{brand['slug']}/{model_slug}"
            
            # Check if we already have this model
            if not any(m['slug'] == model_slug for m in models):
                models.append({
                    "name": model_name,
                    "slug": model_slug,
                    "url": model_url,
                    "brand": brand["name"],
                    "brand_slug": brand["slug"],
                    "starting_price": starting_price
                })
        
        # Method 2: Also check for direct model links in case versions-item is not used
        if not models:
            # Look for links with pattern /fr/neuf/{brand}/{model}/...
            all_links = soup.find_all('a', href=re.compile(rf'^/fr/neuf/{brand["slug"]}/[a-z0-9-]+'))
            
            seen_models = set()
            for link in all_links:
                href = link.get('href', '')
                parts = href.split('/')
                
                if len(parts) >= 5:
                    model_slug = parts[4]
                    
                    # Skip special pages
                    if model_slug in {'devis', 'comparateur'}:
                        continue
                    
                    if model_slug not in seen_models:
                        seen_models.add(model_slug)
                        
                        model_url = f"{self.BASE_URL}/fr/neuf/{brand['slug']}/{model_slug}"
                        
                        models.append({
                            "name": model_slug.replace('-', ' ').title(),
                            "slug": model_slug,
                            "url": model_url,
                            "brand": brand["name"],
                            "brand_slug": brand["slug"],
                            "starting_price": None
                        })
        
        return models
    
    async def get_model_trims(self, crawler: AsyncWebCrawler, model: dict) -> List[CarTrim]:
        """Get all trims with specs for a model"""
        
        config = CrawlerRunConfig(page_timeout=60000, delay_before_return_html=2.5)
        result = await crawler.arun(url=model["url"], config=config)
        
        if not result.success:
            return []
        
        soup = BeautifulSoup(result.html, 'lxml')
        page_text = soup.get_text(separator=' ', strip=True)
        trims = []
        
        # Look for trim/version rows - usually in tables or specific divs
        # Pattern 1: Look for "versions-item" or similar containers
        version_containers = soup.find_all(class_=re.compile(r'version|finition|motorisation|trim', re.I))
        
        # Pattern 2: Look for tables with prices
        tables = soup.find_all('table')
        
        # Pattern 3: Look for divs with price information
        price_containers = soup.find_all(['div', 'tr', 'li'], string=re.compile(r'\d{2,3}\s?\d{3}\s*DT'))
        
        # First, try to find trim rows in tables
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_text = row.get_text(separator=' ', strip=True)

                # Check if this row has a price
                price_match = re.search(r'(\d{2,3}[\s\u00a0]?\d{3})\s*(?:DT|TND)', row_text)
                if price_match and len(row_text) > 10:
                    trim = self._parse_trim_from_text(model, row_text, price_match)
                    if trim:
                        trims.append(trim)

        # Try version containers
        for container in version_containers:
            container_text = container.get_text(separator=' ', strip=True)
            price_match = re.search(r'(\d{2,3}[\s\u00a0]?\d{3})\s*(?:DT|TND)', container_text)
            if price_match and len(container_text) > 10:
                trim = self._parse_trim_from_text(model, container_text, price_match)
                if trim and not any(t.trim == trim.trim and t.price_tnd == trim.price_tnd for t in trims):
                    trims.append(trim)
        
        # If no trims found, create one from page content
        # But don't create "Base" trim for non-model pages like "devis"
        if not trims and model["slug"] not in self.SKIP_MODEL_SLUGS:
            # Also check if URL contains "devis"
            if 'devis' not in model["url"].lower():
                price_match = re.search(r'(\d{2,3}[\s\u00a0]?\d{3})\s*(?:DT|TND)', page_text)
                if price_match:
                    trim = self._parse_trim_from_text(model, page_text, price_match)
                    if trim:
                        trim.trim = "Base"
                        trims.append(trim)
        
        # Extract common specs from the page and apply to all trims
        common_specs = self._extract_specs_from_page(soup, page_text)
        for trim in trims:
            self._apply_specs(trim, common_specs)
            self._determine_fuel_and_body(trim)
            self._generate_id(trim)
        
        self.stats["trims"] += len(trims)
        
        return trims
    
    def _contains_other_brand(self, text: str, current_brand: str) -> bool:
        """Check if text contains other car brand names (likely a comparison/promo section)"""
        text_lower = text.lower()
        current_brand_lower = current_brand.lower()

        for noise_brand in self.NOISE_BRAND_NAMES:
            # Skip if it's the current brand
            if noise_brand in current_brand_lower:
                continue
            if noise_brand in text_lower:
                return True
        return False

    def _is_valid_trim_name(self, trim_name: str, brand: str) -> bool:
        """Check if trim name is valid (not noise from other brands/promos)"""
        if not trim_name:
            return False

        trim_lower = trim_name.lower()

        # Check for other brand names in the trim
        for noise_brand in self.NOISE_BRAND_NAMES:
            if noise_brand in trim_lower and noise_brand not in brand.lower():
                return False

        # Check for noise words at the start
        first_word = trim_lower.split()[0] if trim_lower.split() else ''
        if first_word in self.NOISE_WORDS:
            return False

        # Check if entire trim is just noise words
        words = trim_lower.split()
        if all(w in self.NOISE_WORDS for w in words):
            return False

        # Check if majority of words are noise (e.g., "Iconic Line Black Weeks Deals")
        if len(words) > 2:
            noise_count = sum(1 for w in words if w in self.NOISE_WORDS)
            if noise_count >= len(words) - 1:  # Only 1 non-noise word
                return False

        # Filter out price-like patterns (e.g., "9.990 DT", "DT Fiche technique")
        if re.search(r'\d+[\.,]\d+\s*dt', trim_lower):
            return False
        if 'dt' in trim_lower and re.search(r'\d', trim_lower):
            return False

        # Filter out UI/page text fragments
        if 'fiche technique' in trim_lower:
            return False
        if 'devis gratuit' in trim_lower:
            return False

        # Filter out promo phrases
        promo_phrases = ['black weeks', 'black friday', 'deals', 'soldes', 'offre speciale']
        for phrase in promo_phrases:
            if phrase in trim_lower:
                return False

        return True

    def _clean_trim_name(self, trim_name: str) -> str:
        """Clean up trim name by removing noise prefixes"""
        if not trim_name:
            return trim_name

        # Remove common noise prefixes
        noise_prefixes = ['promo ', 'nouveau ', 'nouvelle ', 'new ', 'offre ']
        trim_lower = trim_name.lower()
        for prefix in noise_prefixes:
            if trim_lower.startswith(prefix):
                trim_name = trim_name[len(prefix):]
                break

        return trim_name.strip()

    def _parse_trim_from_text(self, model: dict, text: str, price_match) -> Optional[CarTrim]:
        """Parse a trim from text content"""

        trim = CarTrim(
            brand=model["brand"],
            model=model["name"],
            model_url=model["url"]
        )

        # Extract price
        price_str = price_match.group(1).replace(' ', '').replace('\u00a0', '')
        try:
            trim.price_tnd = int(price_str)
            self.stats["with_price"] += 1
        except:
            return None

        # Try to extract trim name
        # Common patterns: "2.0 Turbo BVA", "1.5 TSI DSG7 Style", etc.
        trim_patterns = [
            r'(\d\.\d\s*[A-Za-z0-9\s\-]+?)(?=\s*\d{2,3}\s?\d{3})',  # Before price
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # Capitalized words
        ]

        for pattern in trim_patterns:
            match = re.search(pattern, text)
            if match:
                potential_trim = match.group(1).strip()
                # Clean up - remove brand and model name
                potential_trim = potential_trim.replace(model["brand"], '').replace(model["name"], '').strip()
                potential_trim = self._clean_trim_name(potential_trim)

                # Validate the trim name
                if potential_trim and len(potential_trim) > 2 and len(potential_trim) < 50:
                    if self._is_valid_trim_name(potential_trim, model["brand"]):
                        trim.trim = potential_trim
                        break

        # If no valid trim name found, use "Standard" but mark for dedup
        if not trim.trim:
            trim.trim = "Standard"
        
        trim.full_name = f"{model['brand']} {model['name']} {trim.trim}".strip()
        
        # Check for discount
        discount_patterns = [
            r'au\s*lieu\s*de\s*(\d{2,3}[\s\u00a0]?\d{3})',
            r'était\s*(\d{2,3}[\s\u00a0]?\d{3})',
            r'(\d{2,3}[\s\u00a0]?\d{3})\s*(?:DT|TND)\s*(?:barré|rayé)',
        ]
        
        for pattern in discount_patterns:
            disc_match = re.search(pattern, text, re.I)
            if disc_match:
                old_price_str = disc_match.group(1).replace(' ', '').replace('\u00a0', '')
                try:
                    trim.price_original = int(old_price_str)
                    if trim.price_original > trim.price_tnd:
                        trim.discount_tnd = trim.price_original - trim.price_tnd
                        trim.has_discount = True
                        self.stats["with_discount"] += 1
                except:
                    pass
                break
        
        # Check for "promo" or "remise" keywords
        if not trim.has_discount and ('promo' in text.lower() or 'remise' in text.lower()):
            remise_match = re.search(r'(?:remise|économie|réduction)\s*:?\s*(\d[\d\s]*)\s*(?:DT|TND)?', text, re.I)
            if remise_match:
                disc_str = remise_match.group(1).replace(' ', '')
                try:
                    trim.discount_tnd = int(disc_str)
                    trim.price_original = trim.price_tnd + trim.discount_tnd
                    trim.has_discount = True
                    self.stats["with_discount"] += 1
                except:
                    pass
        
        # Extract inline specs
        self._extract_inline_specs(trim, text)
        
        return trim
    
    def _extract_inline_specs(self, trim: CarTrim, text: str):
        """Extract specs mentioned inline in text"""
        
        # Engine CC
        cc_match = re.search(r'(\d{3,4})\s*(?:cc|cm3|cm³)', text, re.I)
        if cc_match:
            trim.engine_cc = int(cc_match.group(1))
        
        # CV fiscal
        cv_match = re.search(r'(\d{1,2})\s*(?:cv|ch)\s*(?:fiscaux|fiscal)?', text, re.I)
        if cv_match:
            trim.cv_fiscal = int(cv_match.group(1))
        
        # Horsepower
        hp_match = re.search(r'(\d{2,3})\s*(?:ch|hp|cv\s*din)', text, re.I)
        if hp_match:
            trim.cv_din = int(hp_match.group(1))
        
        # Transmission
        text_lower = text.lower()
        if any(x in text_lower for x in ['automatique', 'bva', 'dsg', 'dct', 'auto', 'at']):
            trim.transmission = 'automatic'
        elif any(x in text_lower for x in ['manuelle', 'bvm', 'mt']):
            trim.transmission = 'manual'
        
        # Drivetrain
        if any(x in text_lower for x in ['4x4', 'awd', '4motion', 'quattro', 'xdrive', 'q4', '4wd']):
            trim.drivetrain = 'AWD'
    
    def _extract_specs_from_page(self, soup: BeautifulSoup, page_text: str) -> dict:
        """Extract technical specs from the page"""
        
        specs = {}
        
        # Look for spec tables (fiche technique)
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    self._parse_spec_row(specs, label, value)
        
        # Also look for dl/dt/dd structures
        for dl in soup.find_all('dl'):
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                label = dt.get_text(strip=True).lower()
                value = dd.get_text(strip=True)
                self._parse_spec_row(specs, label, value)
        
        return specs
    
    def _parse_spec_row(self, specs: dict, label: str, value: str):
        """Parse a single spec row"""
        
        if 'cylindrée' in label or 'moteur' in label:
            match = re.search(r'(\d{3,4})', value)
            if match:
                specs['engine_cc'] = int(match.group(1))
        
        elif 'puissance fiscale' in label or 'cv fiscaux' in label:
            match = re.search(r'(\d{1,2})', value)
            if match:
                specs['cv_fiscal'] = int(match.group(1))
        
        elif 'puissance' in label and 'fiscale' not in label:
            match = re.search(r'(\d{2,3})', value)
            if match:
                specs['cv_din'] = int(match.group(1))
        
        elif 'couple' in label:
            match = re.search(r'(\d{2,3})', value)
            if match:
                specs['torque_nm'] = int(match.group(1))
        
        elif 'consommation' in label and 'mixte' in label:
            match = re.search(r'(\d+[.,]?\d*)', value)
            if match:
                specs['consumption_mixed'] = float(match.group(1).replace(',', '.'))
        
        elif 'co2' in label or 'émission' in label:
            match = re.search(r'(\d{2,3})', value)
            if match:
                specs['co2_emissions'] = int(match.group(1))
        
        elif 'boîte' in label or 'transmission' in label:
            if 'auto' in value.lower():
                specs['transmission'] = 'automatic'
            elif 'manuel' in value.lower():
                specs['transmission'] = 'manual'
            speed_match = re.search(r'(\d)', value)
            if speed_match:
                specs['gearbox_speeds'] = int(speed_match.group(1))
        
        elif 'longueur' in label:
            match = re.search(r'(\d{4,5})', value)
            if match:
                specs['length_mm'] = int(match.group(1))
        
        elif 'largeur' in label:
            match = re.search(r'(\d{4,5})', value)
            if match:
                specs['width_mm'] = int(match.group(1))
        
        elif 'hauteur' in label:
            match = re.search(r'(\d{4,5})', value)
            if match:
                specs['height_mm'] = int(match.group(1))
        
        elif 'empattement' in label:
            match = re.search(r'(\d{4,5})', value)
            if match:
                specs['wheelbase_mm'] = int(match.group(1))
        
        elif 'coffre' in label:
            match = re.search(r'(\d{2,4})', value)
            if match:
                specs['trunk_liters'] = int(match.group(1))
        
        elif 'réservoir' in label:
            match = re.search(r'(\d{2,3})', value)
            if match:
                specs['fuel_tank_liters'] = int(match.group(1))
        
        elif 'poids' in label or 'masse' in label:
            match = re.search(r'(\d{3,4})', value)
            if match:
                specs['weight_kg'] = int(match.group(1))
        
        elif 'vitesse' in label and 'max' in label:
            match = re.search(r'(\d{3})', value)
            if match:
                specs['top_speed_kmh'] = int(match.group(1))
        
        elif '0-100' in label or '0 à 100' in label:
            match = re.search(r'(\d+[.,]?\d*)', value)
            if match:
                specs['acceleration_0_100'] = float(match.group(1).replace(',', '.'))
        
        elif 'batterie' in label:
            match = re.search(r'(\d+[.,]?\d*)', value)
            if match:
                specs['battery_kwh'] = float(match.group(1).replace(',', '.'))
        
        elif 'autonomie' in label:
            match = re.search(r'(\d{2,3})', value)
            if match:
                specs['range_km'] = int(match.group(1))
        
        elif 'garantie' in label:
            match = re.search(r'(\d)', value)
            if match:
                specs['warranty_years'] = int(match.group(1))
        
        elif 'places' in label:
            match = re.search(r'(\d)', value)
            if match:
                specs['seats'] = int(match.group(1))
        
        elif 'portes' in label:
            match = re.search(r'(\d)', value)
            if match:
                specs['doors'] = int(match.group(1))
    
    def _apply_specs(self, trim: CarTrim, specs: dict):
        """Apply common specs to trim"""
        for key, value in specs.items():
            if hasattr(trim, key) and getattr(trim, key) is None:
                setattr(trim, key, value)
    
    def _determine_fuel_and_body(self, trim: CarTrim):
        """Determine fuel type and body type from name"""
        
        name_lower = f"{trim.brand} {trim.model} {trim.trim}".lower()
        
        # Fuel type
        if any(x in name_lower for x in ['électrique', 'electric', 'ev', 'e-tron', 'id.', 'bev']):
            trim.fuel_type = 'electric'
            trim.is_electric = True
        elif any(x in name_lower for x in ['plug-in', 'phev', 'rechargeable', 'e-hybrid']):
            trim.fuel_type = 'hybrid_rechargeable'
            trim.is_hybrid = True
        elif any(x in name_lower for x in ['hybrid', 'hybride', 'mhev']):
            trim.fuel_type = 'hybrid'
            trim.is_hybrid = True
        elif any(x in name_lower for x in ['diesel', 'tdi', 'hdi', 'dci', 'cdti', 'bluehdi']):
            trim.fuel_type = 'diesel'
        else:
            trim.fuel_type = 'essence'
        
        # Body type
        if any(x in name_lower for x in ['suv', 'crossover', 'x1', 'x3', 'x5', 'glc', 'gle', 'q3', 'q5', 'tiguan', 'tucson', '3008', '5008']):
            trim.body_type = 'SUV'
        elif any(x in name_lower for x in ['berline', 'sedan', 'série 3', 'classe c', 'a4', 'passat']):
            trim.body_type = 'Berline'
        elif any(x in name_lower for x in ['citadine', 'i10', 'picanto', 'clio', '208', 'polo']):
            trim.body_type = 'Citadine'
        elif any(x in name_lower for x in ['break', 'touring', 'avant', 'sw']):
            trim.body_type = 'Break'
        elif any(x in name_lower for x in ['coupé', 'coupe']):
            trim.body_type = 'Coupé'
        elif any(x in name_lower for x in ['pick', 'amarok', 'hilux']):
            trim.body_type = 'Pick-up'
        else:
            trim.body_type = 'Compacte'
    
    def _generate_id(self, trim: CarTrim):
        """Generate unique ID"""
        clean = lambda s: re.sub(r'[^a-z0-9]', '_', s.lower())
        trim.id = f"{clean(trim.brand)}_{clean(trim.model)}_{clean(trim.trim)}"
    
    async def scrape_all(self, max_brands: int = None):
        """Main scraping function"""
        
        print("=" * 70)
        print("🚗 AUTOMOBILE.TN NEW CARS SCRAPER")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            
            # Step 1: Get all brands
            brands = await self.get_all_brands(crawler)
            if not brands:
                return
            
            if max_brands:
                brands = brands[:max_brands]
                print(f"⚠️ Limited to {max_brands} brands")
            
            # Step 2 & 3: Scrape each brand
            print(f"\n📋 Scraping {len(brands)} brands...\n")
            
            for i, brand in enumerate(brands, 1):
                print(f"[{i}/{len(brands)}] 🏭 {brand['name']}")
                
                models = await self.get_brand_models(crawler, brand)
                self.stats["models"] += len(models)
                
                if not models:
                    print(f"    ⚠️ No models found")
                    continue
                
                print(f"    📦 Found {len(models)} models")
                
                for model in models:
                    trims = await self.get_model_trims(crawler, model)
                    self.cars.extend(trims)
                    
                    if trims:
                        prices = [t.price_tnd for t in trims if t.price_tnd]
                        price_info = f"({min(prices):,} - {max(prices):,} TND)" if prices else ""
                        disc_info = " 🏷️" if any(t.has_discount for t in trims) else ""
                        print(f"       ✅ {model['name']}: {len(trims)} trims {price_info}{disc_info}")
                    
                    await asyncio.sleep(0.3)
                
                await asyncio.sleep(0.5)
        
        print(f"\n✅ Scraping complete! Total: {len(self.cars)} trims")
    
    def _filter_valid_cars(self) -> List[CarTrim]:
        """Filter out non-car entries and deduplicate by model_url"""
        valid_trims = []

        for car in self.cars:
            # Skip entries with model "Devis"
            if car.model.lower() == 'devis':
                continue
            # Skip entries with brand "Concessionnaires"
            if car.brand.lower() == 'concessionnaires':
                continue
            # Skip entries where model URL contains "devis"
            if 'devis' in car.model_url.lower():
                continue
            # Skip entries with noisy trim names (other brand names)
            if not self._is_valid_trim_name(car.trim, car.brand):
                continue
            valid_trims.append(car)

        # Deduplicate by model_url only (one entry per model page)
        filtered = []
        seen_urls = set()

        for car in valid_trims:
            # One entry per model page URL
            if car.model_url in seen_urls:
                continue
            seen_urls.add(car.model_url)
            filtered.append(car)

        return filtered

    def save_to_csv(self, filename: str = "automobile_tn_new_cars.csv"):
        """Save to CSV"""
        if not self.cars:
            print("⚠️ No cars to save")
            return

        # Filter out non-car entries
        valid_cars = self._filter_valid_cars()

        fieldnames = list(CarTrim.__dataclass_fields__.keys())

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for car in valid_cars:
                writer.writerow(asdict(car))

        print(f"📁 Saved {len(valid_cars)} cars to {filename}")
    
    def save_to_json(self, filename: str = "automobile_tn_new_cars.json"):
        """Save to JSON"""
        # Filter out non-car entries
        valid_cars = self._filter_valid_cars()

        data = {
            "scraped_at": datetime.now().isoformat(),
            "stats": self.stats,
            "total": len(valid_cars),
            "cars": [asdict(c) for c in valid_cars]
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"📁 Saved to {filename}")
    
    def print_summary(self):
        """Print summary"""
        print("\n" + "=" * 70)
        print("📊 SUMMARY")
        print("=" * 70)

        # Use filtered cars for summary
        valid_cars = self._filter_valid_cars()

        print(f"\n📈 Stats:")
        print(f"   Brands: {self.stats['brands']}")
        print(f"   Models: {self.stats['models']}")
        print(f"   Trims: {len(valid_cars)}")
        print(f"   With prices: {sum(1 for c in valid_cars if c.price_tnd)}")
        print(f"   With discounts: {sum(1 for c in valid_cars if c.has_discount)}")

        prices = [c.price_tnd for c in valid_cars if c.price_tnd]
        if prices:
            print(f"\n💰 Prices: {min(prices):,} - {max(prices):,} TND (avg: {sum(prices)//len(prices):,})")
        
        # Top brands
        brand_counts = {}
        for c in valid_cars:
            brand_counts[c.brand] = brand_counts.get(c.brand, 0) + 1

        print(f"\n🏭 Top brands:")
        for brand, count in sorted(brand_counts.items(), key=lambda x: -x[1])[:10]:
            brand_prices = [c.price_tnd for c in valid_cars if c.brand == brand and c.price_tnd]
            if brand_prices:
                print(f"   {brand}: {count} trims ({min(brand_prices):,} - {max(brand_prices):,} TND)")

        # Discounted cars
        discounted = [c for c in valid_cars if c.has_discount]
        if discounted:
            print(f"\n🏷️ Discounts ({len(discounted)}):")
            for c in discounted[:5]:
                print(f"   {c.full_name}: {c.price_tnd:,} TND (save {c.discount_tnd:,})")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    scraper = AutomobileTnScraper()
    
    # Set max_brands=5 for testing, None for full scrape
    await scraper.scrape_all(max_brands=None)
    
    scraper.save_to_csv()
    scraper.save_to_json()
    scraper.print_summary()
    
    print("\n✨ Done!")


if __name__ == "__main__":
    asyncio.run(main())