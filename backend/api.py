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
