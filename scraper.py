import json
import re
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

TEAMS = [
    {
        "name": "Ogden High Varsity Football",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/football/schedule/",
        "output": "ogden_football_schedule.json"
    },
    {
        "name": "Ogden High JV Football",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/football/jv/schedule/",
        "output": "ogden_jv_football_schedule.json"
    },
    {
        "name": "Ogden High Varsity Girls Soccer",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/soccer/girls/schedule/",
        "output": "ogden_girls_soccer_schedule.json"
    },
    {
        "name": "Ogden High JV Girls Soccer",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/soccer/girls/jv/schedule/",
        "output": "ogden_jv_girls_soccer_schedule.json"
    },
    {
        "name": "Ogden High Varsity Girls Volleyball",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/volleyball/girls/schedule/",
        "output": "ogden_girls_volleyball_schedule.json"
    },
    {
        "name": "Ogden High Varsity Girls Tennis",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/tennis/girls/schedule/",
        "output": "ogden_girls_tennis_schedule.json"
    }
]

MONTHS_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}
MONTH_NAMES = {v: k for k, v in MONTHS_MAP.items()}

def parse_game_row(date_raw, opponent_raw, result_raw, full_row_text=""):
    combined = f"{opponent_raw} {result_raw} {full_row_text}"
    
    # 1. Clean up Opponent Name & Strip MaxPreps Metadata
    opp_clean = opponent_raw.strip()
    opp_clean = re.sub(r'(Match Details|Location:|Box Score|Contest Details|Game Details).*$', '', opp_clean, flags=re.IGNORECASE)
    opp_clean = re.sub(r'\([^\)]*\)', '', opp_clean).strip()

    is_home = True
    if opp_clean.startswith("@"):
        is_home = False
        opp_clean = opp_clean.lstrip("@").strip()
    elif opp_clean.lower().startswith("vs"):
        is_home = True
        opp_clean = re.sub(r"^vs\.?\s*", "", opp_clean, flags=re.IGNORECASE).strip()

    is_region = "*" in opp_clean or "*" in opponent_raw or "*" in full_row_text
    opp_clean = opp_clean.replace("*", "").strip()

    # 2. Parse Date and Time
    cleaned_date = re.sub(r'(\d{1,2}/\d{1,2})(\d{1,2}:)', r'\1 \2', date_raw.strip())
    cleaned_date = re.sub(r'([a-zA-Z]{3}\s*\d{1,2})(\d{1,2}:)', r'\1 \2', cleaned_date)

    month_num, day_num = 8, 1
    slash_match = re.search(r'(\d{1,2})/(\d{1,2})', cleaned_date)
    text_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{1,2})', cleaned_date, re.IGNORECASE)

    if slash_match:
        month_num = int(slash_match.group(1))
        day_num = int(slash_match.group(2))
    elif text_match:
        m_str = text_match.group(1).upper()
        month_num = MONTHS_MAP.get(m_str, 8)
        day_num = int(text_match.group(2))

    month_name = MONTH_NAMES.get(month_num, "AUG")
    date_part = f"{month_name} {day_num}"

    time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm)?)', cleaned_date, re.IGNORECASE)
    time_part = time_match.group(1).upper() if time_match else ""
    if time_part and "PM" not in time_part and "AM" not in time_part:
        time_part += " PM"

    date_display = f"{date_part} • {time_part}" if time_part else date_part

    # 3. Parse Result & Score (Supports W/L 36-13, win 9 lost 1, etc.)
    res_clean = "Preview Game"
    wl_match = re.search(r'\b([WL])\b\s*(\d+)\s*[-–]\s*(\d+)', combined, re.IGNORECASE)
    win_lost_match = re.search(r'win\s*(\d+)\s*lost?\s*(\d+)', combined, re.IGNORECASE)
    score_only = re.search(r'(\d+)\s*[-–]\s*(\d+)', result_raw + " " + full_row_text)

    if wl_match:
        res_clean = f"{wl_match.group(1).upper()} {wl_match.group(2)}-{wl_match.group(3)}"
    elif win_lost_match:
        res_clean = f"W {win_lost_match.group(1)}-{win_lost_match.group(2)}"
    elif score_only and any(w in combined.lower() for w in ["win", "won", "w"]):
        res_clean = f"W {score_only.group(1)}-{score_only.group(2)}"
    elif score_only and any(l in combined.lower() for l in ["loss", "lost", "l"]):
        res_clean = f"L {score_only.group(1)}-{score_only.group(2)}"
    elif result_raw.strip() and result_raw.strip().lower() not in ["preview game", "preview", "upcoming", "report score"]:
        res_clean = result_raw.strip()

    # Sort key for fall sports
    sort_month = month_num + 12 if month_num < 6 else month_num
    sort_key = sort_month * 100 + day_num

    return {
        "date_display": date_display,
        "opponent": opp_clean,
        "is_home": is_home,
        "is_region": is_region,
        "result_display": res_clean,
        "sort_key": sort_key
    }

def fetch_team_schedule(team_name, target_url, output_path, browser):
    print(f"Fetching schedule for {team_name}...")
    games = []

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    page = context.new_page()

    try:
        page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)

        html_content = page.content()
        soup = BeautifulSoup(html_content, "html.parser")

        rows = soup.find_all("tr")
        for row in rows:
            tds = row.find_all(["td", "th"])
            cells = [td.get_text(" ", strip=True) for td in tds]
            row_full_text = row.get_text(" ", strip=True)

            if len(cells) >= 2 and any(re.search(r'(\d{1,2}/\d{1,2}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', cells[0], re.IGNORECASE) for _ in [1]):
                date_str = cells[0]
                opp_str = cells[1]
                if any(h in date_str.lower() for h in ["date", "time", "schedule", "overall", "league"]):
                    continue
                res_str = cells[2] if len(cells) > 2 else "Preview Game"

                parsed = parse_game_row(date_str, opp_str, res_str, row_full_text)
                if not any(g["date_display"] == parsed["date_display"] and g["opponent"] == parsed["opponent"] for g in games):
                    games.append(parsed)

        games.sort(key=lambda x: x["sort_key"])

    except Exception as e:
        print(f"Error fetching {team_name}: {e}")
    finally:
        context.close()

    if games:
        for g in games:
            g.pop("sort_key", None)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"team": team_name, "updated": True, "games": games}, f, indent=2)
        print(f"Successfully saved {len(games)} games to {output_path}")
    else:
        print(f"Warning: Could not parse games for {team_name}.")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for team in TEAMS:
            fetch_team_schedule(team["name"], team["url"], team["output"], browser)
            time.sleep(2)
        browser.close()

if __name__ == "__main__":
    main()
