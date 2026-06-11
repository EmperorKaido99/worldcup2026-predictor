"""
xG Model (P1) — Train an expected goals model using StatsBomb open data.

Pulls shot-level data from World Cup tournaments via statsbombpy,
engineers features (distance, angle, body part, play pattern),
and trains a gradient boosting classifier.

Usage:
    python -m src.train_xg
"""

import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from statsbombpy import sb

MODELS_DIR = Path(__file__).parent.parent / "models"
DATA_DIR = Path(__file__).parent.parent / "data" / "processed"

# StatsBomb competition IDs for international tournaments with open data
COMPETITIONS = [
    (43, 106),  # FIFA World Cup 2022
    (43, 3),    # FIFA World Cup 2018
    (43, 55),   # FIFA World Cup 1990
    (43, 54),   # FIFA World Cup 1986
    (72, 107),  # Women's World Cup 2023 (more shot data for training)
    (72, 30),   # Women's World Cup 2019
]

# Pitch dimensions in StatsBomb coordinate system
PITCH_LENGTH = 120.0
PITCH_WIDTH = 80.0
GOAL_CENTER_Y = 40.0
GOAL_WIDTH = 7.32  # metres, but StatsBomb uses yards so ~8 yards


def fetch_shots() -> pd.DataFrame:
    """Pull all shot events from StatsBomb open data competitions."""
    all_shots = []

    for comp_id, season_id in COMPETITIONS:
        print(f"Fetching matches for competition {comp_id}, season {season_id}...")
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception as e:
            print(f"  Skipping: {e}")
            continue

        print(f"  Found {len(matches)} matches")
        for _, match_row in matches.iterrows():
            match_id = match_row["match_id"]
            try:
                events = sb.events(match_id=match_id)
            except Exception:
                continue

            shots = events[events["type"] == "Shot"].copy()
            if shots.empty:
                continue

            shots["match_id"] = match_id
            shots["competition_id"] = comp_id
            shots["home_team_name"] = match_row.get("home_team", "")
            shots["away_team_name"] = match_row.get("away_team", "")
            all_shots.append(shots)

    if not all_shots:
        raise RuntimeError("No shot data found. Check StatsBomb API availability.")

    df = pd.concat(all_shots, ignore_index=True)
    print(f"\nTotal shots collected: {len(df)}")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer xG features from raw shot data."""
    records = []

    for _, shot in df.iterrows():
        loc = shot.get("location")
        if loc is None or not isinstance(loc, (list, tuple)) or len(loc) < 2:
            continue

        x, y = float(loc[0]), float(loc[1])

        # Distance to goal center (in StatsBomb coords, goal at x=120, y=40)
        dx = PITCH_LENGTH - x
        dy = y - GOAL_CENTER_Y
        distance = math.sqrt(dx**2 + dy**2)

        # Angle to goal (radians) — angle subtended by goal posts
        goal_left_y = GOAL_CENTER_Y - 4.0  # ~8 yard goal width / 2
        goal_right_y = GOAL_CENTER_Y + 4.0
        angle_left = math.atan2(goal_left_y - y, PITCH_LENGTH - x)
        angle_right = math.atan2(goal_right_y - y, PITCH_LENGTH - x)
        angle = abs(angle_right - angle_left)

        # Body part
        body_part = str(shot.get("shot_body_part", "Unknown"))
        is_head = 1 if "Head" in body_part else 0
        is_right = 1 if "Right" in body_part else 0
        is_left = 1 if "Left" in body_part else 0

        # Play pattern / technique
        technique = str(shot.get("shot_technique", "Normal"))
        is_volley = 1 if "Volley" in technique else 0
        is_half_volley = 1 if "Half Volley" in technique else 0

        # Shot type
        shot_type = str(shot.get("shot_type", "Open Play"))
        is_penalty = 1 if "Penalty" in shot_type else 0
        is_free_kick = 1 if "Free Kick" in shot_type else 0

        # First time shot
        first_time = 1 if shot.get("shot_first_time") else 0

        # Outcome
        outcome = str(shot.get("shot_outcome", ""))
        is_goal = 1 if "Goal" in outcome else 0

        # StatsBomb xG for comparison
        sb_xg = float(shot.get("shot_statsbomb_xg", 0.0)) if pd.notna(shot.get("shot_statsbomb_xg")) else 0.0

        records.append({
            "distance": distance,
            "angle": angle,
            "x": x,
            "y": y,
            "is_head": is_head,
            "is_right_foot": is_right,
            "is_left_foot": is_left,
            "is_volley": is_volley,
            "is_half_volley": is_half_volley,
            "is_penalty": is_penalty,
            "is_free_kick": is_free_kick,
            "first_time": first_time,
            "is_goal": is_goal,
            "sb_xg": sb_xg,
            "team": shot.get("team", ""),
            "player": shot.get("player", ""),
            "match_id": shot.get("match_id"),
            "competition_id": shot.get("competition_id"),
        })

    feat_df = pd.DataFrame(records)
    print(f"Engineered features for {len(feat_df)} shots ({feat_df['is_goal'].sum()} goals)")
    return feat_df


FEATURE_COLS = [
    "distance", "angle", "x", "y",
    "is_head", "is_right_foot", "is_left_foot",
    "is_volley", "is_half_volley",
    "is_penalty", "is_free_kick", "first_time",
]


def train_model(df: pd.DataFrame):
    """Train and save the xG model."""
    X = df[FEATURE_COLS].values
    y = df["is_goal"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\nTraining set: {len(X_train)} shots ({y_train.sum()} goals, {y_train.mean():.1%} rate)")
    print(f"Test set:     {len(X_test)} shots ({y_test.sum()} goals, {y_test.mean():.1%} rate)")

    # Gradient boosting with calibration
    base_model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )
    model = CalibratedClassifierCV(base_model, cv=5, method="isotonic")
    model.fit(X_train, y_train)

    # Evaluate
    y_prob = model.predict_proba(X_test)[:, 1]
    brier = brier_score_loss(y_test, y_prob)
    logloss = log_loss(y_test, y_prob)
    auc = roc_auc_score(y_test, y_prob)

    print(f"\n--- xG Model Evaluation ---")
    print(f"Brier score: {brier:.4f}")
    print(f"Log loss:    {logloss:.4f}")
    print(f"ROC AUC:     {auc:.4f}")

    # Compare with StatsBomb xG
    if "sb_xg" in df.columns:
        test_indices = df.index[len(X_train):]
        if len(test_indices) == len(y_test):
            sb_xg_test = df.loc[test_indices, "sb_xg"].values
            sb_brier = brier_score_loss(y_test, sb_xg_test)
            print(f"\nStatsBomb xG Brier: {sb_brier:.4f} (for comparison)")

    # Save model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "model": model,
        "feature_cols": FEATURE_COLS,
        "metrics": {"brier": brier, "log_loss": logloss, "roc_auc": auc},
    }
    joblib.dump(artifacts, MODELS_DIR / "xg_model.joblib")
    print(f"\nModel saved to {MODELS_DIR / 'xg_model.joblib'}")

    # Save shot data for API use (shot maps)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_DIR / "shots.csv", index=False)
    print(f"Shot data saved to {DATA_DIR / 'shots.csv'}")

    return model


def main():
    print("=== xG Model Training (P1) ===\n")
    print("Step 1: Fetching shot data from StatsBomb...")
    shots_raw = fetch_shots()

    print("\nStep 2: Engineering features...")
    shots_df = engineer_features(shots_raw)

    print("\nStep 3: Training model...")
    train_model(shots_df)

    print("\nDone!")


if __name__ == "__main__":
    main()
