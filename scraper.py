import json
import re
import datetime
from playwright.sync_api import sync_playwright

TEAMS = [
    # ================= OGDEN HIGH SCHOOL =================
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
    },

    # ================= BEN LOMOND HIGH SCHOOL =================
    {
        "name": "Ben Lomond Varsity Football",
        "url": "https://www.maxpreps.com/ut/ogden/ben-lomond-scots/football/schedule/",
        "output": "ben_lomond_football_schedule.json"
    },
    {
        "name": "Ben Lomond JV Football",
        "url": "https://www.maxpreps.com/ut/ogden/ben-lomond-scots/football/jv/schedule/",
        "output": "ben_lomond_jv_football_schedule.json"
    },
    {
        "name": "Ben Lomond Varsity Girls Soccer",
        "url": "https://www.maxpreps.com/ut/ogden/ben-lomond-scots/soccer/girls/schedule/",
        "output": "ben_lomond_girls_soccer_schedule.json"
    },
    {
        "name": "Ben Lomond JV Girls Soccer",
        "url": "https://www.maxpreps.com/ut/ogden/ben-lomond-scots/soccer/girls/jv/schedule/",
        "output": "ben_lomond_jv_girls_soccer_schedule.json"
    },
    {
        "name": "Ben Lomond Varsity Girls Tennis",
        "url": "https://www.maxpreps.com/ut/ogden/ben-lomond-scots/tennis/girls/schedule/",
        "output": "ben_lomond_girls_tennis_schedule.json"
    },
    {
        "name": "Ben Lomond Varsity Girls Volleyball",
        "url": "https://www.maxpreps.com/ut/ogden/ben-lomond-scots/volleyball/girls/schedule/",
        "output": "ben_lomond_girls_volleyball_schedule.json"
    }
]

def parse_game_row(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return None

    date_str = lines[0] if len(lines) > 0 else ""
    opponent_str = ""
    result_str = ""
    location_str = ""
    time_str = ""

    for line in lines[1:]:
        if any(marker in line.lower() for marker in ["vs", "@", "against"]):
            opponent_str = line
        elif re.search(r'\b(W|L|T)\b|\d+-\d+', line):
            result_str = line
        elif any(loc in line.lower() for loc in ["home", "away", "neutral"]):
            location_str = line
        elif re.search(r'\d+:\d+|\b(am|pm)\b', line.lower()):
            time_str = line
        elif not opponent_str:
            opponent_str = line

    return {
        "date": date_str,
        "opponent": opponent_str,
        "opponent_name": opponent_str.replace("vs", "").replace("@", "").strip(),
        "result": result_str,
        "score": result_str,
        "time": time_str,
        "location": location_str,
        "raw": " | ".join(lines),
        "details": lines
    }

def scrape_team_schedule(page, team):
    print(f"Scraping schedule for {team['name']}...")
    games = []
    wins, losses, ties = 0, 0, 0

    try:
        page.goto(team["url"], wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)

        # Target table rows and container elements on MaxPreps
        rows = page.query_selector_all("tr, li[class*='contest'], div[class*='contest-row'], div[class*='ContestRow']")

        for row in rows:
            text = row.inner_text().strip()
            if text and len(text) > 8:
                parsed = parse_game_row(text)
                if parsed and parsed["date"]:
                    games.append(parsed)

                    res_upper = parsed["result"].upper()
                    if "W" in res_upper:
                        wins += 1
                    elif "L" in res_upper:
                        losses += 1
                    elif "T" in res_upper:
                        ties += 1

    except Exception as e:
        print(f"  [ERROR] Scraping failed for {team['name']}: {e}")

    overall_record = f"{wins}-{losses}" + (f"-{ties}" if ties > 0 else "")

    # Structured schema compatible with both legacy and new frontend widgets
    schedule_data = {
        "team": team["name"],
        "source_url": team["url"],
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall_record": overall_record,
        "record": overall_record,
        "metrics": {
            "overall_record": overall_record,
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "total_games": len(games)
        },
        "game_metrics": {
            "wins": wins,
            "losses": losses,
            "ties": ties
        },
        "games": games,
        "schedule": games
    }

    with open(team["output"], "w", encoding="utf-8") as f:
        json.dump(schedule_data, f, indent=2, ensure_ascii=False)

    print(f"  [SUCCESS] {len(games)} games scraped -> {team['output']}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for team in TEAMS:
            scrape_team_schedule(page, team)

        browser.close()

if __name__ == "__main__":
    main()
