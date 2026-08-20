import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

TARGET_URL = "https://www.maxpreps.com/ut/ogden/ogden-tigers/football/schedule/"

def fetch_ogden_football_schedule():
    games = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"Fetching schedule from {TARGET_URL}...")
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        
        # Scroll down to ensure all lazy-loaded content loads
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(4000)
        
        html_content = page.content()
        browser.close()

    soup = BeautifulSoup(html_content, "html.parser")
    
    # Method 1: Extract structured JSON-LD embedded by MaxPreps
    script_tags = soup.find_all("script", type="application/ld+json")
    for script in script_tags:
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            
            for item in items:
                if item.get("@type") in ["SportsEvent", "Event"]:
                    raw_date = item.get("startDate", "TBD")
                    date = raw_date.split("T")[0] if "T" in raw_date else raw_date
                    
                    competitors = item.get("competitor", [])
                    opponent = "Unknown Opponent"
                    if isinstance(competitors, list):
                        for comp in competitors:
                            name = comp.get("name", "")
                            if "Ogden" not in name and name:
                                opponent = name
                                break
                    
                    result = "Upcoming"
                    if "eventStatus" in item and "Completed" in item.get("eventStatus", ""):
                        result = "Final"
                        
                    games.append({
                        "date": date,
                        "opponent": opponent,
                        "result": result
                    })
        except Exception:
            continue

    # Method 2: Fallback table text scraper if JSON-LD is absent
    if not games:
        rows = soup.find_all("tr")
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if len(cells) >= 2 and any(m in cells[0].lower() for m in ["aug", "sep", "oct", "nov", "10/", "8/", "9/"]):
                games.append({
                    "date": cells[0],
                    "opponent": cells[1],
                    "result": cells[2] if len(cells) > 2 else "Upcoming"
                })

    output_path = "ogden_football_schedule.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"team": "Ogden High Varsity Football", "updated": True, "games": games}, f, indent=2)
        
    print(f"Successfully saved {len(games)} games to {output_path}")

if __name__ == "__main__":
    fetch_ogden_football_schedule()
