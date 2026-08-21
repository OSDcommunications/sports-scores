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
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/football/jv/schedule/",
        "filename": "ogden_jv_football_schedule.json"
    },
    {
        "name": "Ogden High Girls Soccer",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/soccer/girls/schedule/",
        "filename": "ogden_girls_soccer_schedule.json"
    },
    {
        "name": "Ogden High JV Girls Soccer",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/soccer/girls/jv/schedule/",
        "filename": "ogden_jv_girls_soccer_schedule.json"
    },
    {
        "name": "Ogden High Girls Tennis",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/tennis/girls/schedule/",
        "filename": "ogden_girls_tennis_schedule.json"
    },
    {
        "name": "Ogden High Girls Volleyball",
        "url": "https://www.maxpreps.com/ut/ogden/ogden-tigers/volleyball/schedule/",
        "filename": "ogden_girls_volleyball_schedule.json"
    }
]

def parse_schedule_text(text):
    raw_games = []
    pattern = r'(\d{1,2})/([0-3]?\d)\s*\n?\s*(\d{1,2}:\d{2}\s*(?:[ap]\.?m\.?|[ap])?|TBA|tba)?\s*\n?\s*(vs|@)\s*\n?\s*([^\n]+)'
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    
    for i, match in enumerate(matches):
        m_str, d_str = match.group(1), match.group(2)
        time_raw = match.group(3)
        location_str = match.group(4)
        opp_raw = match.group(5).strip()
        
        # Clean Opponent and Location
        is_home = location_str.lower() == "vs"
        is_region = "*" in opp_raw
        opp_clean = opp_raw.replace("*", "").strip()
        opp_clean = re.sub(r'^\d{1,2}:\d{2}\s*(?:AM|PM|a|p)?\s*', '', opp_clean, flags=re.IGNORECASE).strip()
        
        # Clean Time
        if not time_raw or time_raw.upper() in ["TBA", "TBD"]:
            time_clean = "TBA"
        else:
            time_clean = time_raw.upper().replace('.', '').strip()
            if re.search(r'\d\s*[AP]$', time_clean):
                time_clean += 'M'
            
        start_idx = match.end()
        end_idx = matches[i+1].start() if i + 1 < len(matches) else len(text)
        tail_text = text[start_idx:end_idx]
        
        # Parse Game Result / Status
        res_match = re.search(r'([WLwl]\s*\d+-\d+(?:\s*\([^)]+\))?|Preview Game|Upcoming|Final|TBD|Box Score|Preview|Report Score)', tail_text)
        result_display = "Preview Game"
        if res_match:
            matched_res = res_match.group(1).strip()
            if matched_res.lower() not in ["preview", "box score", "report score", "preview game", "upcoming", "tbd"]:
                # Normalize lowercase w/l to uppercase W/L
                if matched_res[0].lower() in ['w', 'l']:
                    result_display = matched_res[0].upper() + matched_res[1:]
                else:
                    result_display = matched_res
        
        m_num, d_num = int(m_str), int(d_str)
        month_name = MONTHS.get(m_str, "AUG")
        date_display = f"{month_name} {d_str} • {time_clean}"
        
        raw_games.append({
            "month_num": m_num,
            "day_num": d_num,
            "date": f"{m_num}/{d_num}",
            "time": time_clean,
            "date_display": date_display,
            "opponent": opp_clean,
            "location": "Home" if is_home else "Away",
            "is_home": is_home,
            "is_region": is_region,
            "result": result_display,
            "result_display": result_display
        })
        
    # Deduplicate entries (prefers score entries over preview summaries)
    unique_games = {}
    for g in raw_games:
        key = (g["month_num"], g["day_num"], g["opponent"].lower())
        if key not in unique_games:
            unique_games[key] = g
        else:
            existing = unique_games[key]
            if ("W " in g["result_display"] or "L " in g["result_display"]) and not ("W " in existing["result_display"] or "L " in existing["result_display"]):
                unique_games[key] = g

    # Sort chronologically (August - December first, January - May second)
    sorted_games = sorted(
        unique_games.values(),
        key=lambda x: (x["month_num"] if x["month_num"] >= 6 else x["month_num"] + 12, x["day_num"])
    )
    
    # Strip internal keys before JSON export
    final_games = []
    for g in sorted_games:
        game_copy = dict(g)
        game_copy.pop("month_num", None)
        game_copy.pop("day_num", None)
        final_games.append(game_copy)
        
    return final_games

def scrape_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        
        for team in TEAMS:
            print(f"Scraping {team['name']}...")
            try:
                page = context.new_page()
                page.goto(team["url"], wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(3000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                
                body_text = page.inner_text("body")
                games = parse_schedule_text(body_text)
                page.close()
                
                data = {"team": team["name"], "updated": True, "games": games}
                with open(team["filename"], "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                print(f"  -> Saved {len(games)} games to {team['filename']}")
            except Exception as e:
                print(f"  -> Error scraping {team['name']}: {e}")
                
        browser.close()

if __name__ == "__main__":
    scrape_all()
