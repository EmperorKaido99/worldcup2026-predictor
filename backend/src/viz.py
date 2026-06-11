"""
Visualization utilities — mplsoccer shot maps and heatmaps.
Renders PNGs server-side for the frontend to display.
"""

import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mplsoccer import VerticalPitch


DATA_DIR = Path(__file__).parent.parent / "data" / "processed"

# Team ID → StatsBomb team name mapping (for filtering shots)
TEAM_ID_MAP = {
    "ARG": "Argentina", "AUS": "Australia", "BEL": "Belgium", "BRA": "Brazil",
    "CAN": "Canada", "CMR": "Cameroon", "CRC": "Costa Rica", "CRO": "Croatia",
    "DEN": "Denmark", "ECU": "Ecuador", "ENG": "England", "FRA": "France",
    "GER": "Germany", "GHA": "Ghana", "IRN": "Iran", "JPN": "Japan",
    "KOR": "Korea Republic", "MEX": "Mexico", "MAR": "Morocco", "NED": "Netherlands",
    "POL": "Poland", "POR": "Portugal", "QAT": "Qatar", "KSA": "Saudi Arabia",
    "SEN": "Senegal", "SRB": "Serbia", "ESP": "Spain", "SUI": "Switzerland",
    "TUN": "Tunisia", "URU": "Uruguay", "USA": "United States", "WAL": "Wales",
    "COL": "Colombia", "PAR": "Paraguay", "CHI": "Chile", "PER": "Peru",
    "BOL": "Bolivia", "VEN": "Venezuela", "NGA": "Nigeria", "ALG": "Algeria",
    "EGY": "Egypt", "CIV": "Ivory Coast", "COD": "DR Congo",
    "NOR": "Norway", "SWE": "Sweden", "CZE": "Czech Republic",
    "JOR": "Jordan", "CPV": "Cape Verde", "CUW": "Curacao",
    "HAI": "Haiti", "BIH": "Bosnia and Herzegovina",
    "ITA": "Italy", "TUR": "Turkey", "SCO": "Scotland",
}


def _load_shots() -> pd.DataFrame:
    """Load the processed shot data."""
    shots_path = DATA_DIR / "shots.csv"
    if not shots_path.exists():
        raise FileNotFoundError(
            "Shot data not found. Run: python -m src.train_xg"
        )
    return pd.read_csv(shots_path)


def generate_shot_map(team_id: str, position: str = "ALL") -> bytes:
    """
    Generate a shot map PNG for a team.
    Returns PNG bytes.
    """
    shots = _load_shots()
    team_name = TEAM_ID_MAP.get(team_id, team_id)

    # Filter to team
    team_shots = shots[shots["team"] == team_name]
    if team_shots.empty:
        # Try partial match
        team_shots = shots[shots["team"].str.contains(team_name, case=False, na=False)]

    if team_shots.empty:
        return _empty_pitch_png(f"No shot data for {team_name}")

    # Create pitch
    pitch = VerticalPitch(
        pitch_type="statsbomb",
        half=True,
        pitch_color="#0e1117",
        line_color="#333333",
        goal_type="box",
    )
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_facecolor("#0e1117")

    goals = team_shots[team_shots["is_goal"] == 1]
    non_goals = team_shots[team_shots["is_goal"] == 0]

    # Plot non-goals
    if not non_goals.empty:
        pitch.scatter(
            non_goals["x"], non_goals["y"],
            ax=ax, s=non_goals["sb_xg"] * 400 + 20,
            c="#555555", edgecolors="#888888", linewidth=0.5,
            alpha=0.5, zorder=2,
        )

    # Plot goals
    if not goals.empty:
        pitch.scatter(
            goals["x"], goals["y"],
            ax=ax, s=goals["sb_xg"] * 400 + 40,
            c="#10b981", edgecolors="#34d399", linewidth=1,
            alpha=0.9, zorder=3, marker="*",
        )

    # Title
    total_xg = team_shots["sb_xg"].sum()
    ax.set_title(
        f"{team_name} — {len(goals)} goals from {len(team_shots)} shots (xG: {total_xg:.1f})",
        color="white", fontsize=12, pad=10,
    )

    # Legend
    ax.scatter([], [], c="#10b981", marker="*", s=60, label="Goal")
    ax.scatter([], [], c="#555555", s=30, label="No goal")
    ax.legend(loc="lower right", fontsize=8, facecolor="#0e1117",
              edgecolor="#333333", labelcolor="white")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor="#0e1117", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_heatmap(team_id: str) -> bytes:
    """Generate a shot heatmap PNG for a team."""
    shots = _load_shots()
    team_name = TEAM_ID_MAP.get(team_id, team_id)

    team_shots = shots[shots["team"] == team_name]
    if team_shots.empty:
        team_shots = shots[shots["team"].str.contains(team_name, case=False, na=False)]

    if team_shots.empty:
        return _empty_pitch_png(f"No shot data for {team_name}")

    pitch = VerticalPitch(
        pitch_type="statsbomb",
        half=True,
        pitch_color="#0e1117",
        line_color="#333333",
    )
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_facecolor("#0e1117")

    # KDE heatmap
    try:
        pitch.kdeplot(
            team_shots["x"], team_shots["y"],
            ax=ax, cmap="YlOrRd", fill=True, levels=50, alpha=0.7,
        )
    except Exception:
        # Fallback to hexbin if KDE fails (too few points)
        pitch.hexbin(
            team_shots["x"], team_shots["y"],
            ax=ax, cmap="YlOrRd", gridsize=10,
        )

    total_xg = team_shots["sb_xg"].sum()
    ax.set_title(
        f"{team_name} — Shot Density Heatmap ({len(team_shots)} shots, xG: {total_xg:.1f})",
        color="white", fontsize=12, pad=10,
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor="#0e1117", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _empty_pitch_png(message: str) -> bytes:
    """Return a pitch PNG with a 'no data' message."""
    pitch = VerticalPitch(
        pitch_type="statsbomb",
        half=True,
        pitch_color="#0e1117",
        line_color="#333333",
    )
    fig, ax = pitch.draw(figsize=(8, 6))
    fig.patch.set_facecolor("#0e1117")
    ax.text(60, 60, message, ha="center", va="center",
            color="#666666", fontsize=14)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor="#0e1117", edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def get_team_xg_stats(team_id: str) -> dict:
    """Get summary xG stats for a team."""
    shots = _load_shots()
    team_name = TEAM_ID_MAP.get(team_id, team_id)

    team_shots = shots[shots["team"] == team_name]
    if team_shots.empty:
        team_shots = shots[shots["team"].str.contains(team_name, case=False, na=False)]

    if team_shots.empty:
        return {
            "team": team_name,
            "total_shots": 0,
            "goals": 0,
            "total_xg": 0,
            "xg_per_shot": 0,
            "conversion_rate": 0,
            "top_scorers": [],
        }

    goals = team_shots[team_shots["is_goal"] == 1]
    total_xg = float(team_shots["sb_xg"].sum())

    # Top scorers
    if not goals.empty and "player" in goals.columns:
        scorer_counts = goals["player"].value_counts().head(5)
        top_scorers = [
            {"player": name, "goals": int(count)}
            for name, count in scorer_counts.items()
        ]
    else:
        top_scorers = []

    return {
        "team": team_name,
        "total_shots": int(len(team_shots)),
        "goals": int(len(goals)),
        "total_xg": round(total_xg, 2),
        "xg_per_shot": round(total_xg / len(team_shots), 3) if len(team_shots) > 0 else 0,
        "conversion_rate": round(len(goals) / len(team_shots), 3) if len(team_shots) > 0 else 0,
        "top_scorers": top_scorers,
    }


def generate_penalty_grid(player_id: str, keeper_id: str):
    """Generate a penalty probability grid. P2 feature — not yet implemented."""
    raise NotImplementedError("Penalty prediction is a P2 feature")
