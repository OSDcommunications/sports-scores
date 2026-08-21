import json
import re
from playwright.sync_api import sync_playwright

MONTHS = {"1": "JAN", "2": "FEB", "3": "MAR", "4": "APR", "5": "MAY", "6": "JUN",
          "7": "JUL", "8": "AUG", "9": "SEP", "10": "OCT", "11": "NOV", "12": "DEC"}

TEAMS = [
    {
        "name": "Ogden High Varsity Football",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/football/schedule/",
        "filename": "ogden_football_schedule.json"
    },
    {
        "name": "Ogden High JV Football",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/football/junior-varsity/schedule/",
        "filename": "ogden_jv_football_schedule.json"
    },
    {
        "name": "Ogden High Girls Soccer",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/girls-soccer/schedule/",
        "filename": "ogden_girls_soccer_schedule.json"
    },
    {
        "name": "Ogden High Girls Tennis",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/girls-tennis/schedule/",
        "filename": "ogden_girls_tennis_schedule.json"
    },
    {
        "name": "Ogden High Girls Volleyball",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/girls-volleyball/schedule/",
        "filename": "ogden_girls_volleyball_schedule.json"
    }
]

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
            "date": date_str,
            "time": time_str,
            "date_display": date_display,
            "opponent": opp_clean,
            "location": "Home" if is_home else "Away",
            "is_home": is_home,
            "is_region": is_region,
            "result": result_display,
            "result_display": result_display
        })
    return games

def scrape_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        for team in TEAMS:
            print(f"Scraping {team['name']}...")
            try:
                page = context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page.goto(team["url"], wait_until="domcontentloaded", timeout=60000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(3000)
                
                body_text = page.inner_text("body")
                games = parse_schedule_text(body_text)
                page.close()
                
                data = {
                    "team": team["name"],
                    "updated": True,
                    "games": games
                }
                with open(team["filename"], "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                print(f"  -> Saved {len(games)} games to {team['filename']}")
            except Exception as e:
                print(f"  -> Error scraping {team['name']}: {e}")
                
        browser.close()

if __name__ == "__main__":
    scrape_all()
