"""
Penalty Predictor (P2) — Train a penalty placement model using StatsBomb data.

Pulls penalty/shootout events from World Cup data, maps shot end-locations
to a 3x3 goal grid, and trains a model to predict placement probabilities.

Usage:
    python -m src.train_penalty
"""

import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from statsbombpy import sb

MODELS_DIR = Path(__file__).parent.parent / "models"
DATA_DIR = Path(__file__).parent.parent / "data" / "processed"

# All StatsBomb competitions with open data that include penalties
COMPETITIONS = [
    (43, 106),  # FIFA World Cup 2022
    (43, 3),    # FIFA World Cup 2018
    (43, 55),   # FIFA World Cup 1990
    (43, 54),   # FIFA World Cup 1986
    (72, 107),  # Women's World Cup 2023
    (72, 30),   # Women's World Cup 2019
    (11, 90),   # La Liga 2020/21
    (11, 42),   # La Liga 2019/20
    (11, 41),   # La Liga 2018/19
    (2, 44),    # Premier League 2003/04
    (55, 43),   # Euro 2020
    (49, 3),    # NWSL 2018
]

# Goal grid mapping: StatsBomb end_location → 3x3 zone
# StatsBomb goal coords: x is always 120, y from ~36 to ~44, z from 0 to ~2.67
# y: left(36-38.67), center(38.67-41.33), right(41.33-44)
# z: low(0-0.89), mid(0.89-1.78), high(1.78-2.67)
GOAL_Y_MIN = 36.0
GOAL_Y_MAX = 44.0
GOAL_Z_MAX = 2.67


def map_to_grid(y: float, z: float) -> int:
    """Map goal end-location to 0-8 grid zone (3x3, left-to-right, bottom-to-top)."""
    # Normalize
    y_norm = max(0, min(1, (y - GOAL_Y_MIN) / (GOAL_Y_MAX - GOAL_Y_MIN)))
    z_norm = max(0, min(1, z / GOAL_Z_MAX))

    col = min(2, int(y_norm * 3))  # 0=left, 1=center, 2=right
    row = min(2, int(z_norm * 3))  # 0=low, 1=mid, 2=high

    return row * 3 + col  # 0-8


def fetch_penalties() -> pd.DataFrame:
    """Pull all penalty shot events from StatsBomb open data."""
    all_pens = []

    for comp_id, season_id in COMPETITIONS:
        print(f"Fetching penalties from comp {comp_id}, season {season_id}...")
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception as e:
            print(f"  Skipping: {e}")
            continue

        for _, match_row in matches.iterrows():
            match_id = match_row["match_id"]
            try:
                events = sb.events(match_id=match_id)
            except Exception:
                continue

            # Filter for penalty shots
            shots = events[events["type"] == "Shot"]
            penalties = shots[
                shots["shot_type"].apply(
                    lambda x: "Penalty" in str(x) if pd.notna(x) else False
                )
            ].copy()

            if penalties.empty:
                continue

            penalties["match_id"] = match_id
            penalties["competition_id"] = comp_id
            all_pens.append(penalties)

    if not all_pens:
        raise RuntimeError("No penalty data found.")

    df = pd.concat(all_pens, ignore_index=True)
    print(f"\nTotal penalties collected: {len(df)}")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Engineer features from penalty events."""
    records = []

    for _, pen in df.iterrows():
        # End location (where the shot ended up)
        end_loc = pen.get("shot_end_location")
        if end_loc is None or not isinstance(end_loc, (list, tuple)) or len(end_loc) < 2:
            continue

        end_y = float(end_loc[1]) if len(end_loc) > 1 else 40.0
        end_z = float(end_loc[2]) if len(end_loc) > 2 else 1.0

        # Map to grid zone
        zone = map_to_grid(end_y, end_z)

        # Outcome
        outcome = str(pen.get("shot_outcome", ""))
        is_goal = 1 if "Goal" in outcome else 0
        is_saved = 1 if "Saved" in outcome else 0

        # Body part
        body_part = str(pen.get("shot_body_part", "Right Foot"))
        is_right = 1 if "Right" in body_part else 0

        # Technique
        technique = str(pen.get("shot_technique", "Normal"))

        records.append({
            "zone": zone,
            "is_goal": is_goal,
            "is_saved": is_saved,
            "is_right_foot": is_right,
            "end_y": end_y,
            "end_z": end_z,
            "player": pen.get("player", ""),
            "team": pen.get("team", ""),
            "match_id": pen.get("match_id"),
            "competition_id": pen.get("competition_id"),
            "technique": technique,
        })

    feat_df = pd.DataFrame(records)
    print(f"Processed {len(feat_df)} penalties ({feat_df['is_goal'].sum()} goals)")
    return feat_df


def compute_zone_stats(df: pd.DataFrame) -> dict:
    """Compute goal probability for each zone across all penalties."""
    zone_stats = {}
    for zone in range(9):
        zone_shots = df[df["zone"] == zone]
        total = len(zone_shots)
        goals = int(zone_shots["is_goal"].sum())
        prob = goals / total if total > 0 else 0.0
        zone_stats[zone] = {
            "total": total,
            "goals": goals,
            "probability": round(prob, 3),
        }
    return zone_stats


def main():
    print("=== Penalty Predictor Training (P2) ===\n")

    print("Step 1: Fetching penalty data from StatsBomb...")
    pens_raw = fetch_penalties()

    print("\nStep 2: Engineering features...")
    pens_df = engineer_features(pens_raw)

    if pens_df.empty:
        print("No usable penalty data found. Exiting.")
        return

    print("\nStep 3: Computing zone statistics...")
    zone_stats = compute_zone_stats(pens_df)

    print("\n--- Zone Goal Probabilities (3x3 grid) ---")
    print("        Left    Center   Right")
    for row_label, row_idx in [("High", 2), ("Mid", 1), ("Low", 0)]:
        probs = [zone_stats[row_idx * 3 + col]["probability"] for col in range(3)]
        counts = [zone_stats[row_idx * 3 + col]["total"] for col in range(3)]
        print(f"{row_label:>5}   {probs[0]:.1%} ({counts[0]:>2})  {probs[1]:.1%} ({counts[1]:>2})  {probs[2]:.1%} ({counts[2]:>2})")

    # Overall stats
    total_pens = len(pens_df)
    total_goals = int(pens_df["is_goal"].sum())
    conversion = total_goals / total_pens if total_pens > 0 else 0
    print(f"\nOverall: {total_goals}/{total_pens} scored ({conversion:.1%})")

    # Save
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    artifacts = {
        "zone_stats": zone_stats,
        "total_penalties": total_pens,
        "total_goals": total_goals,
        "conversion_rate": round(conversion, 3),
    }
    joblib.dump(artifacts, MODELS_DIR / "penalty_model.joblib")
    print(f"\nModel saved to {MODELS_DIR / 'penalty_model.joblib'}")

    pens_df.to_csv(DATA_DIR / "penalties.csv", index=False)
    print(f"Penalty data saved to {DATA_DIR / 'penalties.csv'}")

    # Per-team stats
    team_stats = {}
    for team, group in pens_df.groupby("team"):
        t_zones = compute_zone_stats(group)
        team_stats[team] = {
            "zones": t_zones,
            "total": len(group),
            "goals": int(group["is_goal"].sum()),
            "conversion": round(int(group["is_goal"].sum()) / len(group), 3) if len(group) > 0 else 0,
        }
    joblib.dump(team_stats, MODELS_DIR / "penalty_team_stats.joblib")
    print(f"Team stats saved to {MODELS_DIR / 'penalty_team_stats.joblib'}")

    # Train a goal probability model (ML-based, not just zone stats)
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, roc_auc_score

    pen_features = ["zone", "is_right_foot", "end_y", "end_z"]
    available = [c for c in pen_features if c in pens_df.columns]
    if len(available) >= 2 and len(pens_df) >= 50:
        X = pens_df[available].values
        y = pens_df["is_goal"].values
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        pen_model = GradientBoostingClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42,
        )
        pen_model.fit(X_tr, y_tr)
        acc = accuracy_score(y_te, pen_model.predict(X_te))
        auc = roc_auc_score(y_te, pen_model.predict_proba(X_te)[:, 1])
        print(f"\nPenalty ML Model: acc={acc:.3f} auc={auc:.3f}")

        artifacts["penalty_ml_model"] = pen_model
        artifacts["penalty_ml_features"] = available
        joblib.dump(artifacts, MODELS_DIR / "penalty_model.joblib")
        print(f"Updated penalty model with ML scorer")

    print("\nDone!")


if __name__ == "__main__":
    main()
