"""
Data ingestion for World Cup 2026 Match Predictor.
Pulls real match data from API-Football, with hardcoded fallback.
"""

import csv
import json
import os
import time
from pathlib import Path
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
API_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_BASE = "https://v3.football.api-sports.io"

# Team name normalization (API-Football names → our standard names)
TEAM_NAME_MAP = {
    "USA": "USA", "United States": "USA",
    "Korea Republic": "South Korea", "South Korea": "South Korea",
    "Korea DPR": "North Korea",
    "IR Iran": "Iran", "Iran": "Iran",
    "Saudi Arabia": "Saudi Arabia",
    "Costa Rica": "Costa Rica",
    "New Zealand": "New Zealand",
    "South Africa": "South Africa",
    "Côte D'Ivoire": "Ivory Coast", "Cote D'Ivoire": "Ivory Coast",
    "Czechia": "Czech Republic", "Czech Republic": "Czech Republic",
    "Türkiye": "Turkey", "Turkey": "Turkey",
    "Bosnia and Herzegovina": "Bosnia",
    "North Macedonia": "North Macedonia",
    "Trinidad And Tobago": "Trinidad and Tobago",
}

# FIFA 3-letter codes
TEAM_IDS = {
    "Argentina": "ARG", "France": "FRA", "Brazil": "BRA", "England": "ENG",
    "Spain": "ESP", "Germany": "GER", "Portugal": "POR", "Netherlands": "NED",
    "Belgium": "BEL", "Italy": "ITA", "Croatia": "CRO", "Colombia": "COL",
    "Uruguay": "URU", "Morocco": "MAR", "Japan": "JPN", "USA": "USA",
    "Mexico": "MEX", "Switzerland": "SUI", "Denmark": "DEN", "Austria": "AUT",
    "Senegal": "SEN", "South Korea": "KOR", "Australia": "AUS", "Turkey": "TUR",
    "Serbia": "SRB", "Nigeria": "NGA", "Iran": "IRN", "Ecuador": "ECU",
    "Scotland": "SCO", "Canada": "CAN", "Cameroon": "CMR", "Tunisia": "TUN",
    "Peru": "PER", "Chile": "CHI", "Paraguay": "PAR", "Mali": "MLI",
    "Egypt": "EGY", "Panama": "PAN", "Costa Rica": "CRC", "Slovenia": "SVN",
    "Albania": "ALB", "Saudi Arabia": "KSA", "Jamaica": "JAM", "South Africa": "RSA",
    "Venezuela": "VEN", "Bolivia": "BOL", "Honduras": "HON", "Qatar": "QAT",
    "Uzbekistan": "UZB", "Iraq": "IRQ", "New Zealand": "NZL", "Indonesia": "IDN",
}

# WC2026 participating nations
WC2026_TEAMS = set(TEAM_IDS.keys())

# API-Football league IDs and seasons to fetch
COMPETITIONS = [
    # (league_id, season, description)
    (1, 2018, "World Cup 2018"),
    (1, 2022, "World Cup 2022"),
    (1, 2026, "World Cup 2026"),
    (4, 2020, "Euro 2020"),
    (4, 2024, "Euro 2024"),
    (9, 2019, "Copa America 2019"),
    (9, 2021, "Copa America 2021"),
    (9, 2024, "Copa America 2024"),
    (6, 2023, "AFCON 2023"),
    (6, 2024, "AFCON 2024"),
    (29, 2023, "WCQ South America 2026"),
    (32, 2023, "WCQ CONCACAF 2026"),
    (5, 2024, "UEFA Nations League 2024-25"),
    (5, 2022, "UEFA Nations League 2022-23"),
    (30, 2023, "WCQ Africa 2026"),
    (31, 2023, "WCQ Asia 2026"),
    (15, 2023, "AFC Asian Cup 2023"),
    (22, 2023, "CONCACAF Gold Cup 2023"),
    (10, 2024, "Friendlies 2024"),
    (10, 2023, "Friendlies 2023"),
]


def normalize_team_name(name: str) -> str:
    return TEAM_NAME_MAP.get(name, name)


def get_team_id(name: str) -> str:
    return TEAM_IDS.get(name, name[:3].upper())


def api_fetch(endpoint: str, params: dict) -> dict:
    """Fetch from API-Football with rate limiting."""
    headers = {"x-apisports-key": API_KEY}
    url = f"{API_BASE}/{endpoint}"
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("errors"):
        print(f"  API errors: {data['errors']}")
    return data


def fetch_fixtures(league_id: int, season: int, description: str) -> list:
    """Fetch fixtures for a competition, with JSON caching."""
    cache_file = RAW_DIR / f"fixtures_{league_id}_{season}.json"

    # Use cache if less than 24 hours old
    if cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < 24:
            print(f"  Using cached data for {description}")
            with open(cache_file) as f:
                return json.load(f)

    print(f"  Fetching from API: {description} (league={league_id}, season={season})")
    try:
        data = api_fetch("fixtures", {"league": league_id, "season": season})
        fixtures = data.get("response", [])
        # Cache the response
        with open(cache_file, "w") as f:
            json.dump(fixtures, f)
        # Rate limit: API-Football free tier
        time.sleep(6.5)  # ~10 req/min safe margin
        return fixtures
    except Exception as e:
        print(f"  ERROR fetching {description}: {e}")
        # Return cached data if available even if stale
        if cache_file.exists():
            print(f"  Falling back to stale cache")
            with open(cache_file) as f:
                return json.load(f)
        return []


def parse_fixtures(fixtures: list) -> list:
    """Parse API-Football fixtures into match records."""
    matches = []
    for fix in fixtures:
        fixture = fix.get("fixture", {})
        teams = fix.get("teams", {})
        goals = fix.get("goals", {})
        league = fix.get("league", {})

        # Skip matches that haven't been played yet
        status = fixture.get("status", {}).get("short", "")
        if status not in ("FT", "AET", "PEN"):
            continue

        home_name = normalize_team_name(teams.get("home", {}).get("name", ""))
        away_name = normalize_team_name(teams.get("away", {}).get("name", ""))
        home_score = goals.get("home")
        away_score = goals.get("away")

        if home_score is None or away_score is None:
            continue

        # Determine venue neutrality
        venue = fixture.get("venue", {})
        # International tournaments are mostly neutral except host nation
        tournament = league.get("name", "")
        is_neutral = True
        # Home qualifiers/friendlies are not neutral
        if "qualification" in tournament.lower() or "friendl" in tournament.lower():
            is_neutral = False
        if "nations league" in tournament.lower():
            is_neutral = False

        date_str = fixture.get("date", "")[:10]  # YYYY-MM-DD

        matches.append({
            "date": date_str,
            "home_team": home_name,
            "away_team": away_name,
            "home_score": int(home_score),
            "away_score": int(away_score),
            "tournament": league.get("name", "Unknown"),
            "neutral_venue": is_neutral,
        })

    return matches


def fetch_team_rankings() -> dict:
    """Fetch FIFA rankings from API-Football to use as Elo proxy."""
    cache_file = RAW_DIR / "rankings.json"

    if cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < 24:
            print("  Using cached rankings")
            with open(cache_file) as f:
                return json.load(f)

    print("  Fetching FIFA rankings from API...")
    try:
        data = api_fetch("rankings", {})
        rankings = data.get("response", [])
        with open(cache_file, "w") as f:
            json.dump(rankings, f)
        time.sleep(6.5)
        return rankings
    except Exception as e:
        print(f"  ERROR fetching rankings: {e}")
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        return []


def rankings_to_elo(rankings: list) -> dict:
    """Convert FIFA rankings to approximate Elo ratings.
    FIFA ranking points roughly map to Elo with an offset."""
    elo_map = {}
    for entry in rankings:
        team_name = normalize_team_name(entry.get("team", {}).get("name", ""))
        rank = entry.get("rank", 100)
        points = entry.get("points", 1000)
        # Convert FIFA points to Elo-like scale (FIFA points are ~1000-1800 range)
        # Elo is ~1400-2100 range. Simple linear mapping.
        elo = int(points * 1.15 + 200)
        elo = max(1500, min(2150, elo))
        elo_map[team_name] = elo
    return elo_map


# ---- Fallback hardcoded data (used when API is unavailable) ----

FALLBACK_ELO = {
    "Argentina": 2080, "France": 2045, "Brazil": 2050, "England": 2035,
    "Spain": 2040, "Germany": 2010, "Portugal": 2025, "Netherlands": 2015,
    "Belgium": 1990, "Italy": 1985, "Croatia": 1980, "Colombia": 1975,
    "Uruguay": 1970, "Morocco": 1965, "Japan": 1960, "USA": 1955,
    "Mexico": 1950, "Switzerland": 1945, "Denmark": 1940, "Austria": 1930,
    "Senegal": 1925, "South Korea": 1920, "Australia": 1910, "Turkey": 1905,
    "Serbia": 1900, "Nigeria": 1895, "Iran": 1890, "Ecuador": 1885,
    "Scotland": 1875, "Canada": 1870, "Cameroon": 1865, "Tunisia": 1860,
    "Peru": 1855, "Chile": 1850, "Paraguay": 1845, "Mali": 1840,
    "Egypt": 1835, "Panama": 1830, "Costa Rica": 1825, "Slovenia": 1820,
    "Albania": 1815, "Saudi Arabia": 1810, "Jamaica": 1800, "South Africa": 1795,
    "Venezuela": 1790, "Bolivia": 1785, "Honduras": 1780, "Qatar": 1775,
    "Uzbekistan": 1770, "Iraq": 1765, "New Zealand": 1720, "Indonesia": 1700,
}

FALLBACK_MATCHES = [
    # 2018 World Cup
    ("2018-06-14", "Russia", "Saudi Arabia", 5, 0, "World Cup 2018", False),
    ("2018-06-15", "Egypt", "Uruguay", 0, 1, "World Cup 2018", True),
    ("2018-06-15", "Morocco", "Iran", 0, 1, "World Cup 2018", True),
    ("2018-06-15", "Portugal", "Spain", 3, 3, "World Cup 2018", True),
    ("2018-06-16", "France", "Australia", 2, 1, "World Cup 2018", True),
    ("2018-06-16", "Argentina", "Iceland", 1, 1, "World Cup 2018", True),
    ("2018-06-17", "Germany", "Mexico", 0, 1, "World Cup 2018", True),
    ("2018-06-17", "Brazil", "Switzerland", 1, 1, "World Cup 2018", True),
    ("2018-06-18", "Belgium", "Panama", 3, 0, "World Cup 2018", True),
    ("2018-06-18", "Tunisia", "England", 1, 2, "World Cup 2018", True),
    ("2018-06-19", "Colombia", "Japan", 1, 2, "World Cup 2018", True),
    ("2018-06-21", "France", "Peru", 1, 0, "World Cup 2018", True),
    ("2018-06-21", "Argentina", "Croatia", 0, 3, "World Cup 2018", True),
    ("2018-06-22", "Brazil", "Costa Rica", 2, 0, "World Cup 2018", True),
    ("2018-06-23", "Belgium", "Tunisia", 5, 2, "World Cup 2018", True),
    ("2018-06-24", "England", "Panama", 6, 1, "World Cup 2018", True),
    ("2018-06-27", "South Korea", "Germany", 2, 0, "World Cup 2018", True),
    ("2018-06-30", "France", "Argentina", 4, 3, "World Cup 2018", True),
    ("2018-07-02", "Brazil", "Mexico", 2, 0, "World Cup 2018", True),
    ("2018-07-06", "France", "Uruguay", 2, 0, "World Cup 2018", True),
    ("2018-07-06", "Brazil", "Belgium", 1, 2, "World Cup 2018", True),
    ("2018-07-10", "France", "Belgium", 1, 0, "World Cup 2018", True),
    ("2018-07-15", "France", "Croatia", 4, 2, "World Cup 2018", True),
    # 2022 World Cup (select)
    ("2022-11-22", "Argentina", "Saudi Arabia", 1, 2, "World Cup 2022", True),
    ("2022-11-22", "France", "Australia", 4, 1, "World Cup 2022", True),
    ("2022-11-23", "Germany", "Japan", 1, 2, "World Cup 2022", True),
    ("2022-11-23", "Spain", "Costa Rica", 7, 0, "World Cup 2022", True),
    ("2022-11-24", "Brazil", "Serbia", 2, 0, "World Cup 2022", True),
    ("2022-11-26", "Argentina", "Mexico", 2, 0, "World Cup 2022", True),
    ("2022-11-26", "France", "Denmark", 2, 1, "World Cup 2022", True),
    ("2022-11-27", "Belgium", "Morocco", 0, 2, "World Cup 2022", True),
    ("2022-11-27", "Spain", "Germany", 1, 1, "World Cup 2022", True),
    ("2022-12-01", "Japan", "Spain", 2, 1, "World Cup 2022", True),
    ("2022-12-03", "Netherlands", "USA", 3, 1, "World Cup 2022", True),
    ("2022-12-05", "Brazil", "South Korea", 4, 1, "World Cup 2022", True),
    ("2022-12-09", "Croatia", "Brazil", 1, 1, "World Cup 2022", True),
    ("2022-12-10", "Morocco", "Portugal", 1, 0, "World Cup 2022", True),
    ("2022-12-10", "England", "France", 1, 2, "World Cup 2022", True),
    ("2022-12-13", "Argentina", "Croatia", 3, 0, "World Cup 2022", True),
    ("2022-12-18", "Argentina", "France", 3, 3, "World Cup 2022", True),
]


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_matches = []
    elo_map = dict(FALLBACK_ELO)  # Start with fallback

    if API_KEY:
        print("=" * 50)
        print("FETCHING LIVE DATA FROM API-FOOTBALL")
        print("=" * 50)

        # Fetch rankings for Elo
        print("\n[1/2] Fetching FIFA rankings...")
        rankings = fetch_team_rankings()
        if rankings:
            api_elo = rankings_to_elo(rankings)
            # Merge with fallback (API data takes priority)
            for team in WC2026_TEAMS:
                if team in api_elo:
                    elo_map[team] = api_elo[team]
            print(f"  Updated Elo for {len(api_elo)} teams from FIFA rankings")

        # Fetch match fixtures
        print(f"\n[2/2] Fetching match data from {len(COMPETITIONS)} competitions...")
        for league_id, season, desc in COMPETITIONS:
            fixtures = fetch_fixtures(league_id, season, desc)
            parsed = parse_fixtures(fixtures)
            all_matches.extend(parsed)
            print(f"  {desc}: {len(parsed)} finished matches")

        print(f"\nTotal matches from API: {len(all_matches)}")
    else:
        print("No API_FOOTBALL_KEY found — using fallback hardcoded data")
        for date, home, away, hs, aws, tourn, neutral in FALLBACK_MATCHES:
            all_matches.append({
                "date": date, "home_team": home, "away_team": away,
                "home_score": hs, "away_score": aws,
                "tournament": tourn, "neutral_venue": neutral,
            })

    # Filter to matches involving WC2026 teams, deduplicate
    seen = set()
    filtered = []
    for m in all_matches:
        home = m["home_team"]
        away = m["away_team"]
        if home not in WC2026_TEAMS and away not in WC2026_TEAMS:
            continue
        key = (m["date"], home, away)
        if key in seen:
            continue
        seen.add(key)
        filtered.append(m)

    # Sort by date
    filtered.sort(key=lambda x: x["date"])

    # Save Elo ratings
    elo_path = DATA_DIR / "elo_ratings.csv"
    with open(elo_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["team", "team_id", "elo_rating"])
        for team in sorted(elo_map.keys()):
            if team in WC2026_TEAMS:
                writer.writerow([team, get_team_id(team), elo_map[team]])
    print(f"\nSaved Elo ratings for {sum(1 for t in elo_map if t in WC2026_TEAMS)} WC2026 teams to {elo_path}")

    # Save matches
    matches_path = DATA_DIR / "matches.csv"
    with open(matches_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "home_team", "away_team", "home_score", "away_score",
                          "tournament", "neutral_venue"])
        for m in filtered:
            writer.writerow([
                m["date"], m["home_team"], m["away_team"],
                m["home_score"], m["away_score"],
                m["tournament"], m["neutral_venue"],
            ])
    print(f"Saved {len(filtered)} matches to {matches_path}")


if __name__ == "__main__":
    main()
