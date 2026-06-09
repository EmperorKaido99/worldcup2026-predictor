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
    global _matches_df
    if _matches_df is not None:
        return _matches_df
    matches_path = DATA_DIR / "matches.csv"
    if matches_path.exists():
        _matches_df = pd.read_csv(matches_path, parse_dates=["date"])
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

    elo_home = elo_map.get(home_name, 1700)
    elo_away = elo_map.get(away_name, 1700)

    # Compute rolling stats from historical data
    matches = _load_matches()

    def _rolling_rate(team, col_if_home, col_if_away, n=10):
        tm = matches[
            (matches["home_team"] == team) | (matches["away_team"] == team)
        ].sort_values("date").tail(n)
        vals = []
        for _, m in tm.iterrows():
            if m["home_team"] == team:
                vals.append(m[col_if_home])
            else:
                vals.append(m[col_if_away])
        return float(np.mean(vals)) if vals else 1.0

    def _points_rate(team, n=10):
        tm = matches[
            (matches["home_team"] == team) | (matches["away_team"] == team)
        ].sort_values("date").tail(n)
        pts = []
        for _, m in tm.iterrows():
            if m["home_team"] == team:
                if m["home_score"] > m["away_score"]:
                    pts.append(3)
                elif m["home_score"] == m["away_score"]:
                    pts.append(1)
                else:
                    pts.append(0)
            else:
                if m["away_score"] > m["home_score"]:
                    pts.append(3)
                elif m["home_score"] == m["away_score"]:
                    pts.append(1)
                else:
                    pts.append(0)
        return float(np.mean(pts)) if pts else 1.0

    neutral_flag = 1 if req.neutral else 0
    host_flag = 1 if (not req.neutral and home_name in HOST_NATIONS) else 0

    feature_vector = np.array([[
        elo_home,
        elo_away,
        elo_home - elo_away,
        _rolling_rate(home_name, "home_score", "away_score"),
        _rolling_rate(home_name, "away_score", "home_score"),
        _points_rate(home_name),
        _rolling_rate(away_name, "away_score", "home_score"),
        _rolling_rate(away_name, "home_score", "away_score"),
        _points_rate(away_name),
        neutral_flag,
        host_flag,
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

    return {
        "home": req.home,
        "away": req.away,
        "neutral": req.neutral,
        "probabilities": prob_map,
        "context": {
            "elo_home": elo_home,
            "elo_away": elo_away,
            "form_home": _get_form_string(home_name),
            "form_away": _get_form_string(away_name),
        },
    }
