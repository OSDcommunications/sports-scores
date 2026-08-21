import json
import re
from playwright.sync_api import sync_playwright

TARGET_URL = "https://www.maxpreps.com/ut/ogden/ogden-tigers/football/schedule/"

MONTHS = {"1": "JAN", "2": "FEB", "3": "MAR", "4": "APR", "5": "MAY", "6": "JUN",
          "7": "JUL", "8": "AUG", "9": "SEP", "10": "OCT", "11": "NOV", "12": "DEC"}

def parse_schedule_text(text):
    games = []
    pattern = r'(\d{1,2}/\d{1,2})\s*\n?\s*(\d{1,2}:\d{2}\s*(?:am|pm)?)\s*\n?\s*(vs|@)\s*\n?\s*([^\n]+)'
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    
    for i, match in enumerate(matches):
        date_str = match.group(1)
        time_str = match.group(2).upper()
        location_str = match.group(3)
        opp_raw = match.group(4).strip()
        
        start_idx = match.end()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(text)
        tail_text = text[start_idx:end_idx]
        
        res_match = re.search(r'([WL]\s*\d+-\d+|Preview Game|Upcoming|Final)', tail_text, re.IGNORECASE)
        result_display = res_match.group(1).strip() if res_match else "Preview Game"
        
        m, d = date_str.split("/")
        month_name = MONTHS.get(m, "AUG")
        date_display = f"{month_name} {d} • {time_str}"
        
        is_home = location_str.lower() == "vs"
        is_region = "*" in opp_raw
        opp_clean = opp_raw.replace("*", "").strip()
        
        games.append({
            "date_display": date_display,
            "opponent": opp_clean,
            "is_home": is_home,
            "is_region": is_region,
            "result_display": result_display
        })
    return games

def fetch_ogden_football_schedule():
    games = []
    with sync_playwright() as p:
        # Launch browser with anti-detection flags
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        # Mask webdriver signature
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"Navigating to {TARGET_URL}...")
        response = page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        
        if response:
            print(f"HTTP Status: {response.status}")
        print(f"Page Title: {page.title()}")
        
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(3000)
        
        body_text = page.inner_text("body")
        print(f"Captured Body Text Length: {len(body_text)} chars")
        
        browser.close()

    games = parse_schedule_text(body_text)
    print(f"Parsed {len(games)} games from page body.")
    
    output_path = "ogden_football_schedule.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"team": "Ogden High Varsity Football", "updated": True, "games": games}, f, indent=2)

if __name__ == "__main__":
    fetch_ogden_football_schedule()
