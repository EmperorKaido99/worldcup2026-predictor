"""
FastAPI backend for World Cup 2026 Predictor.
"""

import os
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="World Cup 2026 Predictor API", version="1.0.0")

# CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
MODELS_DIR = Path(__file__).parent / "models"
DATA_DIR = Path(__file__).parent / "data" / "processed"

# Lazy-loaded globals
_model_artifacts = None
_elo_map = None
_dynamic_elo = None
_teams_list = None
_matches_df = None


def _load_model():
    global _model_artifacts
    if _model_artifacts is not None:
        return _model_artifacts
    model_path = MODELS_DIR / "match_model.joblib"
    if not model_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Model not trained yet. Run: cd backend && python -m src.train_match",
        )
    _model_artifacts = joblib.load(model_path)
    return _model_artifacts


def _load_teams():
    global _elo_map, _teams_list
    if _teams_list is not None:
        return _teams_list, _elo_map

    elo_path = DATA_DIR / "elo_ratings.csv"
    if not elo_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Data not ingested yet. Run: cd backend && python -m src.ingest",
        )
    elo_df = pd.read_csv(elo_path)
    _elo_map = dict(zip(elo_df["team"], elo_df["elo_rating"]))
    _teams_list = [
        {"id": row["team_id"], "name": row["team"]}
        for _, row in elo_df.sort_values("team").iterrows()
    ]
    return _teams_list, _elo_map


def _load_matches():
    global _matches_df, _dynamic_elo
    if _matches_df is not None:
        return _matches_df
    matches_path = DATA_DIR / "matches.csv"
    if matches_path.exists():
        _matches_df = pd.read_csv(matches_path, parse_dates=["date"],
                                   encoding="utf-8-sig", encoding_errors="replace")
        # Compute dynamic Elo from match history
        from src.features import get_current_elo
        _, elo_map = _load_teams()
        elo_df = pd.read_csv(DATA_DIR / "elo_ratings.csv")
        _dynamic_elo = get_current_elo(_matches_df, elo_df)
    else:
        _matches_df = pd.DataFrame()
    return _matches_df


def _get_form_string(team: str, n: int = 5) -> str:
    matches = _load_matches()
    if matches.empty:
        return "-----"

    team_matches = matches[
        (matches["home_team"] == team) | (matches["away_team"] == team)
    ].sort_values("date").tail(n)

    form = []
    for _, m in team_matches.iterrows():
        if m["home_team"] == team:
            if m["home_score"] > m["away_score"]:
                form.append("W")
            elif m["home_score"] == m["away_score"]:
                form.append("D")
            else:
                form.append("L")
        else:
            if m["away_score"] > m["home_score"]:
                form.append("W")
            elif m["home_score"] == m["away_score"]:
                form.append("D")
            else:
                form.append("L")
    return "".join(form) if form else "-----"


HOST_NATIONS = {"USA", "Canada", "Mexico"}

# Cached live WC2026 results
_wc2026_live_cache = None
_wc2026_live_cache_time = 0

# Seed data: WC2026 results from before the API's rolling date window.
# These are real results that the free-tier API can no longer serve.
WC2026_SEED_RESULTS = [
    # June 11
    {"date": "2026-06-11", "home_team": "Mexico", "away_team": "South Africa", "home_score": 2, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-11", "home_team": "South Korea", "away_team": "Czech Republic", "home_score": 2, "away_score": 1, "tournament": "World Cup 2026"},
    # June 12
    {"date": "2026-06-12", "home_team": "USA", "away_team": "Paraguay", "home_score": 4, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-12", "home_team": "Canada", "away_team": "Bosnia", "home_score": 1, "away_score": 1, "tournament": "World Cup 2026"},
    # June 13
    {"date": "2026-06-13", "home_team": "Australia", "away_team": "Turkey", "home_score": 2, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-13", "home_team": "Brazil", "away_team": "Morocco", "home_score": 1, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-13", "home_team": "Scotland", "away_team": "Haiti", "home_score": 1, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-13", "home_team": "Switzerland", "away_team": "Qatar", "home_score": 1, "away_score": 1, "tournament": "World Cup 2026"},
    # June 14
    {"date": "2026-06-14", "home_team": "Germany", "away_team": "Curaçao", "home_score": 7, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-14", "home_team": "Ivory Coast", "away_team": "Ecuador", "home_score": 1, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-14", "home_team": "Netherlands", "away_team": "Japan", "home_score": 2, "away_score": 2, "tournament": "World Cup 2026"},
    {"date": "2026-06-14", "home_team": "Sweden", "away_team": "Tunisia", "home_score": 5, "away_score": 1, "tournament": "World Cup 2026"},
    # June 15
    {"date": "2026-06-15", "home_team": "Belgium", "away_team": "Egypt", "home_score": 1, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-15", "home_team": "Iran", "away_team": "New Zealand", "home_score": 2, "away_score": 2, "tournament": "World Cup 2026"},
    {"date": "2026-06-15", "home_team": "Spain", "away_team": "Cape Verde", "home_score": 0, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-15", "home_team": "Saudi Arabia", "away_team": "Uruguay", "home_score": 1, "away_score": 1, "tournament": "World Cup 2026"},
    # June 16
    {"date": "2026-06-16", "home_team": "France", "away_team": "Senegal", "home_score": 3, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-16", "home_team": "Argentina", "away_team": "Algeria", "home_score": 3, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-16", "home_team": "Norway", "away_team": "Iraq", "home_score": 4, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-16", "home_team": "Austria", "away_team": "Jordan", "home_score": 3, "away_score": 1, "tournament": "World Cup 2026"},
    # June 17
    {"date": "2026-06-17", "home_team": "Portugal", "away_team": "DR Congo", "home_score": 1, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-17", "home_team": "England", "away_team": "Croatia", "home_score": 4, "away_score": 2, "tournament": "World Cup 2026"},
    {"date": "2026-06-17", "home_team": "Ghana", "away_team": "Panama", "home_score": 1, "away_score": 0, "tournament": "World Cup 2026"},
    # June 19
    {"date": "2026-06-19", "home_team": "Mexico", "away_team": "South Korea", "home_score": 1, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-19", "home_team": "USA", "away_team": "Australia", "home_score": 2, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-19", "home_team": "Scotland", "away_team": "Morocco", "home_score": 0, "away_score": 1, "tournament": "World Cup 2026"},
    # June 20
    {"date": "2026-06-20", "home_team": "Brazil", "away_team": "Haiti", "home_score": 3, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-20", "home_team": "Turkey", "away_team": "Paraguay", "home_score": 0, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-20", "home_team": "Netherlands", "away_team": "Sweden", "home_score": 5, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-20", "home_team": "Germany", "away_team": "Ivory Coast", "home_score": 2, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-20", "home_team": "Ecuador", "away_team": "Curaçao", "home_score": 0, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-20", "home_team": "Japan", "away_team": "Tunisia", "home_score": 4, "away_score": 0, "tournament": "World Cup 2026"},
    # June 21
    {"date": "2026-06-21", "home_team": "Belgium", "away_team": "Iran", "home_score": 0, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-21", "home_team": "Egypt", "away_team": "New Zealand", "home_score": 3, "away_score": 1, "tournament": "World Cup 2026"},
    {"date": "2026-06-21", "home_team": "Spain", "away_team": "Saudi Arabia", "home_score": 4, "away_score": 0, "tournament": "World Cup 2026"},
    {"date": "2026-06-21", "home_team": "Uruguay", "away_team": "Cape Verde", "home_score": 2, "away_score": 2, "tournament": "World Cup 2026"},
]


class PredictMatchRequest(BaseModel):
    home: str
    away: str
    neutral: bool = True


# --- Endpoints ---


@app.get("/")
def health():
    return {"status": "ok", "service": "World Cup 2026 Predictor API"}


@app.get("/teams")
def get_teams():
    teams, _ = _load_teams()
    return {"teams": teams}


@app.post("/predict-match")
def predict_match(req: PredictMatchRequest):
    from src.features import rolling_stats, rolling_stats_short, head_to_head, \
        expected_score as elo_expected_score, get_tournament_weight

    teams, elo_map = _load_teams()
    artifacts = _load_model()

    # Resolve team names from IDs
    id_to_name = {t["id"]: t["name"] for t in teams}
    home_name = id_to_name.get(req.home)
    away_name = id_to_name.get(req.away)

    if not home_name:
        raise HTTPException(status_code=400, detail=f"Unknown team ID: {req.home}")
    if not away_name:
        raise HTTPException(status_code=400, detail=f"Unknown team ID: {req.away}")
    if req.home == req.away:
        raise HTTPException(status_code=400, detail="Home and away teams must differ")

    # Load matches and dynamic Elo
    matches = _load_matches()
    if _dynamic_elo:
        elo_home = round(_dynamic_elo.get(home_name, elo_map.get(home_name, 1700)))
        elo_away = round(_dynamic_elo.get(away_name, elo_map.get(away_name, 1700)))
    else:
        elo_home = elo_map.get(home_name, 1700)
        elo_away = elo_map.get(away_name, 1700)

    # Use the same rolling_stats from features.py for consistency
    # Use a future date so all matches are included
    future_date = pd.Timestamp("2099-01-01")
    home_stats_10 = rolling_stats(matches, home_name, future_date, n=10)
    away_stats_10 = rolling_stats(matches, away_name, future_date, n=10)
    home_stats_5 = rolling_stats_short(matches, home_name, future_date, n=5)
    away_stats_5 = rolling_stats_short(matches, away_name, future_date, n=5)
    h2h = head_to_head(matches, home_name, away_name, future_date)

    # Elo momentum
    from src.features import get_elo_momentum
    elo_df = pd.read_csv(DATA_DIR / "elo_ratings.csv")
    initial_elo = dict(zip(elo_df["team"], elo_df["elo_rating"]))
    from src.features import compute_dynamic_elo
    _, elo_history = compute_dynamic_elo(matches, initial_elo)
    elo_mom_home = round(get_elo_momentum(elo_history, home_name, future_date), 1)
    elo_mom_away = round(get_elo_momentum(elo_history, away_name, future_date), 1)

    neutral_flag = 1 if req.neutral else 0
    host_flag = 1 if (not req.neutral and home_name in HOST_NATIONS) else 0
    elo_exp = round(elo_expected_score(elo_home, elo_away), 3)

    # Build feature vector matching the training feature order exactly
    feature_vector = np.array([[
        elo_home,
        elo_away,
        elo_home - elo_away,
        elo_exp,
        elo_mom_home,
        elo_mom_away,
        home_stats_10["goals_scored_rate"],
        home_stats_10["goals_conceded_rate"],
        home_stats_10["points_rate"],
        home_stats_10["gd_rate"],
        away_stats_10["goals_scored_rate"],
        away_stats_10["goals_conceded_rate"],
        away_stats_10["points_rate"],
        away_stats_10["gd_rate"],
        home_stats_5["win_rate"],
        away_stats_5["win_rate"],
        home_stats_5["gd_rate"],
        away_stats_5["gd_rate"],
        home_stats_10["clean_sheet_rate"],
        away_stats_10["clean_sheet_rate"],
        neutral_flag,
        host_flag,
        home_stats_10["win_streak"],
        away_stats_10["win_streak"],
        home_stats_10["unbeaten_streak"],
        away_stats_10["unbeaten_streak"],
        home_stats_10["rest_days"],
        away_stats_10["rest_days"],
        h2h["h2h_wins"],
        h2h["h2h_gd"],
        1.0,  # tournament_weight (World Cup = 1.0)
    ]])

    scaler = artifacts["scaler"]
    model = artifacts["model"]

    X_scaled = scaler.transform(feature_vector)
    proba = model.predict_proba(X_scaled)[0]

    # Map class indices to labels
    classes = artifacts["classes"]
    prob_map = {}
    for i, cls in enumerate(classes):
        if cls == 0:
            prob_map["away_win"] = round(float(proba[i]), 3)
        elif cls == 1:
            prob_map["draw"] = round(float(proba[i]), 3)
        elif cls == 2:
            prob_map["home_win"] = round(float(proba[i]), 3)

    # Compute expected goals from team stats and Elo
    home_attack = home_stats_10["goals_scored_rate"]
    home_defense = home_stats_10["goals_conceded_rate"]
    away_attack = away_stats_10["goals_scored_rate"]
    away_defense = away_stats_10["goals_conceded_rate"]

    base_xg_home = (home_attack + away_defense) / 2.0
    base_xg_away = (away_attack + home_defense) / 2.0

    elo_factor = (elo_home - elo_away) / 800.0
    xg_home = max(0.3, base_xg_home + elo_factor * 0.5)
    xg_away = max(0.3, base_xg_away - elo_factor * 0.5)

    hw = prob_map.get("home_win", 0.33)
    aw = prob_map.get("away_win", 0.33)
    xg_home = xg_home * (1.0 + (hw - aw) * 0.3)
    xg_away = xg_away * (1.0 + (aw - hw) * 0.3)

    xg_home = round(max(0.3, min(3.5, xg_home)), 2)
    xg_away = round(max(0.2, min(3.0, xg_away)), 2)

    return {
        "home": req.home,
        "away": req.away,
        "neutral": req.neutral,
        "probabilities": prob_map,
        "expected_goals": {
            "home": xg_home,
            "away": xg_away,
        },
        "context": {
            "elo_home": elo_home,
            "elo_away": elo_away,
            "form_home": _get_form_string(home_name),
            "form_away": _get_form_string(away_name),
        },
    }


# --- Live WC2026 Results ---


def _fetch_wc2026_live_results() -> list:
    """Fetch completed WC2026 match results from all available APIs.
    Uses date-based fetching (works on free tier) + persistent cache file
    so results accumulate even beyond the API's rolling date window.
    In-memory cache refreshes every 5 minutes."""
    import time as _time
    import json as _json
    import requests as _requests
    from datetime import datetime, timedelta
    global _wc2026_live_cache, _wc2026_live_cache_time

    now = _time.time()
    if _wc2026_live_cache is not None and (now - _wc2026_live_cache_time) < 300:
        return _wc2026_live_cache

    from src.ingest import (
        API_KEY, normalize_team_name, TEAM_IDS,
    )

    # Load persistent cache of all WC2026 results we've seen
    cache_file = Path(__file__).parent / "data" / "raw" / "wc2026_live_results.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cached_matches = []
    if cache_file.exists():
        try:
            with open(cache_file) as f:
                cached_matches = _json.load(f)
        except Exception:
            cached_matches = []

    # Merge seed results (matches from before API window)
    seen = set()
    for m in cached_matches:
        seen.add((m["date"], m["home_team"], m["away_team"]))
    for m in WC2026_SEED_RESULTS:
        key = (m["date"], m["home_team"], m["away_team"])
        if key not in seen:
            seen.add(key)
            cached_matches.append(dict(m))

    new_matches_found = False

    # API-Football: fetch by date (free plan gives ~3-day rolling window)
    if API_KEY:
        today = datetime.utcnow().date()
        # Check today and previous 2 days (the rolling window)
        dates_to_check = [today - timedelta(days=i) for i in range(3)]
        for check_date in dates_to_check:
            date_str = check_date.strftime("%Y-%m-%d")
            try:
                resp = _requests.get(
                    "https://v3.football.api-sports.io/fixtures",
                    headers={"x-apisports-key": API_KEY},
                    params={"date": date_str},
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("errors"):
                    print(f"  API-Football date {date_str}: {data['errors']}")
                    continue

                for fix in data.get("response", []):
                    league = fix.get("league", {})
                    # Only World Cup matches (league_id=1)
                    if league.get("id") != 1:
                        continue

                    fixture = fix.get("fixture", {})
                    status = fixture.get("status", {}).get("short", "")
                    if status not in ("FT", "AET", "PEN"):
                        continue

                    teams = fix.get("teams", {})
                    goals = fix.get("goals", {})
                    home_name = normalize_team_name(
                        teams.get("home", {}).get("name", "")
                    )
                    away_name = normalize_team_name(
                        teams.get("away", {}).get("name", "")
                    )
                    home_score = goals.get("home")
                    away_score = goals.get("away")
                    if home_score is None or away_score is None:
                        continue

                    match_date = fixture.get("date", "")[:10]
                    key = (match_date, home_name, away_name)
                    if key not in seen:
                        seen.add(key)
                        cached_matches.append({
                            "date": match_date,
                            "home_team": home_name,
                            "away_team": away_name,
                            "home_score": int(home_score),
                            "away_score": int(away_score),
                            "tournament": "World Cup 2026",
                        })
                        new_matches_found = True
                        print(f"  New WC2026 result: {home_name} {home_score}-{away_score} {away_name}")

                _time.sleep(6.5)  # Rate limit
            except Exception as e:
                print(f"  API-Football date {date_str} error: {e}")

    # Save updated cache if new matches found
    if new_matches_found:
        try:
            with open(cache_file, "w") as f:
                _json.dump(cached_matches, f)
            print(f"  Saved {len(cached_matches)} total WC2026 results to cache")
        except Exception as e:
            print(f"  Error saving WC2026 cache: {e}")

    # Map team names to IDs
    name_to_id = {}
    for name, tid in TEAM_IDS.items():
        name_to_id[name] = tid

    results = []
    for m in cached_matches:
        home_id = name_to_id.get(m["home_team"], m["home_team"][:3].upper())
        away_id = name_to_id.get(m["away_team"], m["away_team"][:3].upper())
        results.append({
            "date": m["date"],
            "home_team": m["home_team"],
            "away_team": m["away_team"],
            "home_id": home_id,
            "away_id": away_id,
            "home_score": m["home_score"],
            "away_score": m["away_score"],
            "tournament": m.get("tournament", "World Cup 2026"),
        })

    results.sort(key=lambda x: x["date"])
    _wc2026_live_cache = results
    _wc2026_live_cache_time = now
    return results


@app.get("/wc2026/live-results")
def get_wc2026_live_results():
    """Get completed WC2026 match results from live APIs."""
    results = _fetch_wc2026_live_results()
    return {
        "matches": results,
        "count": len(results),
        "source": "live" if results else "none",
    }


@app.get("/wc2026/elimination-risk")
def get_elimination_risk():
    """Calculate elimination risk for each team based on current WC2026 results.
    A team is at risk if they cannot mathematically qualify or are unlikely to."""
    results = _fetch_wc2026_live_results()

    # WC2026 groups (must match frontend)
    groups_def = {
        "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
        "B": ["Canada", "Bosnia", "Qatar", "Switzerland"],
        "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
        "D": ["USA", "Paraguay", "Australia", "Turkey"],
        "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
        "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
        "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
        "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
        "I": ["France", "Senegal", "Iraq", "Norway"],
        "J": ["Argentina", "Algeria", "Austria", "Jordan"],
        "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
        "L": ["England", "Croatia", "Ghana", "Panama"],
    }

    from src.ingest import TEAM_IDS

    group_standings = {}
    for group_name, teams in groups_def.items():
        standings = {}
        for t in teams:
            tid = TEAM_IDS.get(t, t[:3].upper())
            standings[t] = {
                "team": t,
                "team_id": tid,
                "played": 0, "won": 0, "drawn": 0, "lost": 0,
                "gf": 0, "ga": 0, "gd": 0, "points": 0,
            }

        # Apply completed results to standings
        for m in results:
            home = m["home_team"]
            away = m["away_team"]
            if home in standings and away in standings:
                standings[home]["played"] += 1
                standings[away]["played"] += 1
                standings[home]["gf"] += m["home_score"]
                standings[home]["ga"] += m["away_score"]
                standings[away]["gf"] += m["away_score"]
                standings[away]["ga"] += m["home_score"]

                if m["home_score"] > m["away_score"]:
                    standings[home]["won"] += 1
                    standings[home]["points"] += 3
                    standings[away]["lost"] += 1
                elif m["home_score"] == m["away_score"]:
                    standings[home]["drawn"] += 1
                    standings[home]["points"] += 1
                    standings[away]["drawn"] += 1
                    standings[away]["points"] += 1
                else:
                    standings[away]["won"] += 1
                    standings[away]["points"] += 3
                    standings[home]["lost"] += 1

        for s in standings.values():
            s["gd"] = s["gf"] - s["ga"]

        # Sort by points, GD, GF
        sorted_standings = sorted(
            standings.values(),
            key=lambda x: (x["points"], x["gd"], x["gf"]),
            reverse=True,
        )

        # Calculate elimination risk
        # In WC2026: top 2 qualify, best 8 of 12 third-place teams also qualify
        # So 3rd place still has a realistic path (8/12 = 67% chance)
        max_remaining_points = lambda played: (3 - played) * 3
        # Second-place team's current points (to check if 3rd/4th can overtake)
        second_place_pts = sorted_standings[1]["points"] if len(sorted_standings) > 1 else 0

        for i, team in enumerate(sorted_standings):
            remaining = max_remaining_points(team["played"])
            max_possible = team["points"] + remaining

            # Risk levels
            if team["played"] == 0:
                risk = "not_started"
                risk_pct = 0
            elif remaining == 0:
                # All games played — position is final
                if i < 2:
                    risk = "safe"
                    risk_pct = 0
                elif i == 2:
                    # 3rd place: 8/12 best third-place teams qualify
                    risk = "contention" if team["points"] >= 3 else "at_risk"
                    risk_pct = 30 if team["points"] >= 3 else 60
                else:
                    risk = "eliminated"
                    risk_pct = 100
            elif max_possible < second_place_pts and i >= 3:
                # Can't even reach 2nd place — likely out (but 3rd still possible)
                if max_possible < sorted_standings[2]["points"] if len(sorted_standings) > 2 else 0:
                    risk = "eliminated"
                    risk_pct = 95
                else:
                    risk = "critical"
                    risk_pct = 85
            elif team["points"] == 0 and team["played"] >= 2:
                risk = "critical"
                risk_pct = 90
            elif team["points"] == 0 and team["played"] == 1:
                risk = "high"
                risk_pct = 60
            elif team["played"] >= 2 and team["points"] <= 1 and i >= 2:
                risk = "high"
                risk_pct = 70
            elif i < 2 and team["points"] >= 6:
                risk = "qualified"
                risk_pct = 0
            elif i < 2 and team["points"] >= 4:
                risk = "safe"
                risk_pct = 5
            elif i < 2:
                risk = "likely_safe"
                risk_pct = 15
            elif i == 2:
                risk = "contention"
                risk_pct = 40
            else:
                risk = "at_risk"
                risk_pct = 40 + (i * 10)

            team["position"] = i + 1
            team["risk"] = risk
            team["risk_pct"] = min(100, risk_pct)

        group_standings[group_name] = sorted_standings

    return {
        "groups": group_standings,
        "matches_played": len(results),
    }


# --- xG Endpoints (P1) ---


@app.get("/xg/teams-with-data")
def get_xg_teams():
    """Get list of team IDs that have xG shot data."""
    try:
        from src.viz import get_teams_with_data
        return {"teams": get_teams_with_data()}
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/xg/team/{team_id}")
def get_xg_stats(team_id: str):
    """Get xG summary stats for a team."""
    try:
        from src.viz import get_team_xg_stats
        return get_team_xg_stats(team_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/xg/team/{team_id}/shotmap")
def get_shot_map(team_id: str):
    """Get shot map PNG for a team."""
    try:
        from src.viz import generate_shot_map
        png_bytes = generate_shot_map(team_id)
        return Response(content=png_bytes, media_type="image/png")
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/xg/team/{team_id}/heatmap")
def get_heatmap(team_id: str):
    """Get shot heatmap PNG for a team."""
    try:
        from src.viz import generate_heatmap
        png_bytes = generate_heatmap(team_id)
        return Response(content=png_bytes, media_type="image/png")
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


# --- Penalty Endpoints (P2) ---

_penalty_artifacts = None
_penalty_team_stats = None


def _load_penalty_model():
    global _penalty_artifacts, _penalty_team_stats
    if _penalty_artifacts is not None:
        return _penalty_artifacts, _penalty_team_stats

    model_path = MODELS_DIR / "penalty_model.joblib"
    team_path = MODELS_DIR / "penalty_team_stats.joblib"
    if not model_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Penalty model not trained. Run: python -m src.train_penalty",
        )
    _penalty_artifacts = joblib.load(model_path)
    if team_path.exists():
        _penalty_team_stats = joblib.load(team_path)
    else:
        _penalty_team_stats = {}
    return _penalty_artifacts, _penalty_team_stats


@app.get("/penalties/stats")
def get_penalty_stats():
    """Get overall penalty zone statistics."""
    artifacts, _ = _load_penalty_model()
    return {
        "zone_stats": artifacts["zone_stats"],
        "total_penalties": artifacts["total_penalties"],
        "total_goals": artifacts["total_goals"],
        "conversion_rate": artifacts["conversion_rate"],
    }


@app.get("/penalties/team/{team_id}")
def get_team_penalty_stats(team_id: str):
    """Get penalty stats for a specific team."""
    _, team_stats = _load_penalty_model()

    # Resolve team name from ID
    teams, _ = _load_teams()
    id_to_name = {t["id"]: t["name"] for t in teams}
    team_name = id_to_name.get(team_id, team_id)

    # Try exact match, then partial
    stats = team_stats.get(team_name)
    if not stats:
        for name, s in team_stats.items():
            if team_name.lower() in name.lower() or name.lower() in team_name.lower():
                stats = s
                team_name = name
                break

    if not stats:
        return {
            "team": team_name,
            "zones": {str(i): {"total": 0, "goals": 0, "probability": 0} for i in range(9)},
            "total": 0,
            "goals": 0,
            "conversion": 0,
        }

    return {
        "team": team_name,
        "zones": stats["zones"],
        "total": stats["total"],
        "goals": stats["goals"],
        "conversion": stats["conversion"],
    }


class ShootoutRequest(BaseModel):
    team1: str
    team2: str
    rounds: int = 5
    simulations: int = 1000


@app.post("/penalties/simulate-shootout")
def simulate_shootout(req: ShootoutRequest):
    """Monte Carlo penalty shootout simulation between two teams."""
    import random

    artifacts, team_stats = _load_penalty_model()
    teams, _ = _load_teams()
    id_to_name = {t["id"]: t["name"] for t in teams}
    name1 = id_to_name.get(req.team1, req.team1)
    name2 = id_to_name.get(req.team2, req.team2)

    # Get team-specific conversion rates (or use overall)
    overall_conv = artifacts["conversion_rate"]

    def get_conv(team_name):
        for name, s in team_stats.items():
            if team_name.lower() in name.lower() or name.lower() in team_name.lower():
                return s["conversion"]
        return overall_conv

    conv1 = get_conv(name1)
    conv2 = get_conv(name2)

    # Run Monte Carlo simulations
    team1_wins = 0
    for _ in range(req.simulations):
        score1, score2 = 0, 0
        # Regular rounds
        for r in range(req.rounds):
            if random.random() < conv1:
                score1 += 1
            if random.random() < conv2:
                score2 += 1
        # Sudden death if tied
        while score1 == score2:
            if random.random() < conv1:
                score1 += 1
            if random.random() < conv2:
                score2 += 1
            if score1 == score2:
                continue
        if score1 > score2:
            team1_wins += 1

    team1_pct = round(team1_wins / req.simulations, 3)
    team2_pct = round(1.0 - team1_pct, 3)

    return {
        "team1": req.team1,
        "team2": req.team2,
        "team1_name": name1,
        "team2_name": name2,
        "team1_win_pct": team1_pct,
        "team2_win_pct": team2_pct,
        "team1_conversion": conv1,
        "team2_conversion": conv2,
        "simulations": req.simulations,
    }
