import json
import re
import datetime
import os
from playwright.sync_api import sync_playwright

# List of all 12 teams for Ogden High School and Ben Lomond High School
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


def parse_game_block(lines):
    """Fallback text parser if JSON extraction fails for a row."""
    if not lines:
        return None

    raw_str = " | ".join(lines)
    date_str = ""
    time_str = ""
    opponent_str = ""
    result_str = ""
    location_str = "Home"
    is_home = True
    is_away = False
    is_region = False

    for line in lines:
        l_lower = line.lower()

        # Date matching
        if not date_str and (re.search(r'\b(\d{1,2}/\d{1,2})\b', line) or any(
                m in l_lower for m in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])):
            date_match = re.search(r'(\d{1,2}/\d{1,2}(?:/\d{2,4})?)', line)
            date_str = date_match.group(1) if date_match else line

        # Time matching
        if re.search(r'\d{1,2}:\d{2}\s*(?:am|pm)?', l_lower):
            time_match = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm)?)', l_lower)
            if time_match:
                time_str = time_match.group(1).upper()

        # Opponent & Location matching
        if '@' in line or 'vs' in l_lower or 'against' in l_lower or 'at ' in l_lower:
            opponent_str = line
            if '@' in line or 'at ' in l_lower:
                location_str = "Away"
                is_home = False
                is_away = True
            elif 'vs' in l_lower:
                location_str = "Home"
                is_home = True
                is_away = False

        # Region / Conference indicator
        if '*' in line or 'league' in l_lower or 'region' in l_lower or 'conference' in l_lower:
            is_region = True

        # Score / Result
        if re.search(r'\b[WLT]\b|\b\d+-\d+\b', line):
            result_str = line

    if not date_str and len(lines) > 0:
        date_str = lines[0]
    if not opponent_str and len(lines) > 1:
        opponent_str = lines[1]

    opp_clean = re.sub(r'^(vs\.?|@|at)\s*', '', opponent_str, flags=re.IGNORECASE).replace('*', '').strip()

    return {
        "date": date_str,
        "time": time_str,
        "date_time": f"{date_str} {time_str}".strip(),
        "opponent": opponent_str if opponent_str else opp_clean,
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
        "raw": raw_str,
        "details": lines
    }


def scrape_team_schedule(page, team):
    print(f"Scraping schedule for {team['name']}...")
    games = []

    try:
        page.goto(team["url"], wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # Method 1: Extract direct schedule payload embedded in MaxPreps Next.js data tag
        next_data_el = page.query_selector("script#__NEXT_DATA__")
        if next_data_el:
            try:
                raw_json = json.loads(next_data_el.inner_text())

                def find_contests(obj):
                    if isinstance(obj, dict):
                        for k in ["contests", "scheduleEntries", "games", "contestList"]:
                            if k in obj and isinstance(obj[k], list) and len(obj[k]) > 0:
                                return obj[k]
                        for v in obj.values():
                            res = find_contests(v)
                            if res:
                                return res
                    elif isinstance(obj, list):
                        for item in obj:
                            res = find_contests(item)
                            if res:
                                return res
                    return []

                raw_contests = find_contests(raw_json)
                for contest in raw_contests:
                    if isinstance(contest, dict):
                        date_val = contest.get("date", contest.get("dateString", ""))
                        opp_data = contest.get("opponent", {})
                        opp_name = opp_data.get("name", "Opponent") if isinstance(opp_data, dict) else str(opp_data)
                        res_data = contest.get("result", {})
                        res_text = res_data.get("text", res_data.get("score", "")) if isinstance(res_data, dict) else str(res_data)

                        is_away = contest.get("isAway", False) or (isinstance(opp_data, dict) and opp_data.get("isHome", False))
                        is_home = not is_away
                        loc = "Away" if is_away else "Home"
                        is_reg = contest.get("isConference", contest.get("isLeague", False))

                        games.append({
                            "date": str(date_val),
                            "time": str(contest.get("time", "")),
                            "date_time": f"{date_val} {contest.get('time', '')}".strip(),
                            "opponent": f"{'@' if is_away else 'vs'} {opp_name}",
                            "opponent_name": opp_name,
                            "opponentName": opp_name,
                            "location": loc,
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
            except Exception as e_json:
                print(f"  [INFO] Next.js parsing skipped: {e_json}")

        # Method 2: DOM row scraping fallback if Next.js data wasn't found
        if not games:
            rows = page.query_selector_all("tr, [class*='contest'], [class*='Contest'], [data-testid*='contest']")
            for row in rows:
                txt = row.inner_text().strip()
                if txt and len(txt) > 6:
                    lines = [line.strip() for line in txt.split("\n") if line.strip()]
                    parsed = parse_game_block(lines)
                    if parsed and parsed["date"]:
                        games.append(parsed)

    except Exception as e:
        print(f"  [ERROR] Scraping failed for {team['name']}: {e}")

    # Compute metrics summary
    wins = 0
    losses = 0
    ties = 0
    home_count = 0
    away_count = 0
    region_count = 0

    for g in games:
        res_u = g["result"].upper()
        if "W" in res_u:
            wins += 1
        elif "L" in res_u:
            losses += 1
        elif "T" in res_u:
            ties += 1

        if g.get("is_home"):
            home_count += 1
        if g.get("is_away"):
            away_count += 1
        if g.get("is_region"):
            region_count += 1

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
        "home": home_count,
        "home_matches": home_count,
        "homeMatches": home_count,
        "away": away_count,
        "away_matches": away_count,
        "awayMatches": away_count,
        "region": region_count,
        "region_matches": region_count,
        "regionMatches": region_count
    }

    # Combined payload format to support any website widget variation
    payload = {
        "team": team["name"],
        "source_url": team["url"],
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall_record": rec_str,
        "record": rec_str,
        "total_matches": total_games,
        "totalMatches": total_games,
        "home_matches": home_count,
        "homeMatches": home_count,
        "away_matches": away_count,
        "awayMatches": away_count,
        "region_matches": region_count,
        "regionMatches": region_count,
        "metrics": metrics_obj,
        "game_metrics": metrics_obj,
        "games": games,
        "schedule": games
    }

    # Save to JSON file
    with open(team["output"], "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"  [SUCCESS] Saved {total_games} games -> {team['output']}")


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
