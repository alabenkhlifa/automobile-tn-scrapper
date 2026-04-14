# 9annas.tn Used Cars Scraper - Design Spec

## Context

We need a scraper for 9annas.tn, a Tunisian used car aggregator that indexes ~12.5k car listings. Unlike the existing automobile.tn scrapers which parse HTML, 9annas exposes a clean JSON API. The output will be a CSV file following the existing `used_cars` schema (with image fields added), intended for use in an external project.

## API Endpoints

### POST `https://api.9annas.tn/search`

Initial search. Returns first 20 results.

**Request body:**
```json
{
  "query": "voiture",
  "location": {"id": null, "name": "", "radius": 10},
  "filter": {
    "categoryId": 1,
    "priceMin": null,
    "priceMax": null,
    "onlyWithPrice": false
  },
  "isUserSearch": true,
  "isFilterSearch": true
}
```

**Response:**
```json
{
  "hits": 12574,
  "categoryHits": {"1": 12574},
  "ads": [
    {
      "id": 26054587,
      "title": "Golf7 tdi bleu motion",
      "description": "Golf7 tdi high line...\n\nKilométrage: 240 km\nCouleur du véhicule: Gris\n...",
      "price": 41500,
      "categoryId": 1,
      "location": "Nabeul, Nabeul",
      "distance": null,
      "timestamp": 1776172543,
      "thumbnail": "https://cdn.9annas.tn/thumbs/52109/26054587_e09894de47066725.jpg",
      "externalId": "69de3dfc25a6db48ab1b9897",
      "sourceId": 2,
      "crawlerId": 10
    }
  ],
  "similarSearch": {...},
  "affiliates": []
}
```

### POST `https://api.9annas.tn/searchmore`

Paginated results. Returns array of 20 ads (no wrapper object).

**Request body:**
```json
{
  "searchQuery": { /* same as /search body */ },
  "offset": "DHBGFGCFAEGHBKKIKG"
}
```

**Response:** `[{ad}, {ad}, ...]` (plain array, same ad schema as above)

### Cursor Encoding (reverse-engineered from website JS)

```python
def num_to_letters(n: int) -> str:
    """Each digit d -> chr(98 + d) -> uppercase. 0->B, 1->C, ..., 9->K"""
    return ''.join(chr(98 + int(d)).upper() for d in str(n))

def encode_offset(ad_id: int, timestamp: int) -> str:
    return num_to_letters(ad_id + 99) + "A" + num_to_letters(timestamp - 1420070400)
```

The offset is computed from the **last ad** in the current page: `encode_offset(last_ad.id, last_ad.timestamp)`.

### GET `https://api.9annas.tn/images/?ad={id}`

Returns array of full-resolution image URLs for an ad.

**Response:**
```json
[
  "https://storage.googleapis.com/tayara-migration-yams-pro/48/48669290-55df-40e2-a2cd-62cd7268bbe0",
  "https://storage.googleapis.com/tayara-migration-yams-pro/fe/fe7ce388-..."
]
```

Images are WebP format. Thumbnails (from search) are JPEG.

## Data Model

```python
@dataclass
class NineannasCar:
    # Identification
    id: str = ""
    brand: str = ""
    model: str = ""
    full_name: str = ""          # title from search result
    url: str = ""                # constructed: https://9annas.tn/ad/{id}

    # Pricing
    price_tnd: Optional[int] = None

    # Vehicle History
    year: Optional[int] = None
    mileage_km: Optional[int] = None
    condition: str = ""          # "Nouveau", "Avec kilométrage"

    # Engine & Performance
    cv_fiscal: Optional[int] = None
    cylindree: str = ""          # "1.6L", "<1.0L"

    # Fuel & Transmission
    fuel_type: str = ""          # Essence, Diesel
    transmission: str = ""       # Manuelle, Automatique

    # Body
    body_type: str = ""          # Berline, Compacte, SUV, Utilitaire
    color_exterior: str = ""

    # Location
    governorate: str = ""        # Extracted from location field (2nd part after comma)
    location: str = ""           # Full location string from API

    # Images
    thumbnail: str = ""          # CDN thumbnail URL
    images: List[str] = field(default_factory=list)  # Full image URLs

    # Metadata
    listing_date: str = ""       # ISO date from timestamp field
    scraped_at: str = ""
```

### Description Parsing

All specs are extracted from the `description` field via regex. Key-value pairs appear as:

| Description Key | Dataclass Field | Regex |
|---|---|---|
| `Marque` | `brand` | `Marque:\s*(.+?)\\s*$` |
| `Modèle` | `model` | `Modèle:\s*(.+?)\\s*$` |
| `Année` | `year` | `Année:\s*(\d{4})` |
| `Kilométrage` | `mileage_km` | `Kilométrage:\s*(\d[\d\s]*)\s*km` |
| `Puissance fiscale` | `cv_fiscal` | `Puissance fiscale:\s*(\d+)\s*CV` |
| `Cylindrée` | `cylindree` | `Cylindrée:\s*(.+?)\\s*$` |
| `Carburant` | `fuel_type` | `Carburant:\s*(.+?)\\s*$` |
| `Boite` | `transmission` | `Boite:\s*(.+?)\\s*$` |
| `Type de carrosserie` | `body_type` | `Type de carrosserie:\s*(.+?)\\s*$` |
| `Couleur du véhicule` | `color_exterior` | `Couleur du véhicule:\s*(.+?)\\s*$` |
| `Etat du véhicule` | `condition` | `Etat du véhicule:\s*(.+?)\\s*$` |

**Notes:**
- All regex use `re.MULTILINE` flag so `$` matches line endings
- `price: 0` in API response means no price listed, mapped to `price_tnd: None`
- Non-breaking spaces (`\u00a0`) handled in mileage parsing (French formatting)

## Architecture

### Incremental Scraping

The scraper supports incremental mode to avoid re-fetching known listings:

1. On startup, load existing `9annas_tn_used_cars.json` if present
2. Build a set of known ad IDs from the existing data
3. During pagination, when a batch contains an ad whose ID is already known, stop fetching new pages (since results are ordered by most recent first, hitting a known ID means all subsequent pages are already scraped)
4. Merge new ads with existing data (new ads prepended, preserving order)
5. Export the merged dataset

This means daily GitHub Actions runs only fetch new listings posted since the last run.

### Scraping Flow

```
1. Load existing data → known_ids set
2. POST /search → 20 ads + total hits count
3. Loop:
   a. For current batch of 20 ads:
      - Check if any ad ID is in known_ids → if yes, keep only new ads from batch, STOP pagination
      - Parse specs from description
      - Queue image fetches (concurrent, semaphore=10)
   b. Compute offset from last ad in batch
   c. POST /searchmore with offset → next 20 ads
   d. Repeat until empty response, all hits fetched, or known ID hit
4. Merge new ads with existing data
5. Deduplicate by ad ID
6. Export to JSON + CSV
```

### Rate Limiting

- **Search pages**: sequential, 0.3s delay between `/search` and `/searchmore` calls
- **Image fetches**: `asyncio.Semaphore(10)`, 0.2s delay per request + jitter
- **Error handling**: exponential backoff on 429/403 (2s, 4s, 8s, max 3 retries)
- Image fetches are batched per search page (overlapped with search pagination)

### Concurrency Pattern

```
for each search page:
    fetch 20 ads (sequential, rate limited)
    spawn 20 concurrent image fetches (semaphore-limited)
    compute next offset
```

## Output

### Files
- `9annas_tn_used_cars.json` - full structured data with metadata and stats
- `9annas_tn_used_cars.csv` - flattened, `images` column as semicolon-separated URLs

### JSON Structure
```json
{
  "scraped_at": "2026-04-14T...",
  "source": "9annas.tn",
  "total": 12574,
  "stats": {
    "with_price": 10234,
    "with_images": 11890,
    "top_brands": {"Volkswagen": 1200, "Peugeot": 980, ...},
    "avg_price": 45000,
    "price_range": [5000, 350000]
  },
  "cars": [...]
}
```

### CSV Columns
All dataclass fields flattened. `images` list joined by `;`.

## CLI Interface

```bash
python 9annas_scraper.py                    # incremental scrape (merges with existing data)
python 9annas_scraper.py --full             # full scrape (ignores existing data)
python 9annas_scraper.py --max-pages 5      # limit to 5 pages (100 ads)
python 9annas_scraper.py --skip-images      # skip image URL fetching
```

## GitHub Actions Integration

Add to `.github/workflows/scrape.yml`:

```yaml
- name: Run 9annas used cars scraper
  run: python 9annas_scraper.py
  timeout-minutes: 30
```

And update the git add step to include the new output files:

```yaml
git add ... 9annas_tn_used_cars.json 9annas_tn_used_cars.csv
```

The scraper runs in incremental mode by default, so daily runs only fetch new listings since the last commit.

## File

Single file: `9annas_scraper.py` (following existing project convention of one file per scraper)

## Dependencies

No new dependencies. Uses existing: `httpx`, `asyncio`, `json`, `csv`, `re`, `dataclasses`.

## Verification

1. Run `python 9annas_scraper.py --max-pages 2` to test with 40 ads
2. Verify CSV has correct columns matching UsedCar schema + thumbnail + images
3. Verify image URLs are accessible (spot-check a few)
4. Run full scrape with `--full` and verify deduplication (total should match API hits count)
5. Run again without `--full` to verify incremental mode stops at known listings
6. Compare a few entries against the 9annas.tn website to confirm data accuracy
