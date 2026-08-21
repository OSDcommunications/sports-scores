import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

TARGET_URL = "https://www.maxpreps.com/ut/ogden/ogden-tigers/football/schedule/"

MONTHS = {"1": "JAN", "2": "FEB", "3": "MAR", "4": "APR", "5": "MAY", "6": "JUN",
          "7": "JUL", "8": "AUG", "9": "SEP", "10": "OCT", "11": "NOV", "12": "DEC"}

def parse_game_row(date_raw, opponent_raw, result_raw):
    # Determine Home vs Away
    is_home = True
    opp_clean = opponent_raw.strip()
    if opp_clean.startswith("@"):
        is_home = False
        opp_clean = opp_clean.lstrip("@").strip()
    elif opp_clean.lower().startswith("vs"):
        is_home = True
        opp_clean = re.sub(r"^vs\.?\s*", "", opp_clean, flags=re.IGNORECASE).strip()

    # Detect Region Game marker (*)
    is_region = "*" in opp_clean or "*" in opponent_raw
    opp_clean = opp_clean.replace("*", "").strip()

    # Separate Date & Time cleanly
    date_match = re.search(r'([A-Za-z]{3}\s+\d{1,2}|\d{1,2}/\d{1,2})', date_raw)
    time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm)?)', date_raw, re.IGNORECASE)

    date_part = date_match.group(1) if date_match else "TBD"
    time_part = time_match.group(1).upper() if time_match else ""

    if "/" in date_part:
        m, d = date_part.split("/")
        date_part = f"{MONTHS.get(m, m)} {d}"
    else:
        date_part = date_part.upper()

    if time_part and "PM" not in time_part and "AM" not in time_part:
        time_part += " PM"

    date_display = f"{date_part} • {time_part}" if time_part else date_part

    # Clean Result/Status
    res_clean = result_raw.strip()
    if not res_clean or res_clean.lower() in ["preview game", "preview", "upcoming"]:
        res_clean = "Preview Game"

    return {
        "date_display": date_display,
        "opponent": opp_clean,
        "is_home": is_home,
        "is_region": is_region,
        "result_display": res_clean
    }

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
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(4000)
        html_content = page.content()
        browser.close()

    soup = BeautifulSoup(html_content, "html.parser")
    rows = soup.find_all("tr")
    
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if len(cells) >= 2 and any(re.search(r'\d{1,2}/\d{1,2}', cells[0]) or m in cells[0].lower() for m in ["aug", "sep", "oct", "nov"]):
            date_raw = cells[0]
            opp_raw = cells[1]
            res_raw = cells[2] if len(cells) > 2 else "Preview Game"
            games.append(parse_game_row(date_raw, opp_raw, res_raw))

    output_path = "ogden_football_schedule.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"team": "Ogden High Varsity Football", "updated": True, "games": games}, f, indent=2)
    print(f"Successfully saved {len(games)} games.")

if __name__ == "__main__":
    fetch_ogden_football_schedule()
