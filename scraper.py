import json
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

def scrape_schedule(page, team):
    print(f"Fetching schedule for {team['name']}...")
    games = []
    wins, losses, ties = 0, 0, 0

    try:
        page.goto(team["url"], wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(3000)

        # Target MaxPreps contest rows
        rows = page.query_selector_all("tr, div[class*='contest-row'], div[class*='ContestRow']")
        
        for row in rows:
            text = row.inner_text().strip()
            if text and len(text) > 5:
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                
                game_obj = {
                    "raw": " | ".join(lines),
                    "date": lines[0] if len(lines) > 0 else "",
                    "opponent": lines[1] if len(lines) > 1 else "",
                    "result": lines[2] if len(lines) > 2 else "",
                    "details": lines
                }
                games.append(game_obj)
                
                full_str = " ".join(lines).upper()
                if " W " in f" {full_str} " or full_str.startswith("W "):
                    wins += 1
                elif " L " in f" {full_str} " or full_str.startswith("L "):
                    losses += 1
                elif " T " in f" {full_str} " or full_str.startswith("T "):
                    ties += 1

    except Exception as e:
        print(f"  [ERROR] Scraping failed for {team['name']}: {e}")

    schedule_data = {
        "team": team["name"],
        "source_url": team["url"],
        "last_updated": datetime.datetime.now().isoformat(),
        "metrics": {
            "total_games": len(games),
            "wins": wins,
            "losses": losses,
            "ties": ties
        },
        "games": games
    }

    with open(team["output"], "w", encoding="utf-8") as f:
        json.dump(schedule_data, f, indent=2, ensure_ascii=False)

    print(f"  [SUCCESS] Saved {len(games)} entries to {team['output']}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        for team in TEAMS:
            scrape_schedule(page, team)

        browser.close()

if __name__ == "__main__":
    main()
