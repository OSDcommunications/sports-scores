import json
import re
import datetime
import os
import urllib.request
from playwright.sync_api import sync_playwright

# All 12 teams for Ogden High and Ben Lomond High
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}

def extract_contests_from_json(obj):
    """Recursively find contest list in MaxPreps Next.js JSON tree."""
    if isinstance(obj, dict):
        for key in ["contests", "scheduleEntries", "games", "contestList"]:
            if key in obj and isinstance(obj[key], list) and len(obj[key]) > 0:
                return obj[key]
        for v in obj.values():
            res = extract_contests_from_json(v)
            if res:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = extract_contests_from_json(item)
            if res:
                return res
    return []

def fetch_schedule_direct_http(url):
    """Method 1: Direct HTTP GET requesting MaxPreps Next.js embedded data."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8')
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
            if match:
                raw_data = json.loads(match.group(1))
                return extract_contests_from_json(raw_data)
    except Exception as e:
        print(f"  [INFO] HTTP direct fetch skipped/blocked ({e})")
    return []

def parse_game_block(lines):
    if not lines:
        return None
    raw_str = " | ".join(lines)
    date_str, time_str, opponent_str, result_str = "", "", "", ""
    location_str, is_home, is_away, is_region = "Home", True, False, False

    for line in lines:
        l_lower = line.lower()
        if not date_str and (re.search(r'\b(\d{1,2}/\d{1,2})\b', line) or any(m in l_lower for m in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'])):
            m = re.search(r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)', line)
            date_str = m.group(1) if m else line
        if re.search(r'\d{1,2}:\d{2}\s*(?:am|pm)?', l_lower):
            m = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm)?)', l_lower)
            if m: time_str = m.group(1).upper()
        if '@' in line or 'vs' in l_lower or 'against' in l_lower or 'at ' in l_lower:
            opponent_str = line
            if '@' in line or 'at ' in l_lower:
                location_str, is_home, is_away = "Away", False, True
            elif 'vs' in l_lower:
                location_str, is_home, is_away = "Home", True, False
        if '*' in line or 'league' in l_lower or 'region' in l_lower or 'conference' in l_lower:
            is_region = True
        if re.search(r'\b[WLT]\b|\b\d+-\d+\b', line):
            result_str = line

    opp_clean = re.sub(r'^(vs\.?|@|at)\s*', '', opponent_str, flags=re.IGNORECASE).replace('*', '').strip()
    return {
        "date": date_str or (lines[0] if len(lines) > 0 else ""),
        "time": time_str,
        "date_time": f"{date_str} {time_str}".strip(),
        "opponent": opponent_str or opp_clean,
        "opponent_name": opp_clean,
        "opponentName": opp_clean,
        "location": location_str,
        "is_home": is_home,
        "isHome": is_home,
        "is_away": is_away,
        "isAway": is_away,
        "is_region": is_region,
        "isRegion": is_region,
        "result": result_str,
        "score": result_str,
        "raw": raw_str
    }

def process_and_save_team(team, raw_contests):
    games = []
    for c in raw_contests:
        if isinstance(c, dict):
            date_val = c.get("date", c.get("dateString", ""))
            opp_data = c.get("opponent", {})
            opp_name = opp_data.get("name", "Opponent") if isinstance(opp_data, dict) else str(opp_data)
            res_data = c.get("result", {})
            res_text = res_data.get("text", res_data.get("score", "")) if isinstance(res_data, dict) else str(res_data)

            is_away = c.get("isAway", False) or (isinstance(opp_data, dict) and opp_data.get("isHome", False))
            is_home = not is_away
            is_reg = c.get("isConference", c.get("isLeague", False))

            games.append({
                "date": str(date_val),
                "time": str(c.get("time", "")),
                "date_time": f"{date_val} {c.get('time', '')}".strip(),
                "opponent": f"{'@' if is_away else 'vs'} {opp_name}",
                "opponent_name": opp_name,
                "opponentName": opp_name,
                "location": "Away" if is_away else "Home",
                "is_home": is_home,
                "isHome": is_home,
                "is_away": is_away,
                "isAway": is_away,
                "is_region": is_reg,
                "isRegion": is_reg,
                "result": str(res_text),
                "score": str(res_text),
                "raw": f"{date_val} | {opp_name} | {res_text}"
            })

    wins, losses, ties, home_cnt, away_cnt, region_cnt = 0, 0, 0, 0, 0, 0
    for g in games:
        res_u = g["result"].upper()
        if "W" in res_u: wins += 1
        elif "L" in res_u: losses += 1
        elif "T" in res_u: ties += 1
        if g["is_home"]: home_cnt += 1
        if g["is_away"]: away_cnt += 1
        if g["is_region"]: region_cnt += 1

    total_games = len(games)
    rec_str = f"{wins}-{losses}" + (f"-{ties}" if ties > 0 else "")

    metrics_obj = {
        "overall_record": rec_str,
        "record": rec_str,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "total_games": total_games,
        "total_matches": total_games,
        "totalMatches": total_games,
        "home": home_cnt,
        "home_matches": home_cnt,
        "homeMatches": home_cnt,
        "away": away_cnt,
        "away_matches": away_cnt,
        "awayMatches": away_cnt,
        "region": region_cnt,
        "region_matches": region_cnt,
        "regionMatches": region_cnt
    }

    payload = {
        "team": team["name"],
        "source_url": team["url"],
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall_record": rec_str,
        "record": rec_str,
        "total_matches": total_games,
        "totalMatches": total_games,
        "home_matches": home_cnt,
        "homeMatches": home_cnt,
        "away_matches": away_cnt,
        "awayMatches": away_cnt,
        "region_matches": region_cnt,
        "regionMatches": region_cnt,
        "metrics": metrics_obj,
        "game_metrics": metrics_obj,
        "games": games,
        "schedule": games
    }

    # Only overwrite if we found games OR if no file exists yet
    if total_games > 0 or not os.path.exists(team["output"]):
        with open(team["output"], "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"  [SUCCESS] Wrote {total_games} games -> {team['output']}")
    else:
        print(f"  [WARNING] 0 games scraped for {team['name']}. Preserving existing {team['output']} file.")

def main():
    print("Starting MaxPreps Schedule Scraper...")
    
    # Track teams that need Playwright fallback
    fallback_teams = []

    for team in TEAMS:
        print(f"\nProcessing {team['name']}...")
        contests = fetch_schedule_direct_http(team["url"])
        if contests:
            process_and_save_team(team, contests)
        else:
            fallback_teams.append(team)

    # Use Playwright for any remaining teams
    if fallback_teams:
        print(f"\nLaunching Playwright browser fallback for {len(fallback_teams)} teams...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=HEADERS["User-Agent"])
            page = context.new_page()

            for team in fallback_teams:
                print(f"Playwright scraping: {team['name']}...")
                games_list = []
                try:
                    page.goto(team["url"], wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(3000)
                    
                    next_el = page.query_selector("script#__NEXT_DATA__")
                    if next_el:
                        data = json.loads(next_el.inner_text())
                        contests = extract_contests_from_json(data)
                        process_and_save_team(team, contests)
                        continue

                    # DOM row fallback
                    rows = page.query_selector_all("tr, [class*='contest'], [data-testid*='contest']")
                    for row in rows:
                        txt = row.inner_text().strip()
                        if txt and len(txt) > 6:
                            lines = [l.strip() for l in txt.split("\n") if l.strip()]
                            parsed = parse_game_block(lines)
                            if parsed and parsed["date"]:
                                games_list.append(parsed)

                    process_and_save_team(team, games_list)
                except Exception as e:
                    print(f"  [ERROR] Playwright error for {team['name']}: {e}")

            browser.close()

    print("\nScraper complete!")

if __name__ == "__main__":
    main()
