"""
Feature engineering for match outcome prediction.
All features computed as-of-match-date (no leakage).
Dynamic Elo computed from match results.
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
HOST_NATIONS = {"USA", "Canada", "Mexico"}

# Elo calculation parameters
ELO_K = 40  # K-factor for international football
ELO_HOME_ADVANTAGE = 100  # Home advantage in Elo points


def load_data():
    matches = pd.read_csv(DATA_DIR / "matches.csv", parse_dates=["date"],
                          encoding="utf-8-sig", encoding_errors="replace")
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


def expected_score(elo_a: float, elo_b: float) -> float:
    """Expected score for team A against team B."""
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400))


def compute_dynamic_elo(matches: pd.DataFrame, initial_elo: dict) -> dict:
    """Compute dynamic Elo ratings from match results.
    Returns a dict mapping (team, date) → elo_before_that_match,
    plus final Elo for each team.
    """
    elo = dict(initial_elo)
    default_elo = 1500
    # Store Elo snapshots: team → list of (date, elo_before)
    elo_history = {}

    matches_sorted = matches.sort_values("date").reset_index(drop=True)

    for _, m in matches_sorted.iterrows():
        home = m["home_team"]
        away = m["away_team"]
        date = m["date"]

        elo_h = elo.get(home, default_elo)
        elo_a = elo.get(away, default_elo)

        # Record elo BEFORE this match
        if home not in elo_history:
            elo_history[home] = []
        if away not in elo_history:
            elo_history[away] = []
        elo_history[home].append((date, elo_h))
        elo_history[away].append((date, elo_a))

        # Adjust for home advantage (if not neutral)
        neutral = m.get("neutral_venue", True)
        ha = 0 if neutral else ELO_HOME_ADVANTAGE

        exp_h = expected_score(elo_h + ha, elo_a)
        exp_a = 1.0 - exp_h

        # Actual score
        if m["home_score"] > m["away_score"]:
            actual_h, actual_a = 1.0, 0.0
        elif m["home_score"] == m["away_score"]:
            actual_h, actual_a = 0.5, 0.5
        else:
            actual_h, actual_a = 0.0, 1.0

        # Goal difference multiplier (capped)
        gd = abs(m["home_score"] - m["away_score"])
        gd_mult = max(1.0, np.log(gd + 1) + 1)

        # Update
        elo[home] = elo_h + ELO_K * gd_mult * (actual_h - exp_h)
        elo[away] = elo_a + ELO_K * gd_mult * (actual_a - exp_a)

    return elo, elo_history


def get_elo_at_date(elo_history: dict, team: str, date, default: float = 1500) -> float:
    """Get a team's Elo rating just before a given date."""
    if team not in elo_history:
        return default
    entries = [(d, e) for d, e in elo_history[team] if d < date]
    if not entries:
        return default
    return entries[-1][1]


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
    # Build initial Elo from CSV, then compute dynamic Elo from results
    initial_elo = dict(zip(elo_df["team"], elo_df["elo_rating"]))
    final_elo, elo_history = compute_dynamic_elo(matches, initial_elo)

    matches = matches.sort_values("date").reset_index(drop=True)
    rows = []

    for idx, match in matches.iterrows():
        home = match["home_team"]
        away = match["away_team"]
        date = match["date"]

        # Use dynamic Elo as-of this match date (no leakage)
        elo_home = get_elo_at_date(elo_history, home, date, initial_elo.get(home, 1500))
        elo_away = get_elo_at_date(elo_history, away, date, initial_elo.get(away, 1500))

        home_stats = rolling_stats(matches, home, date)
        away_stats = rolling_stats(matches, away, date)

        neutral = bool(match["neutral_venue"])
        host_flag = 1 if (not neutral and home in HOST_NATIONS) else 0

        row = {
            "date": date,
            "home_team": home,
            "away_team": away,
            "elo_home": round(elo_home),
            "elo_away": round(elo_away),
            "elo_diff": round(elo_home - elo_away),
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


def get_current_elo(matches: pd.DataFrame, elo_df: pd.DataFrame) -> dict:
    """Get the most up-to-date Elo for all teams (after all matches)."""
    initial_elo = dict(zip(elo_df["team"], elo_df["elo_rating"]))
    final_elo, _ = compute_dynamic_elo(matches, initial_elo)
    return final_elo


def main():
    matches, elo = load_data()
    print(f"Loaded {len(matches)} matches, {len(elo)} teams with Elo ratings")

    features = build_feature_table(matches, elo)
    out_path = DATA_DIR / "features.csv"
    features.to_csv(out_path, index=False)
    print(f"Saved feature table ({len(features)} rows) to {out_path}")
    print(f"\nResult distribution:\n{features['result'].value_counts().sort_index()}")
    print(f"  0=away_win, 1=draw, 2=home_win")

    # Show top 10 teams by final Elo
    final_elo = get_current_elo(matches, elo)
    sorted_elo = sorted(final_elo.items(), key=lambda x: x[1], reverse=True)[:15]
    print(f"\nTop 15 teams by dynamic Elo:")
    for team, rating in sorted_elo:
        print(f"  {team}: {rating:.0f}")


if __name__ == "__main__":
    main()
