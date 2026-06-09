"""
Feature engineering for match outcome prediction.
All features computed as-of-match-date (no leakage).
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
HOST_NATIONS = {"USA", "Canada", "Mexico"}


def load_data():
    matches = pd.read_csv(DATA_DIR / "matches.csv", parse_dates=["date"])
    elo = pd.read_csv(DATA_DIR / "elo_ratings.csv")
    return matches, elo


def compute_result(row):
    if row["home_score"] > row["away_score"]:
        return 2  # home win
    elif row["home_score"] == row["away_score"]:
        return 1  # draw
    else:
        return 0  # away win


def compute_points(row):
    if row["home_score"] > row["away_score"]:
        return 3, 0
    elif row["home_score"] == row["away_score"]:
        return 1, 1
    else:
        return 0, 3


def rolling_stats(matches: pd.DataFrame, team: str, before_date, n=10):
    """Compute rolling stats for a team using only matches BEFORE the given date."""
    team_matches = matches[
        ((matches["home_team"] == team) | (matches["away_team"] == team))
        & (matches["date"] < before_date)
    ].sort_values("date").tail(n)

    if len(team_matches) == 0:
        return {
            "goals_scored_rate": 1.0,
            "goals_conceded_rate": 1.0,
            "points_rate": 1.0,
            "form_str": "-----",
        }

    goals_scored = []
    goals_conceded = []
    points = []
    form_chars = []

    for _, m in team_matches.iterrows():
        if m["home_team"] == team:
            goals_scored.append(m["home_score"])
            goals_conceded.append(m["away_score"])
            hp, _ = compute_points(m)
            points.append(hp)
            if m["home_score"] > m["away_score"]:
                form_chars.append("W")
            elif m["home_score"] == m["away_score"]:
                form_chars.append("D")
            else:
                form_chars.append("L")
        else:
            goals_scored.append(m["away_score"])
            goals_conceded.append(m["home_score"])
            _, ap = compute_points(m)
            points.append(ap)
            if m["away_score"] > m["home_score"]:
                form_chars.append("W")
            elif m["home_score"] == m["away_score"]:
                form_chars.append("D")
            else:
                form_chars.append("L")

    return {
        "goals_scored_rate": np.mean(goals_scored),
        "goals_conceded_rate": np.mean(goals_conceded),
        "points_rate": np.mean(points),
        "form_str": "".join(form_chars[-5:]),
    }


def build_feature_table(matches: pd.DataFrame, elo_df: pd.DataFrame) -> pd.DataFrame:
    """Build the feature table for training. No leakage — all features as-of-date."""
    elo_map = dict(zip(elo_df["team"], elo_df["elo_rating"]))
    default_elo = 1700

    matches = matches.sort_values("date").reset_index(drop=True)
    rows = []

    for idx, match in matches.iterrows():
        home = match["home_team"]
        away = match["away_team"]
        date = match["date"]

        elo_home = elo_map.get(home, default_elo)
        elo_away = elo_map.get(away, default_elo)

        home_stats = rolling_stats(matches, home, date)
        away_stats = rolling_stats(matches, away, date)

        neutral = bool(match["neutral_venue"])
        host_flag = 1 if (not neutral and home in HOST_NATIONS) else 0

        row = {
            "date": date,
            "home_team": home,
            "away_team": away,
            "elo_home": elo_home,
            "elo_away": elo_away,
            "elo_diff": elo_home - elo_away,
            "home_goals_rate": home_stats["goals_scored_rate"],
            "home_conceded_rate": home_stats["goals_conceded_rate"],
            "home_points_rate": home_stats["points_rate"],
            "away_goals_rate": away_stats["goals_scored_rate"],
            "away_conceded_rate": away_stats["goals_conceded_rate"],
            "away_points_rate": away_stats["points_rate"],
            "neutral_venue": int(neutral),
            "host_nation": host_flag,
            "result": compute_result(match),
            "form_home": home_stats["form_str"],
            "form_away": away_stats["form_str"],
        }
        rows.append(row)

    return pd.DataFrame(rows)


def get_feature_columns():
    return [
        "elo_home", "elo_away", "elo_diff",
        "home_goals_rate", "home_conceded_rate", "home_points_rate",
        "away_goals_rate", "away_conceded_rate", "away_points_rate",
        "neutral_venue", "host_nation",
    ]


def main():
    matches, elo = load_data()
    print(f"Loaded {len(matches)} matches, {len(elo)} teams with Elo ratings")

    features = build_feature_table(matches, elo)
    out_path = DATA_DIR / "features.csv"
    features.to_csv(out_path, index=False)
    print(f"Saved feature table ({len(features)} rows) to {out_path}")
    print(f"\nResult distribution:\n{features['result'].value_counts().sort_index()}")
    print(f"  0=away_win, 1=draw, 2=home_win")


if __name__ == "__main__":
    main()
