"""
Data ingestion for World Cup 2026 Match Predictor.
Pulls real match data from multiple sources:
  1. API-Football (primary, requires key)
  2. football-data.org (free tier, requires key)
  3. Open international results dataset (no key needed)
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
FOOTBALLDATA_KEY = os.getenv("FOOTBALLDATA_KEY", "")
FOOTBALLDATA_BASE = "https://api.football-data.org/v4"

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


# ---- football-data.org integration ----

# football-data.org competition codes for international matches
FOOTBALLDATA_COMPETITIONS = [
    ("WC", 2018, "World Cup 2018"),
    ("WC", 2022, "World Cup 2022"),
    ("EC", 2020, "Euro 2020"),
    ("EC", 2024, "Euro 2024"),
    ("CLI", 2024, "Copa Libertadores/Intl 2024"),
]


def footballdata_fetch(endpoint: str) -> dict:
    """Fetch from football-data.org with rate limiting."""
    headers = {"X-Auth-Token": FOOTBALLDATA_KEY} if FOOTBALLDATA_KEY else {}
    url = f"{FOOTBALLDATA_BASE}/{endpoint}"
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 429:
        print("  football-data.org rate limited, waiting 60s...")
        time.sleep(60)
        resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


# football-data.org team name normalization
FOOTBALLDATA_TEAM_MAP = {
    "Korea Republic": "South Korea",
    "Türkiye": "Turkey",
    "IR Iran": "Iran",
    "Côte d'Ivoire": "Ivory Coast",
    "Czechia": "Czech Republic",
    "Bosnia-Herzegovina": "Bosnia",
    "Trinidad & Tobago": "Trinidad and Tobago",
}


def fetch_footballdata_matches(competition: str, season: int, description: str) -> list:
    """Fetch matches from football-data.org for a competition/season."""
    cache_file = RAW_DIR / f"footballdata_{competition}_{season}.json"

    if cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < 24:
            print(f"  Using cached football-data.org data for {description}")
            with open(cache_file) as f:
                return json.load(f)

    print(f"  Fetching from football-data.org: {description}")
    try:
        data = footballdata_fetch(f"competitions/{competition}/matches?season={season}&status=FINISHED")
        matches_raw = data.get("matches", [])
        with open(cache_file, "w") as f:
            json.dump(matches_raw, f)
        time.sleep(6)  # free tier: 10 req/min
        return matches_raw
    except Exception as e:
        print(f"  ERROR fetching {description} from football-data.org: {e}")
        if cache_file.exists():
            with open(cache_file) as f:
                return json.load(f)
        return []


def parse_footballdata_matches(matches_raw: list) -> list:
    """Parse football-data.org matches into our standard format."""
    matches = []
    for m in matches_raw:
        if m.get("status") != "FINISHED":
            continue

        home_name = m.get("homeTeam", {}).get("name", "")
        away_name = m.get("awayTeam", {}).get("name", "")
        home_name = FOOTBALLDATA_TEAM_MAP.get(home_name, home_name)
        away_name = FOOTBALLDATA_TEAM_MAP.get(away_name, away_name)

        score = m.get("score", {})
        ft = score.get("fullTime", {})
        home_score = ft.get("home")
        away_score = ft.get("away")
        if home_score is None or away_score is None:
            continue

        # Determine venue: tournament matches are generally neutral
        competition = m.get("competition", {}).get("name", "")
        stage = m.get("stage", "")
        is_neutral = "GROUP" in stage or "FINAL" in stage or "ROUND" in stage

        date_str = m.get("utcDate", "")[:10]

        matches.append({
            "date": date_str,
            "home_team": home_name,
            "away_team": away_name,
            "home_score": int(home_score),
            "away_score": int(away_score),
            "tournament": competition,
            "neutral_venue": is_neutral,
        })

    return matches


# ---- Open international results (CSV from GitHub) ----

OPEN_RESULTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"


def fetch_open_results() -> list:
    """Fetch open international football results dataset.
    Source: github.com/martj42/international_results — public domain,
    covers 1872–present with 45k+ matches.
    We filter to 2018+ and WC2026 teams only.
    """
    cache_file = RAW_DIR / "open_international_results.csv"

    if cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 168  # refresh weekly
        if age_hours < 1:
            print("  Using cached open international results")
            return parse_open_results(cache_file)

    print("  Fetching open international results dataset...")
    try:
        resp = requests.get(OPEN_RESULTS_URL, timeout=60)
        resp.raise_for_status()
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(resp.text)
        return parse_open_results(cache_file)
    except Exception as e:
        print(f"  ERROR fetching open results: {e}")
        if cache_file.exists():
            return parse_open_results(cache_file)
        return []


# Team name normalization for the open results dataset
OPEN_RESULTS_TEAM_MAP = {
    "United States": "USA",
    "Korea Republic": "South Korea",
    "IR Iran": "Iran",
    "Côte d'Ivoire": "Ivory Coast",
    "Türkiye": "Turkey",
    "Czechia": "Czech Republic",
    "Czech Republic": "Czech Republic",
    "Bosnia and Herzegovina": "Bosnia",
    "Trinidad and Tobago": "Trinidad and Tobago",
    "Korea DPR": "North Korea",
    "Chinese Taipei": "Taiwan",
    "Eswatini": "Swaziland",
}


def parse_open_results(csv_path: Path) -> list:
    """Parse the open international results CSV (2018+ only)."""
    import pandas as pd
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"  ERROR parsing open results CSV: {e}")
        return []

    # Filter to 2018+
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"] >= "2018-01-01"].copy()

    matches = []
    for _, row in df.iterrows():
        home = OPEN_RESULTS_TEAM_MAP.get(row["home_team"], row["home_team"])
        away = OPEN_RESULTS_TEAM_MAP.get(row["away_team"], row["away_team"])
        try:
            home_score = int(row["home_score"])
            away_score = int(row["away_score"])
        except (ValueError, TypeError):
            continue

        tournament = str(row.get("tournament", "Unknown"))
        is_neutral = row.get("neutral", False)
        if isinstance(is_neutral, str):
            is_neutral = is_neutral.lower() == "true"

        matches.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "home_team": home,
            "away_team": away,
            "home_score": home_score,
            "away_score": away_score,
            "tournament": tournament,
            "neutral_venue": bool(is_neutral),
        })

    return matches


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
    sources_used = []

    # ---- Source 1: API-Football (primary, requires key) ----
    if API_KEY:
        print("=" * 50)
        print("SOURCE 1: API-FOOTBALL")
        print("=" * 50)

        # Fetch rankings for Elo
        print("\n  Fetching FIFA rankings...")
        rankings = fetch_team_rankings()
        if rankings:
            api_elo = rankings_to_elo(rankings)
            for team in WC2026_TEAMS:
                if team in api_elo:
                    elo_map[team] = api_elo[team]
            print(f"  Updated Elo for {len(api_elo)} teams from FIFA rankings")

        print(f"\n  Fetching match data from {len(COMPETITIONS)} competitions...")
        api_count = 0
        for league_id, season, desc in COMPETITIONS:
            fixtures = fetch_fixtures(league_id, season, desc)
            parsed = parse_fixtures(fixtures)
            all_matches.extend(parsed)
            api_count += len(parsed)
            print(f"  {desc}: {len(parsed)} finished matches")

        print(f"  API-Football total: {api_count} matches")
        sources_used.append(f"API-Football ({api_count} matches)")
    else:
        print("No API_FOOTBALL_KEY — skipping API-Football")

    # ---- Source 2: football-data.org (free tier) ----
    if FOOTBALLDATA_KEY:
        print("\n" + "=" * 50)
        print("SOURCE 2: FOOTBALL-DATA.ORG")
        print("=" * 50)

        fd_count = 0
        for comp, season, desc in FOOTBALLDATA_COMPETITIONS:
            raw = fetch_footballdata_matches(comp, season, desc)
            parsed = parse_footballdata_matches(raw)
            all_matches.extend(parsed)
            fd_count += len(parsed)
            print(f"  {desc}: {len(parsed)} matches")

        print(f"  football-data.org total: {fd_count} matches")
        sources_used.append(f"football-data.org ({fd_count} matches)")
    else:
        print("\nNo FOOTBALLDATA_KEY — skipping football-data.org")

    # ---- Source 3: Open international results (always available, no key) ----
    print("\n" + "=" * 50)
    print("SOURCE 3: OPEN INTERNATIONAL RESULTS")
    print("=" * 50)

    open_matches = fetch_open_results()
    if open_matches:
        all_matches.extend(open_matches)
        print(f"  Open results: {len(open_matches)} matches (2018+)")
        sources_used.append(f"Open results ({len(open_matches)} matches)")
    else:
        print("  Could not fetch open results dataset")

    # ---- Fallback: hardcoded data if nothing else worked ----
    if not all_matches:
        print("\nNo API data available — using fallback hardcoded data")
        for date, home, away, hs, aws, tourn, neutral in FALLBACK_MATCHES:
            all_matches.append({
                "date": date, "home_team": home, "away_team": away,
                "home_score": hs, "away_score": aws,
                "tournament": tourn, "neutral_venue": neutral,
            })
        sources_used.append(f"Fallback ({len(FALLBACK_MATCHES)} matches)")

    print(f"\nData sources used: {', '.join(sources_used)}")
    print(f"Total raw matches (pre-dedup): {len(all_matches)}")

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
