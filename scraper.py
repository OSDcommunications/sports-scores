import os
import json
import requests
from bs4 import BeautifulSoup

# Define headers to mimic a web browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

# Master list of teams to scrape (OHS + BLHS)
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

def scrape_schedule(team_info):
    name = team_info["name"]
    url = team_info["url"]
    output_filename = team_info["output"]

    print(f"Fetching schedule for {name}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] Failed to fetch {url}: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    games = []

    # MaxPreps schedules typically format games in rows or cards
    # Adjust selectors as necessary based on MaxPreps page DOM
    rows = soup.find_all("tr") or soup.find_all("div", class_="contest-row")

    for row in rows:
        text = row.get_text(separator=" ", strip=True)
        if text:
            games.append({"raw": text})

    schedule_data = {
        "team": name,
        "source_url": url,
        "total_games": len(games),
        "games": games
    }

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(schedule_data, f, indent=2, ensure_ascii=False)

    print(f"  [SUCCESS] Saved {len(games)} entries to {output_filename}")

def main():
    print("Starting schedule scraper for OHS and BLHS sports...\n")
    for team in TEAMS:
        scrape_schedule(team)
    print("\nScraper completed successfully!")

if __name__ == "__main__":
    main()
