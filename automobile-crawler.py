"""
automobile.tn Production Scraper
================================
Extracts all car listings with full details for the Tunisia Car Import Chatbot.

Features:
- Scrapes used car listings with pagination
- Extracts all car details (price, specs, features)
- Saves to JSON and CSV
- FCR eligibility tagging
- Ready for database insertion

Run:
    python scraper_automobile_tn.py

Requirements:
    pip install crawl4ai beautifulsoup4 lxml
"""

import asyncio
import json
import csv
import re
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List
from bs4 import BeautifulSoup

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class CarListing:
    """Unified car listing data structure"""
    # Identification
    id: str
    source: str = "automobile_tn"
    url: str = ""
    
    # Basic info
    brand: str = ""
    model: str = ""
    variant: str = ""
    title: str = ""
    
    # Technical specs
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    cv_fiscal: Optional[int] = None
    fuel_type: str = ""
    transmission: str = ""
    body_type: str = ""
    
    # Pricing
    price_tnd: Optional[int] = None
    price_rating: str = ""  # "Très bon prix", "Bon prix", etc.
    price_type: str = ""    # "regular", "non_dedouane", "sous_leasing"
    
    # Location & Seller
    location: str = ""
    seller_type: str = ""   # "Professionnel" or "Particulier"
    seller_name: str = ""
    phone: str = ""
    
    # Registration
    serie_tu: str = ""
    
    # Media
    image_url: str = ""
    
    # Features
    features: List[str] = None
    description: str = ""
    
    # FCR Eligibility (computed)
    fcr_eligible: bool = False
    fcr_eligible_reason: str = ""
    
    # Metadata
    scraped_at: str = ""
    
    def __post_init__(self):
        if self.features is None:
            self.features = []
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class AutomobileTnScraper:
    """Scraper for automobile.tn used car listings"""
    
    BASE_URL = "https://www.automobile.tn"
    OCCASION_URL = "https://www.automobile.tn/fr/occasion"
    
    # Fuel type mapping
    FUEL_MAPPING = {
        'essence': 'essence',
        'diesel': 'diesel',
        'hybride léger essence': 'hybrid_mild_essence',
        'hybride essence': 'hybrid_essence',
        'hybride rechargeable essence': 'hybrid_rechargeable',
        'hybride léger diesel': 'hybrid_mild_diesel',
        'hybride rechargeable diesel': 'hybrid_rechargeable_diesel',
        'electrique': 'electric',
        'électrique': 'electric',
    }
    
    # Body type mapping
    BODY_MAPPING = {
        'citadine': 'citadine',
        'suv': 'suv',
        'compacte': 'compacte',
        'berline': 'berline',
        'coupé': 'coupe',
        'utilitaire': 'utilitaire',
        'monospace': 'monospace',
        'pick up': 'pickup',
        'cabriolet': 'cabriolet',
    }
    
    def __init__(self):
        self.cars: List[CarListing] = []
        self.browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
    
    async def scrape_listing_page(self, crawler: AsyncWebCrawler, page_num: int = 1) -> List[CarListing]:
        """Scrape a single page of listings"""
        
        url = f"{self.OCCASION_URL}/{page_num}" if page_num > 1 else self.OCCASION_URL
        print(f"  📄 Fetching page {page_num}: {url}")
        
        config = CrawlerRunConfig(
            page_timeout=60000,
            delay_before_return_html=3.0  # Wait for JS
        )
        
        result = await crawler.arun(url=url, config=config)
        
        if not result.success:
            print(f"  ❌ Failed to fetch page {page_num}: {result.error_message}")
            return []
        
        # Parse HTML
        soup = BeautifulSoup(result.html, 'lxml')
        cars = self._extract_cars_from_page(soup)
        
        print(f"  ✅ Found {len(cars)} cars on page {page_num}")
        return cars
    
    def _extract_cars_from_page(self, soup: BeautifulSoup) -> List[CarListing]:
        """Extract car listings from parsed HTML"""
        cars = []
        
        # Find all car listing links - they follow pattern /fr/occasion/brand/model/id
        listing_links = soup.find_all('a', href=re.compile(r'/fr/occasion/[^/]+/[^/]+/\d+'))
        
        # Get unique listing URLs
        seen_urls = set()
        listing_urls = []
        for link in listing_links:
            href = link.get('href', '')
            if href and href not in seen_urls and '/financement' not in href:
                seen_urls.add(href)
                listing_urls.append(href)
        
        # Now extract data for each listing
        # The page structure has cards with images and details
        
        # Find all listing cards - look for divs containing listing images
        # Each card typically has: image, title (h2), details, price
        
        for url in listing_urls:
            car = self._extract_car_from_url_context(soup, url)
            if car:
                cars.append(car)
        
        return cars
    
    def _extract_car_from_url_context(self, soup: BeautifulSoup, listing_url: str) -> Optional[CarListing]:
        """Extract car data from the context around a listing URL"""
        
        # Extract ID from URL
        id_match = re.search(r'/(\d+)$', listing_url)
        if not id_match:
            return None
        
        listing_id = id_match.group(1)
        full_url = f"{self.BASE_URL}{listing_url}"
        
        # Find the link element
        link_elem = soup.find('a', href=listing_url)
        if not link_elem:
            return None
        
        # Get the parent container (usually a few levels up)
        # Look for the card container
        parent = link_elem
        for _ in range(10):  # Go up max 10 levels
            parent = parent.parent
            if parent is None:
                break
            # Check if this looks like a card container
            parent_text = parent.get_text() if parent else ""
            if len(parent_text) > 200 and ('km' in parent_text.lower() or 'cv' in parent_text.lower()):
                break
        
        if parent is None:
            return None
        
        card_text = parent.get_text(separator=' ', strip=True)
        card_html = str(parent)
        
        # Initialize car
        car = CarListing(id=listing_id, url=full_url)
        
        # Extract brand and model from URL
        url_parts = listing_url.split('/')
        if len(url_parts) >= 5:
            car.brand = url_parts[3].replace('-', ' ').title()
            car.model = url_parts[4].replace('-', ' ').title()
        
        # Extract title (usually in h2)
        h2 = parent.find('h2')
        if h2:
            car.title = h2.get_text(strip=True)
            # Parse variant from title
            if car.brand and car.model:
                variant = car.title.replace(car.brand, '').replace(car.model, '').strip()
                car.variant = variant
        
        # Extract image
        img = parent.find('img')
        if img:
            car.image_url = img.get('src', '')
        
        # Extract price (look for DT or TND)
        price_match = re.search(r'(\d{1,3}[\s\u00a0]?\d{3})\s*(?:DT|TND|Dinars?)', card_text, re.IGNORECASE)
        if price_match:
            price_str = price_match.group(1).replace(' ', '').replace('\u00a0', '')
            try:
                car.price_tnd = int(price_str)
            except:
                pass
        
        # Alternative: Look for price in specific elements
        if not car.price_tnd:
            # Sometimes price is in a specific class
            price_elem = parent.find(class_=re.compile(r'price|prix', re.I))
            if price_elem:
                price_text = price_elem.get_text()
                price_match = re.search(r'(\d[\d\s\u00a0]*\d{3})', price_text)
                if price_match:
                    price_str = price_match.group(1).replace(' ', '').replace('\u00a0', '')
                    try:
                        car.price_tnd = int(price_str)
                    except:
                        pass
        
        # Extract price rating
        price_ratings = ['Très bon prix', 'Bon prix', 'Prix équitable', 'Prix élevé', 'Prix très élevé']
        for rating in price_ratings:
            if rating.lower() in card_text.lower():
                car.price_rating = rating
                break
        
        # Extract year
        year_match = re.search(r'\b(20[0-2]\d)\b', card_text)
        if year_match:
            car.year = int(year_match.group(1))
        
        # Alternative year format: 04/2021
        date_match = re.search(r'(\d{2})/?(20[0-2]\d)', card_text)
        if date_match and not car.year:
            car.year = int(date_match.group(2))
        
        # Extract mileage
        km_match = re.search(r'(\d[\d\s\u00a0]*\d{3})\s*km', card_text, re.IGNORECASE)
        if km_match:
            km_str = km_match.group(1).replace(' ', '').replace('\u00a0', '')
            try:
                car.mileage_km = int(km_str)
            except:
                pass
        
        # Extract CV fiscal
        cv_match = re.search(r'(\d{1,2})\s*(?:CV|cv)', card_text)
        if cv_match:
            car.cv_fiscal = int(cv_match.group(1))
        
        # Extract fuel type
        text_lower = card_text.lower()
        if 'hybride rechargeable' in text_lower:
            car.fuel_type = 'hybrid_rechargeable'
        elif 'hybride' in text_lower:
            car.fuel_type = 'hybrid'
        elif 'électrique' in text_lower or 'electrique' in text_lower:
            car.fuel_type = 'electric'
        elif 'diesel' in text_lower:
            car.fuel_type = 'diesel'
        elif 'essence' in text_lower:
            car.fuel_type = 'essence'
        
        # Extract transmission
        if 'automatique' in text_lower or 'bva' in text_lower:
            car.transmission = 'automatic'
        elif 'manuelle' in text_lower:
            car.transmission = 'manual'
        
        # Extract body type
        for body_fr, body_en in self.BODY_MAPPING.items():
            if body_fr in text_lower:
                car.body_type = body_en
                break
        
        # Extract Série TU
        serie_match = re.search(r'(?:Série|Serie|TU)\s*(\d{3})', card_text, re.IGNORECASE)
        if serie_match:
            car.serie_tu = f"TU {serie_match.group(1)}"
        
        # Extract phone
        phone_match = re.search(r'(\d{2}[\s]?\d{3}[\s]?\d{3})', card_text)
        if phone_match:
            car.phone = phone_match.group(1).replace(' ', '')
        
        # Extract seller info
        seller_elem = parent.find('img', alt=re.compile(r'proposé par|Véhicule proposé', re.I))
        if seller_elem:
            car.seller_type = 'Professionnel'
            car.seller_name = seller_elem.get('alt', '').replace('Véhicule proposé par ', '')
        else:
            car.seller_type = 'Particulier'
        
        # Extract location from governorats
        governorats = ['Tunis', 'Ariana', 'Ben Arous', 'La Manouba', 'Nabeul', 'Sousse', 
                       'Sfax', 'Monastir', 'Bizerte', 'Gabès', 'Médenine', 'Kairouan']
        for gov in governorats:
            if gov.lower() in text_lower:
                car.location = gov
                break
        
        # Store description
        car.description = card_text[:500] if len(card_text) > 500 else card_text
        
        # Compute FCR eligibility
        self._compute_fcr_eligibility(car)
        
        return car
    
    def _compute_fcr_eligibility(self, car: CarListing):
        """Determine if car is eligible for FCR import regimes"""
        
        current_year = datetime.now().year
        reasons = []
        eligible = True
        
        # Check age (max 8 years for FCR Famille)
        if car.year:
            age = current_year - car.year
            if age > 8:
                eligible = False
                reasons.append(f"Trop ancien ({age} ans > 8 ans max)")
        
        # Check engine size based on CV fiscal (approximation)
        # FCR Famille: Essence ≤1600cc, Diesel ≤1900cc
        if car.cv_fiscal and car.fuel_type:
            if car.fuel_type == 'essence' and car.cv_fiscal > 9:
                eligible = False
                reasons.append(f"CV fiscal trop élevé pour essence ({car.cv_fiscal} CV)")
            elif car.fuel_type == 'diesel' and car.cv_fiscal > 10:
                eligible = False
                reasons.append(f"CV fiscal trop élevé pour diesel ({car.cv_fiscal} CV)")
        
        # Electric and PHEV are always eligible
        if car.fuel_type in ['electric', 'hybrid_rechargeable']:
            eligible = True
            reasons = ["Véhicule électrique/hybride rechargeable - toujours éligible"]
        
        car.fcr_eligible = eligible
        car.fcr_eligible_reason = "; ".join(reasons) if reasons else "Potentiellement éligible"
    
    async def scrape_all_pages(self, max_pages: int = 5) -> List[CarListing]:
        """Scrape multiple pages of listings"""
        
        print("=" * 70)
        print("🚗 AUTOMOBILE.TN SCRAPER - Production Mode")
        print("=" * 70)
        print(f"\n📋 Scraping up to {max_pages} pages...")
        
        all_cars = []
        
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            for page in range(1, max_pages + 1):
                cars = await self.scrape_listing_page(crawler, page)
                all_cars.extend(cars)
                
                if not cars:
                    print(f"  ⚠️ No cars found on page {page}, stopping.")
                    break
                
                # Small delay between pages
                if page < max_pages:
                    await asyncio.sleep(1)
        
        # Remove duplicates
        seen_ids = set()
        unique_cars = []
        for car in all_cars:
            if car.id not in seen_ids:
                seen_ids.add(car.id)
                unique_cars.append(car)
        
        self.cars = unique_cars
        print(f"\n✅ Total unique cars scraped: {len(self.cars)}")
        
        return self.cars
    
    def save_to_json(self, filename: str = "automobile_tn_cars.json"):
        """Save cars to JSON file"""
        data = [asdict(car) for car in self.cars]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"📁 Saved {len(self.cars)} cars to {filename}")
    
    def save_to_csv(self, filename: str = "automobile_tn_cars.csv"):
        """Save cars to CSV file"""
        if not self.cars:
            print("⚠️ No cars to save")
            return
        
        fieldnames = list(asdict(self.cars[0]).keys())
        # Remove complex fields for CSV
        fieldnames = [f for f in fieldnames if f != 'features']
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for car in self.cars:
                row = asdict(car)
                del row['features']  # Remove list field
                writer.writerow(row)
        
        print(f"📁 Saved {len(self.cars)} cars to {filename}")
    
    def print_summary(self):
        """Print summary statistics"""
        if not self.cars:
            print("⚠️ No cars to summarize")
            return
        
        print("\n" + "=" * 70)
        print("📊 SCRAPING SUMMARY")
        print("=" * 70)
        
        print(f"\n📈 Total cars: {len(self.cars)}")
        
        # By brand
        brands = {}
        for car in self.cars:
            brands[car.brand] = brands.get(car.brand, 0) + 1
        print(f"\n🏭 Top brands:")
        for brand, count in sorted(brands.items(), key=lambda x: -x[1])[:10]:
            print(f"   {brand}: {count}")
        
        # By fuel type
        fuels = {}
        for car in self.cars:
            if car.fuel_type:
                fuels[car.fuel_type] = fuels.get(car.fuel_type, 0) + 1
        print(f"\n⛽ By fuel type:")
        for fuel, count in sorted(fuels.items(), key=lambda x: -x[1]):
            print(f"   {fuel}: {count}")
        
        # FCR eligible
        fcr_count = sum(1 for car in self.cars if car.fcr_eligible)
        print(f"\n✅ FCR eligible: {fcr_count}/{len(self.cars)} ({100*fcr_count/len(self.cars):.1f}%)")
        
        # Price range
        prices = [car.price_tnd for car in self.cars if car.price_tnd]
        if prices:
            print(f"\n💰 Price range: {min(prices):,} - {max(prices):,} TND")
            print(f"   Average: {sum(prices)//len(prices):,} TND")
        
        # Sample cars
        print("\n" + "-" * 70)
        print("🚙 SAMPLE CARS (First 5)")
        print("-" * 70)
        for car in self.cars[:5]:
            print(f"\n  {car.brand} {car.model} {car.variant}")
            print(f"    Price: {car.price_tnd:,} TND" if car.price_tnd else "    Price: N/A")
            print(f"    Year: {car.year} | Mileage: {car.mileage_km:,} km" if car.mileage_km else f"    Year: {car.year}")
            print(f"    Fuel: {car.fuel_type} | CV: {car.cv_fiscal}")
            print(f"    FCR Eligible: {'✅' if car.fcr_eligible else '❌'} {car.fcr_eligible_reason}")
            print(f"    URL: {car.url}")


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point"""
    
    scraper = AutomobileTnScraper()
    
    # Scrape pages (adjust max_pages as needed)
    await scraper.scrape_all_pages(max_pages=3)
    
    # Save results
    scraper.save_to_json()
    scraper.save_to_csv()
    
    # Print summary
    scraper.print_summary()
    
    print("\n✨ Scraping complete!")


if __name__ == "__main__":
    asyncio.run(main())