import json
import os
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
        # Wait for HTML structure to load instead of waiting for ad scripts
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000) # Pause 5 seconds for game data to render
        
        html_content = page.content()
        browser.close()

    soup = BeautifulSoup(html_content, "html.parser")
    
    # Locate schedule entries
    game_rows = soup.find_all("tr", class_=lambda c: c and "contest" in c.lower()) or soup.find_all("li", class_=lambda c: c and "contest" in c.lower())
    
    for row in game_rows:
        try:
            date_elem = row.find(class_=lambda c: c and "date" in c.lower())
            opponent_elem = row.find(class_=lambda c: c and "opponent" in c.lower())
            result_elem = row.find(class_=lambda c: c and "result" in c.lower())
            
            date = date_elem.get_text(strip=True) if date_elem else "TBD"
            opponent = opponent_elem.get_text(strip=True) if opponent_elem else "Unknown Opponent"
            result = result_elem.get_text(strip=True) if result_elem else "Upcoming"

            games.append({
                "date": date,
                "opponent": opponent,
                "result": result
            })
        except Exception:
            continue

    output_path = "ogden_football_schedule.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"team": "Ogden High Varsity Football", "updated": True, "games": games}, f, indent=2)
        
    print(f"Successfully saved {len(games)} games to {output_path}")

if __name__ == "__main__":
    fetch_ogden_football_schedule()
