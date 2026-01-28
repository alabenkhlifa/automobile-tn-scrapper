"""
AutoScout24 Multi-Country Car Listings Scraper
===============================================
Async scraper for AutoScout24 car listings across DE, FR, IT, BE.

Features:
- Multi-country support (de, fr, it, be) with localized label parsing
- JSON-LD extraction with HTML spec table and regex fallback
- Rate limiting with semaphore, jitter, and exponential backoff
- User-Agent rotation and Accept-Language matching per country
- Optional Playwright fallback for JS-rendered pages
- Per-country and combined JSON/CSV output

Run:
    python autoscout24_scraper.py
    python autoscout24_scraper.py --countries de,fr --condition used --max-listings 200
    python autoscout24_scraper.py --makes bmw,audi --min-price 5000 --max-price 30000
    python autoscout24_scraper.py --use-playwright

Requirements:
    pip install httpx beautifulsoup4 lxml
    pip install playwright  # optional, for --use-playwright
"""

import asyncio
import json
import csv
import re
import random
import argparse
import logging
import time
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict
from bs4 import BeautifulSoup

import httpx


class RateLimitStop(Exception):
    """Raised when a 429 is hit to signal scraping should stop."""
    pass


# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("autoscout24")


# =============================================================================
# DATA MODEL
# =============================================================================

@dataclass
class AutoScout24Car:
    """A single AutoScout24 car listing with full specs."""

    # Identification & URLs
    id: str = ""
    listing_url: str = ""
    country: str = ""

    # Basic info
    make: str = ""
    model: str = ""
    variant: str = ""
    full_name: str = ""

    # Pricing
    price_eur: Optional[int] = None
    price_original_eur: Optional[int] = None
    vat_deductible: bool = False

    # History
    year: Optional[int] = None
    first_registration: str = ""
    mileage_km: Optional[int] = None
    previous_owners: Optional[int] = None
    condition: str = ""  # "new" or "used"

    # Engine
    fuel_type: str = ""
    power_kw: Optional[int] = None
    power_hp: Optional[int] = None
    engine_cc: Optional[int] = None
    emission_class: str = ""
    co2_emissions: Optional[int] = None
    consumption_combined: Optional[float] = None

    # Transmission
    transmission: str = ""
    gears: Optional[int] = None
    drivetrain: str = ""

    # Body
    body_type: str = ""
    doors: Optional[int] = None
    seats: Optional[int] = None
    color_exterior: str = ""
    color_interior: str = ""

    # Features
    features: List[str] = field(default_factory=list)
    safety_features: List[str] = field(default_factory=list)
    comfort_features: List[str] = field(default_factory=list)

    # Seller
    seller_type: str = ""  # "dealer" or "private"
    seller_name: str = ""
    seller_location: str = ""
    seller_country: str = ""

    # Meta
    image_count: int = 0
    scraped_at: str = ""

    # Computed (filled by _clean_data)
    price_per_km: Optional[float] = None
    age_years: Optional[int] = None

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()


# =============================================================================
# CONSTANTS
# =============================================================================

COUNTRIES_MAP: Dict[str, str] = {
    "de": "autoscout24.de",
    "fr": "autoscout24.fr",
    "it": "autoscout24.it",
    "be": "autoscout24.be",
}

# Belgium requires a language prefix in URLs (e.g. /fr/lst instead of /lst)
COUNTRY_PATH_PREFIX: Dict[str, str] = {
    "de": "",
    "fr": "",
    "it": "",
    "be": "/fr",
}

# Localized path for detail/offer pages per country
COUNTRY_DETAIL_PATH: Dict[str, str] = {
    "de": "angebote",
    "fr": "offres",
    "it": "annunci",
    "be": "offres",  # Belgian site uses French
}

ACCEPT_LANGUAGE_MAP: Dict[str, str] = {
    "de": "de-DE,de;q=0.9,en;q=0.5",
    "fr": "fr-FR,fr;q=0.9,en;q=0.5",
    "it": "it-IT,it;q=0.9,en;q=0.5",
    "be": "fr-BE,fr;q=0.9,nl-BE;q=0.8,en;q=0.5",
}

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# Localized spec labels → field name mapping (DE, FR, IT)
SPEC_LABEL_MAP: Dict[str, str] = {
    # Mileage
    "kilometerstand": "mileage_km",
    "kilométrage": "mileage_km",
    "chilometraggio": "mileage_km",
    # First registration
    "erstzulassung": "first_registration",
    "première immatriculation": "first_registration",
    "prima immatricolazione": "first_registration",
    # Fuel
    "kraftstoffart": "fuel_type",
    "kraftstoff": "fuel_type",
    "carburant": "fuel_type",
    "combustibile": "fuel_type",
    # Power
    "leistung": "power",
    "puissance": "power",
    "potenza": "power",
    # Transmission
    "getriebe": "transmission",
    "boîte de vitesse": "transmission",
    "cambio": "transmission",
    # Body type
    "karosserie": "body_type",
    "karosserieform": "body_type",
    "carrosserie": "body_type",
    "carrozzeria": "body_type",
    # Doors
    "türen": "doors",
    "portes": "doors",
    "porte": "doors",
    # Seats
    "sitze": "seats",
    "sièges": "seats",
    "sitzplätze": "seats",
    "posti": "seats",
    # Exterior color
    "farbe": "color_exterior",
    "couleur": "color_exterior",
    "colore": "color_exterior",
    # Previous owners
    "vorbesitzer": "previous_owners",
    "propriétaires précédents": "previous_owners",
    "propriétaires": "previous_owners",
    "proprietari precedenti": "previous_owners",
    "proprietari": "previous_owners",
    # Displacement
    "hubraum": "engine_cc",
    "cylindrée": "engine_cc",
    "cilindrata": "engine_cc",
    # CO2
    "co₂-emissionen": "co2_emissions",
    "co2-emissionen": "co2_emissions",
    "émissions co₂": "co2_emissions",
    "émissions co2": "co2_emissions",
    "emissioni co₂": "co2_emissions",
    "emissioni co2": "co2_emissions",
    # Consumption
    "verbrauch (komb.)": "consumption_combined",
    "verbrauch": "consumption_combined",
    "consommation (comb.)": "consumption_combined",
    "consommation": "consumption_combined",
    "consumo (comb.)": "consumption_combined",
    "consumo": "consumption_combined",
    # Emission class
    "schadstoffklasse": "emission_class",
    "norme antipollution": "emission_class",
    "classe d'émission": "emission_class",
    "classe di emissione": "emission_class",
    # Drivetrain
    "antrieb": "drivetrain",
    "transmission": "drivetrain",
    "trazione": "drivetrain",
    # Interior color
    "innenfarbe": "color_interior",
    "couleur intérieure": "color_interior",
    "colore interni": "color_interior",
    # Condition
    "zustand": "condition",
    "état": "condition",
    "stato": "condition",
}

# Fuel type normalization across languages
FUEL_TYPE_NORMALIZE: Dict[str, str] = {
    "benzin": "petrol",
    "super": "petrol",
    "essence": "petrol",
    "benzina": "petrol",
    "diesel": "diesel",
    "elektro": "electric",
    "électrique": "electric",
    "elettrica": "electric",
    "electric": "electric",
    "hybrid": "hybrid",
    "hybride": "hybrid",
    "ibrida": "hybrid",
    "plug-in-hybrid": "plug-in hybrid",
    "hybride rechargeable": "plug-in hybrid",
    "ibrida plug-in": "plug-in hybrid",
    "erdgas (cng)": "cng",
    "gaz naturel (cng)": "cng",
    "autogas (lpg)": "lpg",
    "gpl": "lpg",
    "wasserstoff": "hydrogen",
    "hydrogène": "hydrogen",
    "idrogeno": "hydrogen",
}

ALLOWED_FUEL_TYPES = {"petrol", "diesel", "electric", "hybrid", "plug-in hybrid", "hybrid_rechargeable"}

MAKE_NORMALIZE = {
    "mercedes-benz": "Mercedes-Benz",
    "mercedes": "Mercedes-Benz",
    "bmw": "BMW",
    "vw": "Volkswagen",
    "volkswagen": "Volkswagen",
    "alfa-romeo": "Alfa Romeo",
    "alfa romeo": "Alfa Romeo",
    "land-rover": "Land Rover",
    "land rover": "Land Rover",
    "rolls-royce": "Rolls-Royce",
    "rolls royce": "Rolls-Royce",
    "aston-martin": "Aston Martin",
    "aston martin": "Aston Martin",
}

# Transmission normalization
TRANSMISSION_NORMALIZE: Dict[str, str] = {
    "automatik": "automatic",
    "automatique": "automatic",
    "automatico": "automatic",
    "automatic": "automatic",
    "schaltgetriebe": "manual",
    "manuelle": "manual",
    "manuale": "manual",
    "manual": "manual",
    "halbautomatik": "semi-automatic",
    "semi-automatique": "semi-automatic",
    "semi-automatico": "semi-automatic",
}


# =============================================================================
# PRICE PARSING
# =============================================================================

def parse_eur_price(text: str) -> Optional[int]:
    """Parse European price formats and return integer EUR value.

    Handles:
      - € 25.900, €25.900  (DE/IT - dots as thousands separators)
      - 25 900 €, 25.900 € (FR - spaces or dots as thousands separators)
      - €25,900 is NOT treated as thousands (EU decimal comma)
    Returns None if no price found.
    """
    if not text:
        return None

    # Remove currency symbol and surrounding whitespace
    cleaned = text.replace("€", "").replace("EUR", "").strip()
    cleaned = cleaned.replace("\u00a0", " ").replace("\u202f", " ")

    # Pattern: digits separated by dots (thousands) e.g. 25.900
    m = re.search(r"(\d{1,3}(?:\.\d{3})+)", cleaned)
    if m:
        return int(m.group(1).replace(".", ""))

    # Pattern: digits separated by spaces (thousands) e.g. 25 900
    m = re.search(r"(\d{1,3}(?:\s\d{3})+)", cleaned)
    if m:
        return int(m.group(1).replace(" ", ""))

    # Plain number e.g. 25900
    m = re.search(r"(\d{4,7})", cleaned)
    if m:
        return int(m.group(1))

    return None


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class AutoScout24Scraper:
    """Async multi-country scraper for AutoScout24 car listings."""

    MAX_CONCURRENT = 5
    BASE_DELAY = 0.5
    MAX_JITTER = 0.3
    MAX_RETRIES = 3
    LISTINGS_PER_PAGE = 20  # AutoScout24 default page size

    def __init__(
        self,
        countries: List[str] = None,
        condition: str = "all",
        max_listings: int = 100,
        makes: List[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        use_playwright: bool = False,
        per_model: bool = False,
        per_model_limit: int = 10,
    ):
        self.countries = countries or ["de"]
        self.condition = condition
        self.max_listings = max_listings
        self.makes = makes
        self.min_price = min_price
        self.max_price = max_price
        self.use_playwright = use_playwright
        self.per_model = per_model
        self.per_model_limit = per_model_limit

        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)
        self._semaphore_value = self.MAX_CONCURRENT
        self.cars: List[AutoScout24Car] = []
        self.cars_by_country: Dict[str, List[AutoScout24Car]] = {}
        self.playwright_browser = None

        # Request metrics
        self.request_stats: Dict[str, int] = {
            "total": 0, "success": 0, "rate_limited": 0, "blocked": 0, "errors": 0,
        }
        self.request_stats_by_country: Dict[str, Dict[str, int]] = {}
        self.request_timestamps: List[float] = []
        self.rate_limit_timestamps: List[float] = []

        self._country_delay: Dict[str, float] = {}  # current delay per country
        self._stop_country: Dict[str, bool] = {}  # stop flag per country

    # -------------------------------------------------------------------------
    # HTTP / Fetch helpers
    # -------------------------------------------------------------------------

    def _random_headers(self, country: str) -> Dict[str, str]:
        """Build request headers with rotated User-Agent and localized Accept-Language."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": ACCEPT_LANGUAGE_MAP.get(country, "en;q=0.9"),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _record_request(self, country: str, category: str):
        """Record a request in the stats tracker."""
        self.request_stats["total"] += 1
        self.request_stats[category] += 1
        self.request_timestamps.append(time.monotonic())
        if country not in self.request_stats_by_country:
            self.request_stats_by_country[country] = {
                "total": 0, "success": 0, "rate_limited": 0, "blocked": 0, "errors": 0,
            }
        self.request_stats_by_country[country]["total"] += 1
        self.request_stats_by_country[country][category] += 1

    def _get_country_delay(self, country: str) -> float:
        """Get the current adaptive delay for a country."""
        return self._country_delay.get(country, self.BASE_DELAY)

    def _on_success(self, country: str):
        """Update adaptive state on success."""
        # Gradually restore delay (halve it, floor at BASE_DELAY)
        current = self._country_delay.get(country, self.BASE_DELAY)
        if current > self.BASE_DELAY:
            self._country_delay[country] = max(current * 0.75, self.BASE_DELAY)

    async def _fetch(self, client: httpx.AsyncClient, url: str, country: str = "de") -> Optional[str]:
        """Fetch a URL with rate limiting, jitter, UA rotation, and retry on errors.

        Raises RateLimitStop on 429 to signal the caller to stop scraping.
        """
        # Check if scraping was already stopped for this country
        if self._stop_country.get(country, False):
            raise RateLimitStop(country)

        async with self.semaphore:
            # Check again after acquiring semaphore (another task may have set the flag)
            if self._stop_country.get(country, False):
                raise RateLimitStop(country)

            for attempt in range(1, self.MAX_RETRIES + 1):
                try:
                    delay = self._get_country_delay(country) + random.uniform(0, self.MAX_JITTER)
                    await asyncio.sleep(delay)

                    headers = self._random_headers(country)
                    response = await client.get(url, headers=headers, follow_redirects=True)

                    if response.status_code == 429:
                        self._record_request(country, "rate_limited")
                        self.rate_limit_timestamps.append(time.monotonic())
                        # Set stop flag to prevent other concurrent tasks from making requests
                        self._stop_country[country] = True
                        log.warning("[%s] Got 429 on %s – stopping scrape for this country", country.upper(), url)
                        raise RateLimitStop(country)

                    if response.status_code == 403:
                        self._record_request(country, "blocked")
                        wait = 3 ** (attempt - 1) + random.uniform(0, 1)
                        log.warning("Got %d on %s – retrying in %.1fs (attempt %d/%d)",
                                    response.status_code, url, wait, attempt, self.MAX_RETRIES)
                        if attempt >= self.MAX_RETRIES:
                            return None
                        await asyncio.sleep(wait)
                        continue

                    if response.status_code == 404:
                        self._record_request(country, "errors")
                        log.debug("404 on %s", url)
                        return None

                    response.raise_for_status()
                    self._record_request(country, "success")
                    self._on_success(country)
                    return response.text

                except RateLimitStop:
                    raise
                except httpx.HTTPStatusError as exc:
                    self._record_request(country, "errors")
                    log.error("HTTP %d fetching %s: %s", exc.response.status_code, url, exc)
                    return None
                except httpx.HTTPError as exc:
                    self._record_request(country, "errors")
                    log.error("Request error fetching %s: %s", url, exc)
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(2 ** (attempt - 1))
                        continue
                    return None

        return None

    async def _fetch_playwright(self, url: str, country: str = "de") -> Optional[str]:
        """Fetch a page using Playwright for JS-rendered content."""
        if self.playwright_browser is None:
            return None

        try:
            context = await self.playwright_browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                locale=ACCEPT_LANGUAGE_MAP.get(country, "en-US").split(",")[0],
                viewport={"width": 1920, "height": 1080},
                java_script_enabled=True,
            )
            page = await context.new_page()

            # Disable webdriver detection
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1.5 + random.uniform(0, 0.5))
            content = await page.content()
            await context.close()
            return content
        except Exception as exc:
            log.error("Playwright error on %s: %s", url, exc)
            return None

    async def fetch(self, client: httpx.AsyncClient, url: str, country: str = "de") -> Optional[str]:
        """Unified fetch: use Playwright if enabled, otherwise httpx."""
        if self.use_playwright and self.playwright_browser is not None:
            return await self._fetch_playwright(url, country)
        return await self._fetch(client, url, country)

    # -------------------------------------------------------------------------
    # URL building
    # -------------------------------------------------------------------------

    def _build_search_url(self, country: str, make: Optional[str], page: int) -> str:
        """Build a search results URL for AutoScout24."""
        domain = COUNTRIES_MAP[country]
        prefix = COUNTRY_PATH_PREFIX.get(country, "")
        base = f"https://www.{domain}{prefix}/lst"
        if make:
            base += f"/{make}"

        params = ["atype=C", f"sort=standard", "desc=0", f"page={page}"]

        # Condition filter
        if self.condition == "new":
            params.append("ustate=N")
        elif self.condition == "used":
            params.append("ustate=U")
        # "all" → do not include ustate

        # Price filters
        if self.min_price is not None:
            params.append(f"pricefrom={self.min_price}")
        if self.max_price is not None:
            params.append(f"priceto={self.max_price}")

        return f"{base}?{'&'.join(params)}"

    # -------------------------------------------------------------------------
    # Listing page parsing
    # -------------------------------------------------------------------------

    @staticmethod
    def _clean_full_name(raw_name: str, make: str, model: str) -> str:
        """Clean up a listing heading into a proper car name.

        Removes dealer junk like feature lists, price tags, and abbreviation chains.
        """
        name = raw_name.strip()
        # Fix AutoScout24 heading bug where series+model digits get concatenated
        # e.g. "BMW 435435d" → "BMW 435d", "BMW 216216 i" → "BMW 216 i", "BMW 3203" → "BMW 320"
        if make:
            prefix = make.upper() + " "
            if name.upper().startswith(prefix):
                after = name[len(prefix):]
                dup_match = re.match(r"(\d{3})(\1\w*)", after)
                if dup_match:
                    name = prefix + after[len(dup_match.group(1)):]
        # Remove embedded price tags like "UPE: 56.189€" or "ab 25.900€"
        name = re.sub(r"(?:UPE|UVP|ab|statt)\s*:?\s*[\d.,]+\s*€", "", name, flags=re.I)
        # Remove trailing feature/option lists after multiple slashes or commas
        # e.g. "BMW 118i /Advantage/Xenon/MuFu" → "BMW 118i"
        # e.g. "BMW 435d xDrive Coupe Sport Line Adap.LED,HUD,Leder" → "BMW 435d xDrive Coupe Sport Line"
        name = re.sub(r"\s*/\w.*$", "", name)  # strip from first " /" onward
        name = re.sub(r"(?:,\s*\w+){2,}$", "", name)  # strip trailing comma chains (3+ items)
        name = re.sub(r"\s*\*\w+(\*\w+)+\*?\s*$", "", name)  # strip *Feature*Feature* chains
        # Remove stray punctuation at end
        name = re.sub(r"[,/|*]+\s*$", "", name).strip()
        # Cap length — truncate at ~60 chars on a word boundary
        if len(name) > 60:
            name = name[:60].rsplit(" ", 1)[0]

        # If the heading is empty or too short after cleanup, build from make+model
        if len(name) < 3 and (make or model):
            name = f"{make.upper()} {model}".strip()

        return name

    def _parse_listing_cards(self, html: str, country: str) -> List[Dict]:
        """Extract listing card data from a search results page.

        Primarily uses data-* attributes on <article> elements (most reliable),
        with text/HTML fallbacks for missing fields.
        """
        soup = BeautifulSoup(html, "lxml")
        cards: List[Dict] = []
        domain = COUNTRIES_MAP[country]

        # Fuel type codes used in data-fuel-type attribute
        fuel_code_map = {
            "b": "petrol", "d": "diesel", "e": "electric",
            "2": "hybrid", "l": "lpg", "c": "cng", "h": "hydrogen",
            "m": "hybrid_rechargeable",
        }

        articles = soup.find_all("article")
        if not articles:
            articles = soup.find_all("div", attrs={"data-testid": re.compile(r"listing")})
        if not articles:
            articles = soup.find_all("div", class_=re.compile(r"ListItem|list-item|listing", re.I))

        for article in articles:
            card: Dict = {"country": country}

            # --- ID and URL: prefer full link URL to avoid 308 redirects ---
            guid = article.get("data-guid", "")
            link = article.find("a", href=True)

            if link:
                # Use full URL from link (includes slug, avoids redirect)
                href = link["href"]
                if href.startswith("/"):
                    href = f"https://www.{domain}{href}"
                card["listing_url"] = href
                # Extract ID from URL or use data-guid
                id_match = re.search(r"([a-f0-9-]{36})", href)
                if id_match:
                    card["id"] = id_match.group(1)
                elif guid:
                    card["id"] = guid
            elif guid:
                # Fallback: construct URL from guid (may cause 308 redirect)
                card["id"] = guid
                detail_path = COUNTRY_DETAIL_PATH.get(country, "angebote")
                prefix = COUNTRY_PATH_PREFIX.get(country, "")
                card["listing_url"] = f"https://www.{domain}{prefix}/{detail_path}/{guid}"
            else:
                continue

            # --- Structured data attributes (most reliable) ---
            data_make = article.get("data-make", "").strip()
            data_model = article.get("data-model", "").strip()
            data_price = article.get("data-price", "")
            data_mileage = article.get("data-mileage", "")
            data_fuel = article.get("data-fuel-type", "").lower()
            data_reg = article.get("data-first-registration", "")  # e.g. "07-2008"
            data_seller = article.get("data-seller-type", "")

            if data_make:
                card["make"] = data_make.upper()
            if data_model:
                card["model"] = data_model

            if data_price:
                try:
                    card["price_eur"] = int(data_price)
                except ValueError:
                    pass

            if data_mileage:
                try:
                    card["mileage_km"] = int(data_mileage)
                except ValueError:
                    pass

            if data_fuel and data_fuel in fuel_code_map:
                card["fuel_type"] = fuel_code_map[data_fuel]

            if data_reg:
                year_match = re.search(r"(\d{4})", data_reg)
                if year_match:
                    card["year"] = int(year_match.group(1))
                card["first_registration"] = data_reg

            if data_seller:
                card["seller_type"] = "dealer" if data_seller == "d" else "private"

            # --- Full name from heading, cleaned up ---
            title_el = article.find(["h2", "h3"])
            if title_el:
                raw = title_el.get_text(strip=True)
                card["full_name"] = self._clean_full_name(raw, data_make, data_model)

            # --- Fallback: extract from card text for fields not in data attrs ---
            card_text = article.get_text(separator=" ", strip=True)

            if "price_eur" not in card:
                price_el = article.find(attrs={"data-testid": re.compile(r"price", re.I)})
                if not price_el:
                    price_el = article.find(class_=re.compile(r"price", re.I))
                if price_el:
                    card["price_eur"] = parse_eur_price(price_el.get_text(strip=True))
                else:
                    card["price_eur"] = parse_eur_price(card_text)

            # Power
            power_match = re.search(r"(\d{2,4})\s*(?:PS|hp|ch|CV|kW)", card_text, re.I)
            if power_match:
                val = int(power_match.group(1))
                unit = re.search(r"(PS|hp|ch|CV|kW)", card_text, re.I)
                if unit and unit.group(1).lower() == "kw":
                    card["power_kw"] = val
                    card["power_hp"] = int(val * 1.36)
                else:
                    card["power_hp"] = val
                    card["power_kw"] = int(val / 1.36)

            # Transmission
            if "transmission" not in card:
                for trans_word, normalized in TRANSMISSION_NORMALIZE.items():
                    if trans_word in card_text.lower():
                        card["transmission"] = normalized
                        break

            # Image count from data-testid counter
            img_counter = article.find(attrs={"data-testid": "decluttered-list-item-image-counter"})
            if img_counter:
                try:
                    card["image_count"] = int(img_counter.get_text(strip=True))
                except ValueError:
                    card["image_count"] = len(article.find_all("img"))
            else:
                card["image_count"] = len(article.find_all("img"))

            # Seller info from data-testid elements
            dealer_el = article.find(attrs={"data-testid": "dealer-company-name"})
            if dealer_el:
                card["seller_name"] = dealer_el.get_text(strip=True)
            addr_el = article.find(attrs={"data-testid": "dealer-address"})
            if addr_el:
                card["seller_location"] = addr_el.get_text(strip=True)

            cards.append(card)

        return cards

    # -------------------------------------------------------------------------
    # Detail page parsing
    # -------------------------------------------------------------------------

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract JSON-LD data (@type Car or Product) from the page."""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") in ("Car", "Product", "Vehicle"):
                            return item
                elif isinstance(data, dict) and data.get("@type") in ("Car", "Product", "Vehicle"):
                    return data
            except (json.JSONDecodeError, AttributeError, TypeError):
                continue
        return None

    def _parse_json_ld(self, car: AutoScout24Car, data: dict):
        """Populate car fields from JSON-LD structured data."""
        ld_name = data.get("name", "")
        # Only use JSON-LD name if it looks like a real car name (not "BMW für € 1.399")
        if ld_name and "€" not in ld_name and "für" not in ld_name.lower():
            car.full_name = ld_name

        # Brand
        brand = data.get("brand")
        if isinstance(brand, dict):
            car.make = brand.get("name", car.make)
        elif isinstance(brand, str):
            car.make = brand

        # Model
        model = data.get("model", "")
        if model:
            if car.make and model.lower().startswith(car.make.lower()):
                car.model = model[len(car.make):].strip()
            else:
                car.model = model

        # Offers / price
        offers = data.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if isinstance(offers, dict):
            price_val = offers.get("price")
            if price_val is not None:
                try:
                    car.price_eur = int(float(price_val))
                except (ValueError, TypeError):
                    pass

        # Mileage
        mileage = data.get("mileageFromOdometer")
        if isinstance(mileage, dict):
            val = mileage.get("value")
            if val is not None:
                try:
                    car.mileage_km = int(float(val))
                except (ValueError, TypeError):
                    pass
        elif mileage is not None:
            try:
                car.mileage_km = int(float(str(mileage).replace(",", "").replace(".", "")))
            except (ValueError, TypeError):
                pass

        # Vehicle configuration / variant
        config = data.get("vehicleConfiguration", "")
        if config and not car.variant:
            car.variant = config

        # Body type
        car.body_type = data.get("bodyType", car.body_type)

        # Fuel
        fuel = data.get("fuelType", "")
        if fuel:
            car.fuel_type = FUEL_TYPE_NORMALIZE.get(fuel.lower(), fuel.lower())

        # Transmission
        trans = data.get("vehicleTransmission", "")
        if trans:
            car.transmission = TRANSMISSION_NORMALIZE.get(trans.lower(), trans.lower())

        # Doors, seats
        if data.get("numberOfDoors"):
            try:
                car.doors = int(data["numberOfDoors"])
            except (ValueError, TypeError):
                pass
        if data.get("seatingCapacity"):
            try:
                car.seats = int(data["seatingCapacity"])
            except (ValueError, TypeError):
                pass

        # Color
        car.color_exterior = data.get("color", car.color_exterior)

        # Engine
        engine = data.get("vehicleEngine") or {}
        if isinstance(engine, list):
            engine = engine[0] if engine else {}
        if isinstance(engine, dict):
            disp = engine.get("engineDisplacement")
            if disp:
                cc_match = re.search(r"([\d,.]+)", str(disp))
                if cc_match:
                    try:
                        car.engine_cc = int(float(cc_match.group(1).replace(",", "")))
                    except ValueError:
                        pass
            power = engine.get("enginePower")
            if power:
                kw_match = re.search(r"(\d+)\s*kW", str(power), re.I)
                if kw_match:
                    car.power_kw = int(kw_match.group(1))
                    if not car.power_hp:
                        car.power_hp = int(car.power_kw * 1.36)

        # Images
        images = data.get("image")
        if isinstance(images, list):
            car.image_count = max(car.image_count, len(images))
        elif isinstance(images, str):
            car.image_count = max(car.image_count, 1)

    def _parse_html_specs(self, car: AutoScout24Car, soup: BeautifulSoup):
        """Parse spec sections from detail page HTML (dt/dd pairs or key-value divs)."""

        pairs: List[tuple] = []

        # dt/dd pairs
        for dl in soup.find_all("dl"):
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")
            for dt, dd in zip(dts, dds):
                pairs.append((dt.get_text(strip=True), dd.get_text(strip=True)))

        # Table rows
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    pairs.append((cells[0].get_text(strip=True), cells[1].get_text(strip=True)))

        # Key-value div pairs (common in AutoScout24 detail pages)
        for container in soup.find_all("div", attrs={"data-testid": re.compile(r"spec|detail|key-value", re.I)}):
            children = container.find_all("div", recursive=False)
            if len(children) == 2:
                pairs.append((children[0].get_text(strip=True), children[1].get_text(strip=True)))

        # Also look for generic paired spans/divs in sections
        for section in soup.find_all(["section", "div"], class_=re.compile(r"VehicleOverview|detail|spec", re.I)):
            inner_divs = section.find_all("div", recursive=False)
            for div in inner_divs:
                sub = div.find_all(["span", "div", "p"], recursive=False)
                if len(sub) == 2:
                    pairs.append((sub[0].get_text(strip=True), sub[1].get_text(strip=True)))

        # Apply pairs to car fields
        for label_raw, value in pairs:
            label = label_raw.lower().strip().rstrip(":")
            field_name = SPEC_LABEL_MAP.get(label)
            if not field_name:
                # Partial match
                for key, fname in SPEC_LABEL_MAP.items():
                    if key in label:
                        field_name = fname
                        break

            if not field_name:
                continue

            self._apply_spec_value(car, field_name, value)

        # Features / equipment lists
        self._parse_features(car, soup)

    def _apply_spec_value(self, car: AutoScout24Car, field_name: str, value: str):
        """Apply a single spec pair to the car dataclass."""

        if field_name == "mileage_km" and not car.mileage_km:
            km_str = re.sub(r"[^\d]", "", value)
            if km_str:
                car.mileage_km = int(km_str)

        elif field_name == "first_registration" and not car.first_registration:
            car.first_registration = value.strip()
            # Try to extract year
            ym = re.search(r"(\d{1,2})/(\d{4})", value)
            if ym and not car.year:
                car.year = int(ym.group(2))

        elif field_name == "fuel_type" and not car.fuel_type:
            car.fuel_type = FUEL_TYPE_NORMALIZE.get(value.lower().strip(), value.lower().strip())

        elif field_name == "power":
            # Value like "110 kW (150 PS)" or "150 ch (110 kW)"
            kw_m = re.search(r"(\d+)\s*kW", value, re.I)
            hp_m = re.search(r"(\d+)\s*(?:PS|hp|ch|CV)", value, re.I)
            if kw_m and not car.power_kw:
                car.power_kw = int(kw_m.group(1))
            if hp_m and not car.power_hp:
                car.power_hp = int(hp_m.group(1))
            # Fill in missing
            if car.power_kw and not car.power_hp:
                car.power_hp = int(car.power_kw * 1.36)
            if car.power_hp and not car.power_kw:
                car.power_kw = int(car.power_hp / 1.36)

        elif field_name == "transmission" and not car.transmission:
            car.transmission = TRANSMISSION_NORMALIZE.get(value.lower().strip(), value.lower().strip())
            # Try to extract gear count
            gear_m = re.search(r"(\d)", value)
            if gear_m and not car.gears:
                car.gears = int(gear_m.group(1))

        elif field_name == "body_type" and not car.body_type:
            car.body_type = value.strip()

        elif field_name == "doors" and not car.doors:
            d_m = re.search(r"(\d)", value)
            if d_m:
                car.doors = int(d_m.group(1))

        elif field_name == "seats" and not car.seats:
            s_m = re.search(r"(\d)", value)
            if s_m:
                car.seats = int(s_m.group(1))

        elif field_name == "color_exterior" and not car.color_exterior:
            car.color_exterior = value.strip()

        elif field_name == "color_interior" and not car.color_interior:
            car.color_interior = value.strip()

        elif field_name == "previous_owners" and car.previous_owners is None:
            o_m = re.search(r"(\d+)", value)
            if o_m:
                car.previous_owners = int(o_m.group(1))

        elif field_name == "engine_cc" and not car.engine_cc:
            cc_str = re.sub(r"[^\d]", "", value)
            if cc_str:
                car.engine_cc = int(cc_str)

        elif field_name == "co2_emissions" and car.co2_emissions is None:
            co2_m = re.search(r"(\d+)", value)
            if co2_m:
                car.co2_emissions = int(co2_m.group(1))

        elif field_name == "consumption_combined" and car.consumption_combined is None:
            cons_m = re.search(r"(\d+[.,]?\d*)", value)
            if cons_m:
                car.consumption_combined = float(cons_m.group(1).replace(",", "."))

        elif field_name == "emission_class" and not car.emission_class:
            car.emission_class = value.strip()

        elif field_name == "drivetrain" and not car.drivetrain:
            val_lower = value.lower()
            if any(w in val_lower for w in ["allrad", "4x4", "awd", "4wd", "integrale", "intégrale"]):
                car.drivetrain = "AWD"
            elif any(w in val_lower for w in ["hinterrad", "propulsion", "rwd", "posteriore"]):
                car.drivetrain = "RWD"
            elif any(w in val_lower for w in ["vorderrad", "traction", "fwd", "anteriore"]):
                car.drivetrain = "FWD"
            else:
                car.drivetrain = value.strip()

        elif field_name == "condition" and not car.condition:
            val_lower = value.lower()
            if any(w in val_lower for w in ["neu", "neuf", "nuovo", "new"]):
                car.condition = "new"
            else:
                car.condition = "used"

    def _parse_features(self, car: AutoScout24Car, soup: BeautifulSoup):
        """Extract feature/equipment lists from detail page."""
        # Look for equipment sections
        for section in soup.find_all(["section", "div"], class_=re.compile(r"equipment|feature|ausstattung", re.I)):
            items = section.find_all("li")
            for li in items:
                text = li.get_text(strip=True)
                if not text or len(text) > 100:
                    continue
                text_lower = text.lower()

                # Classify into safety, comfort, or general
                safety_words = ["airbag", "abs", "esp", "asr", "isofix", "notbrems", "freinage",
                                "frenata", "spurhalte", "lane", "blind", "toter", "angle mort"]
                comfort_words = ["klimaanlage", "klimatisation", "climatisation", "aria condizionata",
                                 "sitzheizung", "sièges chauffants", "sedili riscaldati",
                                 "tempomat", "cruise", "régulateur", "navi", "gps", "parksen",
                                 "parking", "parcheggio", "leder", "cuir", "pelle"]

                if any(w in text_lower for w in safety_words):
                    if text not in car.safety_features:
                        car.safety_features.append(text)
                elif any(w in text_lower for w in comfort_words):
                    if text not in car.comfort_features:
                        car.comfort_features.append(text)
                else:
                    if text not in car.features:
                        car.features.append(text)

    def _extract_from_text(self, car: AutoScout24Car, text: str):
        """Regex fallback extraction from full page text."""

        # Price
        if not car.price_eur:
            price_m = re.search(r"€\s*([\d.\s]+)", text)
            if price_m:
                car.price_eur = parse_eur_price(price_m.group(0))
            else:
                price_m = re.search(r"([\d.\s]+)\s*€", text)
                if price_m:
                    car.price_eur = parse_eur_price(price_m.group(0))

        # Mileage
        if not car.mileage_km:
            km_m = re.search(r"([\d.]+)\s*km", text, re.I)
            if km_m:
                km_str = km_m.group(1).replace(".", "")
                try:
                    car.mileage_km = int(km_str)
                except ValueError:
                    pass

        # Power
        if not car.power_kw and not car.power_hp:
            pw_m = re.search(r"(\d+)\s*kW\s*\((\d+)\s*(?:PS|hp|ch|CV)\)", text, re.I)
            if pw_m:
                car.power_kw = int(pw_m.group(1))
                car.power_hp = int(pw_m.group(2))

        # Year (skip regex fallback if first_registration is a non-date like "new")
        if not car.year and not (car.first_registration and not re.search(r"\d{4}", car.first_registration)):
            y_m = re.search(r"\b(20[0-2]\d)\b", text)
            if y_m:
                car.year = int(y_m.group(1))

        # VAT deductible
        if not car.vat_deductible:
            if re.search(r"MwSt|TVA|IVA|VAT", text, re.I):
                if re.search(r"ausweisbar|déductible|detraibile|deductible", text, re.I):
                    car.vat_deductible = True

    def _parse_seller(self, car: AutoScout24Car, soup: BeautifulSoup):
        """Extract seller information from the detail page."""
        # Seller name
        seller_el = soup.find(attrs={"data-testid": re.compile(r"seller|dealer|vendor", re.I)})
        if not seller_el:
            seller_el = soup.find(class_=re.compile(r"SellerInfo|DealerInfo|seller", re.I))

        if seller_el:
            name_el = seller_el.find(["h2", "h3", "a", "span"])
            if name_el:
                car.seller_name = name_el.get_text(strip=True)

            # Location
            loc_el = seller_el.find(class_=re.compile(r"location|address|city", re.I))
            if not loc_el:
                loc_el = seller_el.find(attrs={"data-testid": re.compile(r"location|address", re.I)})
            if loc_el:
                car.seller_location = loc_el.get_text(strip=True)

            seller_text = seller_el.get_text(separator=" ", strip=True).lower()
            if any(w in seller_text for w in ["händler", "concessionnaire", "dealer", "concessionario"]):
                car.seller_type = "dealer"
            elif any(w in seller_text for w in ["privat", "particulier", "private", "privato"]):
                car.seller_type = "private"

        car.seller_country = car.country.upper()

    # -------------------------------------------------------------------------
    # Detail page fetch & parse
    # -------------------------------------------------------------------------

    async def _fetch_detail(self, client: httpx.AsyncClient, card_data: Dict) -> Optional[AutoScout24Car]:
        """Fetch and parse a single listing detail page, merging with card data."""
        url = card_data.get("listing_url", "")
        country = card_data.get("country", "de")

        # Start with card data
        car = AutoScout24Car(
            id=card_data.get("id", ""),
            listing_url=url,
            country=country,
            make=card_data.get("make", ""),
            model=card_data.get("model", ""),
            full_name=card_data.get("full_name", ""),
            price_eur=card_data.get("price_eur"),
            first_registration=card_data.get("first_registration", ""),
            mileage_km=card_data.get("mileage_km"),
            year=card_data.get("year"),
            fuel_type=card_data.get("fuel_type", ""),
            power_kw=card_data.get("power_kw"),
            power_hp=card_data.get("power_hp"),
            transmission=card_data.get("transmission", ""),
            seller_type=card_data.get("seller_type", ""),
            seller_name=card_data.get("seller_name", ""),
            seller_location=card_data.get("seller_location", ""),
            image_count=card_data.get("image_count", 0),
        )

        # Fetch detail page
        html = await self.fetch(client, url, country)
        if not html:
            # Use card data only — still valid
            log.debug("Could not fetch detail for %s, using card data only", url)
            self._finalize_car(car)
            return car

        soup = BeautifulSoup(html, "lxml")
        page_text = soup.get_text(separator=" ", strip=True)

        # Priority 1: JSON-LD
        json_ld = self._extract_json_ld(soup)
        if json_ld:
            self._parse_json_ld(car, json_ld)

        # Priority 2: HTML spec sections
        self._parse_html_specs(car, soup)

        # Priority 3: Seller info
        self._parse_seller(car, soup)

        # Priority 4: Regex fallback
        self._extract_from_text(car, page_text)

        # Finalize
        self._finalize_car(car)
        return car

    def _finalize_car(self, car: AutoScout24Car):
        """Fill in derived fields and generate ID."""
        # Build full name if missing or if it looks like a price stub
        if (not car.full_name or "€" in car.full_name or "für" in car.full_name.lower()) and (car.make or car.model):
            parts = [car.make, car.model, car.variant]
            car.full_name = " ".join(p for p in parts if p)

        # Extract make/model from full_name if needed
        if car.full_name and not car.make:
            words = car.full_name.split()
            if words:
                car.make = words[0]
            if len(words) > 1:
                car.model = words[1]

        # Default condition
        if not car.condition:
            if car.mileage_km is not None and car.mileage_km <= 100:
                car.condition = "new"
            elif car.mileage_km is not None:
                car.condition = "used"

        # Generate ID if missing
        if not car.id:
            clean = lambda s: re.sub(r"[^a-z0-9]", "_", s.lower().strip())
            car.id = f"{car.country}_{clean(car.make)}_{clean(car.model)}_{car.year or 'na'}_{id(car) % 10000}"

    # -------------------------------------------------------------------------
    # Taxonomy discovery (per-model mode)
    # -------------------------------------------------------------------------

    def _parse_next_data(self, html: str) -> Optional[dict]:
        """Extract __NEXT_DATA__ JSON from a Next.js page."""
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script", id="__NEXT_DATA__")
        if script and script.string:
            try:
                return json.loads(script.string)
            except json.JSONDecodeError:
                return None
        return None

    async def _discover_makes(self, client: httpx.AsyncClient, country: str) -> List[Dict]:
        """Discover all makes from the AutoScout24 taxonomy.

        Returns list of {label, value, slug}.
        """
        domain = COUNTRIES_MAP[country]
        prefix = COUNTRY_PATH_PREFIX.get(country, "")
        url = f"https://www.{domain}{prefix}/lst/"
        html = await self.fetch(client, url, country)
        if not html:
            log.error("[%s] Failed to fetch taxonomy page", country.upper())
            return []

        data = self._parse_next_data(html)
        if not data:
            log.error("[%s] No __NEXT_DATA__ found on /lst/", country.upper())
            return []

        try:
            page_props = data["props"]["pageProps"]
            taxonomy = page_props.get("taxonomy") or page_props.get("taxonomies", {})
            makes_sorted = taxonomy.get("makesSorted", [])
        except (KeyError, TypeError):
            log.error("[%s] Could not find taxonomy.makesSorted", country.upper())
            return []

        results = []
        for make in makes_sorted:
            label = make.get("label") or make.get("n", "")
            value = make.get("value") or make.get("i", "")
            slug = label.lower().replace(" ", "-") if label else str(value)
            results.append({"label": label, "value": value, "slug": slug})

        log.info("[%s] Discovered %d makes", country.upper(), len(results))
        return results

    async def _discover_models(self, client: httpx.AsyncClient, country: str,
                                make_slug: str, make_id) -> List[Dict]:
        """Discover all models for a make from the taxonomy.

        Uses the `models` dict (keyed by make ID) which contains individual
        models (e.g. 316, 318, 320, M3) rather than `modelGroups` which are
        umbrella categories (e.g. 1er, 3er) that have no direct listings.

        Returns list of {label, value}.
        """
        domain = COUNTRIES_MAP[country]
        prefix = COUNTRY_PATH_PREFIX.get(country, "")
        url = f"https://www.{domain}{prefix}/lst/{make_slug}"
        html = await self.fetch(client, url, country)
        if not html:
            log.warning("[%s] Failed to fetch models for %s", country.upper(), make_slug)
            return []

        data = self._parse_next_data(html)
        if not data:
            log.warning("[%s] No __NEXT_DATA__ for %s", country.upper(), make_slug)
            return []

        try:
            page_props = data["props"]["pageProps"]
            taxonomy = page_props.get("taxonomy") or page_props.get("taxonomies", {})
            # models dict is keyed by make ID (string), each entry is a list of
            # {value, label, makeId, modelLineId}
            models_dict = taxonomy.get("models", {})
            models = models_dict.get(str(make_id)) or models_dict.get(make_id, [])
        except (KeyError, TypeError):
            log.warning("[%s] Could not find models for %s", country.upper(), make_slug)
            return []

        results = []
        for model in models:
            label = model.get("label") or model.get("n", "")
            value = model.get("value") or model.get("i", "")
            results.append({"label": label, "value": value})

        log.info("[%s] %s: %d models", country.upper(), make_slug, len(results))
        return results

    def _card_to_car(self, card: Dict) -> AutoScout24Car:
        """Convert a listing card dict to an AutoScout24Car (no detail page fetch)."""
        car = AutoScout24Car(
            id=card.get("id", ""),
            listing_url=card.get("listing_url", ""),
            country=card.get("country", ""),
            make=card.get("make", ""),
            model=card.get("model", ""),
            full_name=card.get("full_name", ""),
            price_eur=card.get("price_eur"),
            first_registration=card.get("first_registration", ""),
            mileage_km=card.get("mileage_km"),
            year=card.get("year"),
            fuel_type=card.get("fuel_type", ""),
            power_kw=card.get("power_kw"),
            power_hp=card.get("power_hp"),
            transmission=card.get("transmission", ""),
            seller_type=card.get("seller_type", ""),
            seller_name=card.get("seller_name", ""),
            seller_location=card.get("seller_location", ""),
            image_count=card.get("image_count", 0),
        )
        self._finalize_car(car)
        return car

    def _clean_data(self, cars: List[AutoScout24Car], country: str) -> List[AutoScout24Car]:
        """Apply data quality filters and enrichment."""
        before = len(cars)

        # 1. Fuel type filter — keep only standard fuel types
        cars = [c for c in cars if c.fuel_type in ALLOWED_FUEL_TYPES]
        log.info("[%s] Fuel filter: %d → %d", country.upper(), before, len(cars))

        # 2. Price outlier filter — drop < €500 (placeholder/errors)
        cars = [c for c in cars if c.price_eur is not None and c.price_eur >= 500]

        # 3. Near-duplicate detection (same make+model+year+mileage+price)
        seen_sigs: set = set()
        unique = []
        for c in cars:
            sig = (c.make.lower(), c.model.lower(), c.year, c.mileage_km, c.price_eur)
            if sig not in seen_sigs:
                seen_sigs.add(sig)
                unique.append(c)
        cars = unique

        # 4. Normalize make names
        for c in cars:
            key = c.make.lower().strip()
            if key in MAKE_NORMALIZE:
                c.make = MAKE_NORMALIZE[key]
            elif c.make:
                c.make = c.make.title()

        # 5. Price per km ratio
        for c in cars:
            if c.price_eur and c.mileage_km and c.mileage_km > 0:
                c.price_per_km = round(c.price_eur / c.mileage_km, 2)

        # 6. Age calculation from first_registration or year
        current_year = datetime.now().year
        for c in cars:
            if c.first_registration:
                match = re.search(r"(\d{4})", c.first_registration)
                if match:
                    c.age_years = current_year - int(match.group(1))
            if c.age_years is None and c.year:
                c.age_years = current_year - c.year

        # 7. Required fields — drop listings missing price, make, or model
        cars = [c for c in cars if c.price_eur and c.make and c.model]

        # 8. Mileage sanity — drop used cars with age ≥3 years but mileage < 100 km
        def mileage_sane(c):
            if c.condition == "new":
                return True
            if c.age_years is not None and c.age_years >= 3 and c.mileage_km is not None and c.mileage_km < 100:
                return False
            return True
        cars = [c for c in cars if mileage_sane(c)]

        log.info("[%s] After all cleaning: %d → %d cars", country.upper(), before, len(cars))
        return cars

    async def _scrape_country_per_model(self, client: httpx.AsyncClient, country: str) -> List[AutoScout24Car]:
        """Scrape listings per model group (card data only, no detail pages)."""
        all_makes = await self._discover_makes(client, country)
        if not all_makes:
            log.error("[%s] No makes discovered, aborting per-model scrape", country.upper())
            return []

        # Filter by --makes if specified
        if self.makes:
            makes_set = {m.lower() for m in self.makes}
            all_makes = [m for m in all_makes if m["slug"] in makes_set]
            log.info("[%s] Filtered to %d makes", country.upper(), len(all_makes))

        domain = COUNTRIES_MAP[country]
        all_cars: List[AutoScout24Car] = []
        seen_ids: set = set()

        rate_limited = False
        for make_info in all_makes:
            if rate_limited:
                break
            make_slug = make_info["slug"]
            make_id = make_info["value"]
            try:
                models = await self._discover_models(client, country, make_slug, make_id)
            except RateLimitStop:
                log.warning("[%s] Rate limited – stopping per-model scrape", country.upper())
                break
            if not models:
                continue

            for model_info in models:
                model_label = model_info.get("label", "")
                model_id = model_info.get("value", "")
                # Use query params (mmvmk0/mmvmd0) instead of URL path slugs
                # to avoid 404s from label-to-slug mismatches
                params = [f"atype=C", f"page=1", f"mmvmk0={make_id}", f"mmvmd0={model_id}"]
                if self.condition == "new":
                    params.append("ustate=N")
                elif self.condition == "used":
                    params.append("ustate=U")
                if self.min_price is not None:
                    params.append(f"pricefrom={self.min_price}")
                if self.max_price is not None:
                    params.append(f"priceto={self.max_price}")
                prefix = COUNTRY_PATH_PREFIX.get(country, "")
                url = f"https://www.{domain}{prefix}/lst?{'&'.join(params)}"

                try:
                    html = await self.fetch(client, url, country)
                except RateLimitStop:
                    log.warning("[%s] Rate limited – stopping per-model scrape", country.upper())
                    rate_limited = True
                    break
                if not html:
                    continue

                cards = self._parse_listing_cards(html, country)
                added = 0
                for card in cards[:self.per_model_limit]:
                    car = self._card_to_car(card)
                    if car.id and car.id in seen_ids:
                        continue
                    if car.id:
                        seen_ids.add(car.id)
                    all_cars.append(car)
                    added += 1

                if added > 0:
                    log.info("[%s] %s/%s: %d listings", country.upper(), make_slug, model_label, added)

        log.info("[%s] Per-model scrape: %d total cars", country.upper(), len(all_cars))
        return all_cars

    # -------------------------------------------------------------------------
    # Country-level scraping orchestration
    # -------------------------------------------------------------------------

    async def _scrape_country(self, client: httpx.AsyncClient, country: str) -> List[AutoScout24Car]:
        """Scrape listings for one country, handling pagination and makes filter."""
        domain = COUNTRIES_MAP.get(country)
        if not domain:
            log.error("Unknown country code: %s", country)
            return []

        # Reset stop flag for this country
        self._stop_country[country] = False

        if self.per_model:
            return await self._scrape_country_per_model(client, country)

        makes_list = self.makes or [None]  # None means no make filter
        all_cards: List[Dict] = []
        seen_urls: set = set()

        for make in makes_list:
            page = 1
            collected = 0
            make_label = make or "all makes"
            log.info("[%s] Searching %s ...", country.upper(), make_label)

            while collected < self.max_listings:
                url = self._build_search_url(country, make, page)
                try:
                    html = await self.fetch(client, url, country)
                except RateLimitStop:
                    log.warning("[%s] Rate limited – stopping pagination for %s", country.upper(), make_label)
                    break
                if not html:
                    log.warning("[%s] Failed to fetch page %d for %s", country.upper(), page, make_label)
                    break

                cards = self._parse_listing_cards(html, country)
                if not cards:
                    log.info("[%s] No more results on page %d for %s", country.upper(), page, make_label)
                    break

                new_cards = 0
                for card in cards:
                    card_url = card.get("listing_url", "")
                    if card_url and card_url not in seen_urls:
                        seen_urls.add(card_url)
                        all_cards.append(card)
                        new_cards += 1
                        collected += 1
                        if collected >= self.max_listings:
                            break

                log.info("[%s] Page %d: %d new listings (total: %d)", country.upper(), page, new_cards, collected)

                if new_cards == 0:
                    break  # No new results, stop paging

                page += 1

        log.info("[%s] Collected %d listing cards, fetching details...", country.upper(), len(all_cards))

        # Fetch detail pages concurrently
        tasks = [self._fetch_detail(client, card) for card in all_cards]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        cars: List[AutoScout24Car] = []
        for result in results:
            if isinstance(result, AutoScout24Car):
                cars.append(result)
            elif isinstance(result, RateLimitStop):
                log.warning("[%s] Rate limited during detail fetch – proceeding with collected data", country.upper())
            elif isinstance(result, Exception):
                log.error("Error fetching detail: %s", result)

        # Deduplicate by ID
        seen_ids: set = set()
        deduped: List[AutoScout24Car] = []
        for car in cars:
            if car.id and car.id not in seen_ids:
                seen_ids.add(car.id)
                deduped.append(car)
            elif not car.id:
                deduped.append(car)

        log.info("[%s] Scraped %d unique cars", country.upper(), len(deduped))
        cleaned = self._clean_data(deduped, country)
        return cleaned

    # -------------------------------------------------------------------------
    # Main scraping entry point
    # -------------------------------------------------------------------------

    async def scrape_all(self):
        """Run the full scraping pipeline across all configured countries."""
        print("=" * 70)
        print("AUTOSCOUT24 MULTI-COUNTRY CAR SCRAPER")
        print("=" * 70)
        print(f"Started:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Countries:  {', '.join(c.upper() for c in self.countries)}")
        print(f"Condition:  {self.condition}")
        print(f"Max/country:{self.max_listings}")
        if self.makes:
            print(f"Makes:      {', '.join(self.makes)}")
        if self.min_price or self.max_price:
            price_range = f"{self.min_price or '...'} - {self.max_price or '...'} EUR"
            print(f"Price:      {price_range}")
        if self.per_model:
            print(f"Mode:       Per-model ({self.per_model_limit} listings/model)")
        if self.use_playwright:
            print("Mode:       Playwright (headless browser)")
        print()

        # Initialize Playwright if requested
        if self.use_playwright:
            await self._init_playwright()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for country in self.countries:
                cars = await self._scrape_country(client, country)
                self.cars_by_country[country] = cars
                self.cars.extend(cars)

        # Cleanup Playwright
        if self.use_playwright:
            await self._close_playwright()

        print(f"\nTotal cars scraped: {len(self.cars)}")

    async def _init_playwright(self):
        """Initialize Playwright browser if available."""
        try:
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()
            self.playwright_browser = await pw.chromium.launch(headless=True)
            log.info("Playwright browser launched")
        except ImportError:
            log.warning("Playwright not installed, falling back to httpx")
            self.use_playwright = False
        except Exception as exc:
            log.warning("Failed to launch Playwright: %s — falling back to httpx", exc)
            self.use_playwright = False

    async def _close_playwright(self):
        """Close Playwright browser."""
        if self.playwright_browser:
            try:
                await self.playwright_browser.close()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Output: JSON
    # -------------------------------------------------------------------------

    def save_json(self):
        """Save per-country and combined JSON files."""
        timestamp = datetime.now().isoformat()

        # Per-country files
        for country, cars in self.cars_by_country.items():
            filename = f"autoscout24_{country}.json"
            data = {
                "scraped_at": timestamp,
                "source": "autoscout24",
                "countries": [country],
                "stats": self._build_stats([country]),
                "total": len(cars),
                "cars": [asdict(c) for c in cars],
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(cars)} cars to {filename}")

        # Combined file (if multiple countries)
        if len(self.countries) > 1:
            filename = "autoscout24_all.json"
            data = {
                "scraped_at": timestamp,
                "source": "autoscout24",
                "countries": self.countries,
                "stats": self._build_stats(self.countries),
                "total": len(self.cars),
                "cars": [asdict(c) for c in self.cars],
            }
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(self.cars)} cars to {filename}")

    def _build_stats(self, countries: List[str]) -> dict:
        """Build statistics dict for the given countries."""
        cars = []
        for c in countries:
            cars.extend(self.cars_by_country.get(c, []))

        by_country: Dict[str, int] = {}
        by_condition: Dict[str, int] = {}
        by_make: Dict[str, int] = {}

        for car in cars:
            by_country[car.country] = by_country.get(car.country, 0) + 1
            cond = car.condition or "unknown"
            by_condition[cond] = by_condition.get(cond, 0) + 1
            make = car.make or "Unknown"
            by_make[make] = by_make.get(make, 0) + 1

        return {
            "total": len(cars),
            "by_country": by_country,
            "by_condition": by_condition,
            "by_make": dict(sorted(by_make.items(), key=lambda x: -x[1])),
        }

    # -------------------------------------------------------------------------
    # Output: CSV
    # -------------------------------------------------------------------------

    def save_csv(self):
        """Save per-country CSV files."""
        if not self.cars:
            print("No cars to save to CSV")
            return

        fieldnames = list(AutoScout24Car.__dataclass_fields__.keys())

        for country, cars in self.cars_by_country.items():
            if not cars:
                continue
            filename = f"autoscout24_{country}.csv"
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for car in cars:
                    row = asdict(car)
                    # Flatten list fields to semicolon-separated strings
                    for key in ("features", "safety_features", "comfort_features"):
                        if isinstance(row.get(key), list):
                            row[key] = "; ".join(row[key])
                    writer.writerow(row)
            print(f"Saved {len(cars)} cars to {filename}")

        # Combined CSV
        if len(self.countries) > 1:
            filename = "autoscout24_all.csv"
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for car in self.cars:
                    row = asdict(car)
                    for key in ("features", "safety_features", "comfort_features"):
                        if isinstance(row.get(key), list):
                            row[key] = "; ".join(row[key])
                    writer.writerow(row)
            print(f"Saved {len(self.cars)} cars to {filename}")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------

    def print_summary(self):
        """Print a human-readable summary of scraping results."""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        stats = self._build_stats(self.countries)
        print(f"\nTotal cars: {stats['total']}")

        # Per-country breakdown
        if stats["by_country"]:
            print("\nBy country:")
            for country, count in sorted(stats["by_country"].items()):
                print(f"   {country.upper()}: {count}")

        # By condition
        if stats["by_condition"]:
            print("\nBy condition:")
            for cond, count in sorted(stats["by_condition"].items()):
                print(f"   {cond}: {count}")

        # Top makes
        if stats["by_make"]:
            print("\nTop makes:")
            for make, count in list(stats["by_make"].items())[:15]:
                # Price range for this make
                make_prices = [c.price_eur for c in self.cars if c.make == make and c.price_eur]
                if make_prices:
                    print(f"   {make}: {count} cars ({min(make_prices):,} - {max(make_prices):,} EUR)")
                else:
                    print(f"   {make}: {count} cars")

        # Overall price range
        all_prices = [c.price_eur for c in self.cars if c.price_eur]
        if all_prices:
            print(f"\nPrices: {min(all_prices):,} - {max(all_prices):,} EUR (avg: {sum(all_prices) // len(all_prices):,})")

        # Per-country price ranges
        if len(self.countries) > 1:
            print("\nPrice ranges by country:")
            for country in self.countries:
                prices = [c.price_eur for c in self.cars_by_country.get(country, []) if c.price_eur]
                if prices:
                    print(f"   {country.upper()}: {min(prices):,} - {max(prices):,} EUR (avg: {sum(prices) // len(prices):,})")

        # Fuel type breakdown
        fuel_counts: Dict[str, int] = {}
        for car in self.cars:
            ft = car.fuel_type or "unknown"
            fuel_counts[ft] = fuel_counts.get(ft, 0) + 1
        if fuel_counts:
            print("\nBy fuel type:")
            for ft, count in sorted(fuel_counts.items(), key=lambda x: -x[1]):
                print(f"   {ft}: {count}")

    def print_rate_limit_report(self):
        """Print a rate-limit and request metrics report."""
        total = self.request_stats["total"]
        if total == 0:
            return

        success = self.request_stats["success"]
        rate_limited = self.request_stats["rate_limited"]
        blocked = self.request_stats["blocked"]
        errors = self.request_stats["errors"]

        pct = lambda n: f"{n / total * 100:.1f}%" if total else "0%"

        print("\n" + "=" * 70)
        print("RATE LIMIT REPORT")
        print("=" * 70)
        print(f"  Total requests:       {total}")
        print(f"  Success (2xx):        {success} ({pct(success)})")
        print(f"  Rate limited (429):   {rate_limited} ({pct(rate_limited)})")
        print(f"  Blocked (403):        {blocked} ({pct(blocked)})")
        print(f"  Errors:               {errors} ({pct(errors)})")

        # Average delay between requests
        if len(self.request_timestamps) >= 2:
            ts = sorted(self.request_timestamps)
            deltas = [ts[i + 1] - ts[i] for i in range(len(ts) - 1)]
            avg_delay = sum(deltas) / len(deltas)
            print(f"  Avg delay between requests: {avg_delay:.2f}s")

        # Per-country breakdown
        if len(self.request_stats_by_country) > 1:
            print("\n  Per-country breakdown:")
            for country, stats in sorted(self.request_stats_by_country.items()):
                ct = stats["total"]
                print(f"    {country.upper()}: {ct} total, "
                      f"{stats['success']} ok, "
                      f"{stats['rate_limited']} 429, "
                      f"{stats['blocked']} 403, "
                      f"{stats['errors']} err")

        # Auto-tuning suggestion
        ratio_429 = rate_limited / total if total else 0
        print()
        if ratio_429 == 0:
            print(f"  → You can likely increase MAX_CONCURRENT or reduce BASE_DELAY")
        elif ratio_429 < 0.05:
            print(f"  → Current settings are near the limit ({rate_limited} 429s detected)")
        else:
            print(f"  → Reduce MAX_CONCURRENT or increase BASE_DELAY ({rate_limited} 429s = {ratio_429 * 100:.1f}%)")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Scrape AutoScout24 car listings")
    parser.add_argument(
        "--countries", type=str, default="de",
        help="Comma-separated country codes: de,fr,it,be",
    )
    parser.add_argument(
        "--condition", type=str, default="all", choices=["new", "used", "all"],
        help="Filter by condition (default: all)",
    )
    parser.add_argument(
        "--max-listings", type=int, default=100,
        help="Max listings per country (default: 100)",
    )
    parser.add_argument(
        "--makes", type=str,
        help="Comma-separated makes: bmw,audi,mercedes-benz",
    )
    parser.add_argument(
        "--min-price", type=int,
        help="Minimum price EUR",
    )
    parser.add_argument(
        "--max-price", type=int,
        help="Maximum price EUR",
    )
    parser.add_argument(
        "--use-playwright", action="store_true",
        help="Use Playwright for JS rendering (anti-bot fallback)",
    )
    parser.add_argument(
        "--per-model", action="store_true",
        help="Discover all makes/models from taxonomy and scrape per model group",
    )
    parser.add_argument(
        "--per-model-limit", type=int, default=10,
        help="Max listings per model group in per-model mode (default: 10)",
    )
    args = parser.parse_args()

    countries = [c.strip().lower() for c in args.countries.split(",")]
    makes = [m.strip().lower() for m in args.makes.split(",")] if args.makes else None

    scraper = AutoScout24Scraper(
        countries=countries,
        condition=args.condition,
        max_listings=args.max_listings,
        makes=makes,
        min_price=args.min_price,
        max_price=args.max_price,
        use_playwright=args.use_playwright,
        per_model=args.per_model,
        per_model_limit=args.per_model_limit,
    )

    await scraper.scrape_all()
    scraper.save_json()
    scraper.save_csv()
    scraper.print_summary()
    scraper.print_rate_limit_report()

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
