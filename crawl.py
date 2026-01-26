"""
Tunisia Car Import Chatbot - Crawl4AI Simple Test
==================================================
Simplified version - just tests if we can fetch pages without strict selectors.

Run:
    python crawl.py
"""

import asyncio
import json
from datetime import datetime

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

# =============================================================================
# WEBSITES TO TEST
# =============================================================================

WEBSITES = [
    {
        "name": "automobile.tn (Used)",
        "country": "🇹🇳 Tunisia",
        "url": "https://www.automobile.tn/fr/occasion",
    },
    {
        "name": "automobile.tn (New)",
        "country": "🇹🇳 Tunisia",
        "url": "https://www.automobile.tn/fr/neuf",
    },
    {
        "name": "mobile.de",
        "country": "🇩🇪 Germany",
        "url": "https://www.mobile.de/",
    },
    {
        "name": "autoscout24.de",
        "country": "🇩🇪 Germany",
        "url": "https://www.autoscout24.de/",
    },
    {
        "name": "leboncoin.fr",
        "country": "🇫🇷 France",
        "url": "https://www.leboncoin.fr/",
    },
]

# =============================================================================
# SIMPLE TEST
# =============================================================================

async def test_website(crawler, site):
    """Test a single website - just fetch, no strict selectors"""
    
    result = {
        "name": site["name"],
        "country": site["country"],
        "url": site["url"],
        "success": False,
        "html_length": 0,
        "markdown_length": 0,
        "title": "",
        "error": None,
        "time": 0
    }
    
    start = datetime.now()
    
    try:
        # Simple config - no wait_for selectors
        config = CrawlerRunConfig(
            page_timeout=60000,  # 60 seconds
        )
        
        crawl_result = await crawler.arun(url=site["url"], config=config)
        
        result["time"] = (datetime.now() - start).total_seconds()
        
        if crawl_result.success:
            result["success"] = True
            result["html_length"] = len(crawl_result.html) if crawl_result.html else 0
            result["markdown_length"] = len(crawl_result.markdown) if crawl_result.markdown else 0
            
            # Try to get page title
            if crawl_result.html:
                import re
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', crawl_result.html, re.IGNORECASE)
                if title_match:
                    result["title"] = title_match.group(1).strip()[:100]
            
            # Check for anti-bot
            html_lower = crawl_result.html.lower() if crawl_result.html else ""
            if any(x in html_lower for x in ["captcha", "blocked", "access denied", "cloudflare-turnstile"]):
                result["error"] = "⚠️ Possible anti-bot detected"
        else:
            result["error"] = crawl_result.error_message
            
    except Exception as e:
        result["error"] = str(e)[:200]
        result["time"] = (datetime.now() - start).total_seconds()
    
    return result


async def main():
    print("=" * 70)
    print("🚗 CRAWL4AI SIMPLE TEST - Tunisia Car Import Chatbot")
    print("=" * 70)
    print(f"\nTesting {len(WEBSITES)} websites (simple fetch, no strict selectors)...\n")
    
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    results = []
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i, site in enumerate(WEBSITES, 1):
            print(f"[{i}/{len(WEBSITES)}] {site['name']} {site['country']}")
            print(f"    URL: {site['url']}")
            
            result = await test_website(crawler, site)
            results.append(result)
            
            if result["success"]:
                status = "✅ SUCCESS" if not result["error"] else "⚠️ PARTIAL"
                print(f"    Status: {status} ({result['time']:.1f}s)")
                print(f"    HTML: {result['html_length']:,} bytes | Markdown: {result['markdown_length']:,} bytes")
                print(f"    Title: {result['title'][:60]}...")
                if result["error"]:
                    print(f"    Note: {result['error']}")
            else:
                print(f"    Status: ❌ FAILED ({result['time']:.1f}s)")
                print(f"    Error: {result['error']}")
            print()
    
    # Summary
    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    success = sum(1 for r in results if r["success"] and not r["error"])
    partial = sum(1 for r in results if r["success"] and r["error"])
    failed = sum(1 for r in results if not r["success"])
    
    print(f"\n✅ Fully working:   {success}/{len(results)}")
    print(f"⚠️ Partial/blocked: {partial}/{len(results)}")
    print(f"❌ Failed:          {failed}/{len(results)}")
    
    # Save results
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📁 Results saved to: test_results.json")
    
    # Show markdown sample from first successful site
    print("\n" + "=" * 70)
    print("📄 SAMPLE MARKDOWN OUTPUT")
    print("=" * 70)
    
    for site in WEBSITES:
        print(f"\nTrying to get sample from {site['name']}...")
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                config = CrawlerRunConfig(page_timeout=30000)
                result = await crawler.arun(url=site["url"], config=config)
                if result.success and result.markdown:
                    print(f"\n--- First 1500 chars of markdown from {site['name']} ---\n")
                    print(result.markdown[:1500])
                    print("\n--- End of sample ---")
                    break
        except Exception as e:
            print(f"Could not get sample: {e}")
            continue
    
    return results


# =============================================================================
# BONUS: Test a search page with actual car listings
# =============================================================================

async def test_search_page():
    """Test scraping an actual search results page"""
    
    print("\n" + "=" * 70)
    print("🔍 TESTING SEARCH RESULTS PAGE")
    print("=" * 70)
    
    # automobile.tn search page with filters
    search_url = "https://www.automobile.tn/fr/occasion?energy=1&gearbox=1"  # Essence + Manual
    
    browser_config = BrowserConfig(headless=True, verbose=False)
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"\nFetching: {search_url}")
        
        config = CrawlerRunConfig(
            page_timeout=60000,
            delay_before_return_html=3.0  # Wait 3s for JS to load
        )
        
        result = await crawler.arun(url=search_url, config=config)
        
        if result.success:
            print(f"✅ Success! Got {len(result.html):,} bytes of HTML")
            print(f"   Markdown: {len(result.markdown):,} chars")
            
            # Save the markdown for inspection
            with open("automobile_tn_sample.md", "w") as f:
                f.write(result.markdown)
            print(f"   Saved markdown to: automobile_tn_sample.md")
            
            # Try to find car listings in the HTML
            import re
            
            # Look for price patterns (TND)
            prices = re.findall(r'(\d{1,3}[\s,.]?\d{3})\s*(?:TND|DT)', result.html, re.IGNORECASE)
            if prices:
                print(f"   Found {len(prices)} price mentions!")
                print(f"   Sample prices: {prices[:5]}")
            
            # Look for car brands
            brands = ["Volkswagen", "Peugeot", "Renault", "Toyota", "Hyundai", "Kia", "BMW", "Mercedes", "Audi"]
            found_brands = [b for b in brands if b.lower() in result.html.lower()]
            if found_brands:
                print(f"   Found brands: {found_brands}")
                
        else:
            print(f"❌ Failed: {result.error_message}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n🔧 Starting Crawl4AI simple tests...\n")
    
    # Run basic connectivity tests
    asyncio.run(main())
    
    # Run search page test
    asyncio.run(test_search_page())
    
    print("\n✨ All tests complete!")