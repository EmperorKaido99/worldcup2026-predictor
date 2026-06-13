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

# Tournament importance weights for filtering/weighting
TOURNAMENT_WEIGHTS = {
    "world cup": 1.0,
    "euro": 0.9,
    "copa america": 0.9,
    "afcon": 0.85,
    "asian cup": 0.85,
    "gold cup": 0.8,
    "nations league": 0.8,
    "qualification": 0.75,
    "wcq": 0.75,
    "friendly": 0.5,
}


def get_tournament_weight(tournament: str) -> float:
    """Get importance weight for a tournament."""
    t = str(tournament).lower()
    for key, weight in TOURNAMENT_WEIGHTS.items():
        if key in t:
            return weight
    return 0.6  # default


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
    """Compute dynamic Elo ratings from match results."""
    elo = dict(initial_elo)
    default_elo = 1500
    elo_history = {}

    matches_sorted = matches.sort_values("date").reset_index(drop=True)

    for _, m in matches_sorted.iterrows():
        home = m["home_team"]
        away = m["away_team"]
        date = m["date"]

        elo_h = elo.get(home, default_elo)
        elo_a = elo.get(away, default_elo)

        if home not in elo_history:
            elo_history[home] = []
        if away not in elo_history:
            elo_history[away] = []
        elo_history[home].append((date, elo_h))
        elo_history[away].append((date, elo_a))

        neutral = m.get("neutral_venue", True)
        ha = 0 if neutral else ELO_HOME_ADVANTAGE

        exp_h = expected_score(elo_h + ha, elo_a)
        exp_a = 1.0 - exp_h

        if m["home_score"] > m["away_score"]:
            actual_h, actual_a = 1.0, 0.0
        elif m["home_score"] == m["away_score"]:
            actual_h, actual_a = 0.5, 0.5
        else:
            actual_h, actual_a = 0.0, 1.0

        gd = abs(m["home_score"] - m["away_score"])
        gd_mult = max(1.0, np.log(gd + 1) + 1)

        # Tournament-weighted K factor
        tourn_weight = get_tournament_weight(m.get("tournament", ""))
        k = ELO_K * tourn_weight

        elo[home] = elo_h + k * gd_mult * (actual_h - exp_h)
        elo[away] = elo_a + k * gd_mult * (actual_a - exp_a)

    return elo, elo_history


def get_elo_at_date(elo_history: dict, team: str, date, default: float = 1500) -> float:
    """Get a team's Elo rating just before a given date."""
    if team not in elo_history:
        return default
    entries = [(d, e) for d, e in elo_history[team] if d < date]
    if not entries:
        return default
    return entries[-1][1]


def get_elo_momentum(elo_history: dict, team: str, date, n=5) -> float:
    """Elo change over last N snapshots — positive = improving."""
    if team not in elo_history:
        return 0.0
    entries = [e for d, e in elo_history[team] if d < date]
    if len(entries) < 2:
        return 0.0
    recent = entries[-n:]
    return recent[-1] - recent[0]


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
            "gd_rate": 0.0,
            "win_rate": 0.0,
            "clean_sheet_rate": 0.0,
            "form_str": "-----",
            "win_streak": 0,
            "unbeaten_streak": 0,
            "rest_days": 30,
        }

    goals_scored = []
    goals_conceded = []
    points = []
    form_chars = []
    clean_sheets = 0

    for _, m in team_matches.iterrows():
        if m["home_team"] == team:
            goals_scored.append(m["home_score"])
            goals_conceded.append(m["away_score"])
            hp, _ = compute_points(m)
            points.append(hp)
            if m["away_score"] == 0:
                clean_sheets += 1
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
            if m["home_score"] == 0:
                clean_sheets += 1
            if m["away_score"] > m["home_score"]:
                form_chars.append("W")
            elif m["home_score"] == m["away_score"]:
                form_chars.append("D")
            else:
                form_chars.append("L")

    # Compute streaks from most recent match backwards
    win_streak = 0
    for c in reversed(form_chars):
        if c == "W":
            win_streak += 1
        else:
            break

    unbeaten_streak = 0
    for c in reversed(form_chars):
        if c in ("W", "D"):
            unbeaten_streak += 1
        else:
            break

    # Rest days since last match
    last_match_date = team_matches["date"].max()
    rest_days = (before_date - last_match_date).days if pd.notna(last_match_date) else 30

    gs = np.array(goals_scored)
    gc = np.array(goals_conceded)
    wins = sum(1 for c in form_chars if c == "W")

    return {
        "goals_scored_rate": float(np.mean(gs)),
        "goals_conceded_rate": float(np.mean(gc)),
        "points_rate": float(np.mean(points)),
        "gd_rate": float(np.mean(gs - gc)),
        "win_rate": wins / len(form_chars) if form_chars else 0.0,
        "clean_sheet_rate": clean_sheets / len(team_matches),
        "form_str": "".join(form_chars[-5:]),
        "win_streak": win_streak,
        "unbeaten_streak": unbeaten_streak,
        "rest_days": min(rest_days, 90),  # cap at 90 days
    }


def rolling_stats_short(matches: pd.DataFrame, team: str, before_date, n=5):
    """Short-window rolling stats (last 5 matches) for recent form."""
    return rolling_stats(matches, team, before_date, n=n)


def head_to_head(matches: pd.DataFrame, team1: str, team2: str, before_date, n=5):
    """Compute head-to-head record between two teams before a given date."""
    h2h = matches[
        (
            ((matches["home_team"] == team1) & (matches["away_team"] == team2))
            | ((matches["home_team"] == team2) & (matches["away_team"] == team1))
        )
        & (matches["date"] < before_date)
    ].sort_values("date").tail(n)

    if len(h2h) == 0:
        return {"h2h_wins": 0, "h2h_draws": 0, "h2h_losses": 0, "h2h_gd": 0}

    wins, draws, losses, gd = 0, 0, 0, 0
    for _, m in h2h.iterrows():
        if m["home_team"] == team1:
            gd += m["home_score"] - m["away_score"]
            if m["home_score"] > m["away_score"]:
                wins += 1
            elif m["home_score"] == m["away_score"]:
                draws += 1
            else:
                losses += 1
        else:
            gd += m["away_score"] - m["home_score"]
            if m["away_score"] > m["home_score"]:
                wins += 1
            elif m["home_score"] == m["away_score"]:
                draws += 1
            else:
                losses += 1

    return {"h2h_wins": wins, "h2h_draws": draws, "h2h_losses": losses, "h2h_gd": gd}


def build_feature_table(matches: pd.DataFrame, elo_df: pd.DataFrame) -> pd.DataFrame:
    """Build the feature table for training. No leakage — all features as-of-date."""
    initial_elo = dict(zip(elo_df["team"], elo_df["elo_rating"]))
    final_elo, elo_history = compute_dynamic_elo(matches, initial_elo)

    matches = matches.sort_values("date").reset_index(drop=True)
    rows = []

    for idx, match in matches.iterrows():
        home = match["home_team"]
        away = match["away_team"]
        date = match["date"]

        # Dynamic Elo as-of this match date
        elo_home = get_elo_at_date(elo_history, home, date, initial_elo.get(home, 1500))
        elo_away = get_elo_at_date(elo_history, away, date, initial_elo.get(away, 1500))

        # Elo momentum (improvement trend)
        elo_mom_home = get_elo_momentum(elo_history, home, date)
        elo_mom_away = get_elo_momentum(elo_history, away, date)

        # Expected score from Elo (calibrated probability)
        elo_expected = expected_score(elo_home, elo_away)

        # Long-form stats (last 10 matches)
        home_stats = rolling_stats(matches, home, date, n=10)
        away_stats = rolling_stats(matches, away, date, n=10)

        # Short-form stats (last 5 matches — recent form)
        home_short = rolling_stats_short(matches, home, date, n=5)
        away_short = rolling_stats_short(matches, away, date, n=5)

        h2h = head_to_head(matches, home, away, date)

        neutral = bool(match["neutral_venue"])
        host_flag = 1 if (not neutral and home in HOST_NATIONS) else 0

        # Tournament importance
        tourn_weight = get_tournament_weight(match.get("tournament", ""))

        row = {
            "date": date,
            "home_team": home,
            "away_team": away,
            # Elo features
            "elo_home": round(elo_home),
            "elo_away": round(elo_away),
            "elo_diff": round(elo_home - elo_away),
            "elo_expected": round(elo_expected, 3),
            "elo_momentum_home": round(elo_mom_home, 1),
            "elo_momentum_away": round(elo_mom_away, 1),
            # Long-form stats (10 matches)
            "home_goals_rate": home_stats["goals_scored_rate"],
            "home_conceded_rate": home_stats["goals_conceded_rate"],
            "home_points_rate": home_stats["points_rate"],
            "home_gd_rate": home_stats["gd_rate"],
            "away_goals_rate": away_stats["goals_scored_rate"],
            "away_conceded_rate": away_stats["goals_conceded_rate"],
            "away_points_rate": away_stats["points_rate"],
            "away_gd_rate": away_stats["gd_rate"],
            # Short-form stats (5 matches — recent form)
            "home_win_rate_5": home_short["win_rate"],
            "away_win_rate_5": away_short["win_rate"],
            "home_gd_rate_5": home_short["gd_rate"],
            "away_gd_rate_5": away_short["gd_rate"],
            # Defensive stats
            "home_clean_sheet_rate": home_stats["clean_sheet_rate"],
            "away_clean_sheet_rate": away_stats["clean_sheet_rate"],
            # Venue
            "neutral_venue": int(neutral),
            "host_nation": host_flag,
            # Form/streaks
            "home_win_streak": home_stats["win_streak"],
            "away_win_streak": away_stats["win_streak"],
            "home_unbeaten": home_stats["unbeaten_streak"],
            "away_unbeaten": away_stats["unbeaten_streak"],
            # Rest days
            "home_rest_days": home_stats["rest_days"],
            "away_rest_days": away_stats["rest_days"],
            # Head-to-head
            "h2h_wins": h2h["h2h_wins"],
            "h2h_gd": h2h["h2h_gd"],
            # Tournament importance
            "tournament_weight": tourn_weight,
            # Target
            "result": compute_result(match),
            "form_home": home_stats["form_str"],
            "form_away": away_stats["form_str"],
        }
        rows.append(row)

    return pd.DataFrame(rows)


def get_feature_columns():
    return [
        "elo_home", "elo_away", "elo_diff", "elo_expected",
        "elo_momentum_home", "elo_momentum_away",
        "home_goals_rate", "home_conceded_rate", "home_points_rate", "home_gd_rate",
        "away_goals_rate", "away_conceded_rate", "away_points_rate", "away_gd_rate",
        "home_win_rate_5", "away_win_rate_5",
        "home_gd_rate_5", "away_gd_rate_5",
        "home_clean_sheet_rate", "away_clean_sheet_rate",
        "neutral_venue", "host_nation",
        "home_win_streak", "away_win_streak",
        "home_unbeaten", "away_unbeaten",
        "home_rest_days", "away_rest_days",
        "h2h_wins", "h2h_gd",
        "tournament_weight",
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
    print(f"\nFeature columns ({len(get_feature_columns())}):")
    for col in get_feature_columns():
        print(f"  {col}")

    # Show top 15 teams by final Elo
    final_elo = get_current_elo(matches, elo)
    sorted_elo = sorted(final_elo.items(), key=lambda x: x[1], reverse=True)[:15]
    print(f"\nTop 15 teams by dynamic Elo:")
    for team, rating in sorted_elo:
        print(f"  {team}: {rating:.0f}")


if __name__ == "__main__":
    main()
