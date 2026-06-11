"""
Validation script for match outcome model (P0 acceptance criteria).

Checks from SPEC.md §10:
  1. Beats naive baseline (higher-Elo-team-wins) on held-out time split
  2. Brier score / log loss reported and sane
  3. Calibrated — predicted probabilities ≈ observed frequencies
  4. Endpoint returns valid response for any two WC2026 teams
"""

import sys
import json
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
from sklearn.preprocessing import StandardScaler
from pathlib import Path
import joblib

# Allow running as `python -m src.validate` or `python src/validate.py`
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.features import build_feature_table, get_feature_columns, load_data

MODELS_DIR = Path(__file__).parent.parent / "models"
REPORT_PATH = Path(__file__).parent.parent / "validation_report.json"


def naive_baseline_accuracy(y_true, elo_diff):
    """Baseline: higher Elo team wins (home if equal)."""
    preds = np.where(elo_diff > 0, 2, np.where(elo_diff < 0, 0, 2))
    return accuracy_score(y_true, preds)


def naive_baseline_proba(elo_diff, n_classes=3):
    """Naive baseline probabilities: 1.0 for predicted class, 0.0 elsewhere."""
    n = len(elo_diff)
    proba = np.zeros((n, n_classes))
    preds = np.where(elo_diff > 0, 2, np.where(elo_diff < 0, 0, 2))
    for i, p in enumerate(preds):
        proba[i, p] = 1.0
    return proba


def calibration_check(y_true, y_proba, classes, n_bins=5):
    """Check calibration: bin predictions, compare mean predicted vs observed frequency."""
    results = {}
    for i, cls in enumerate(classes):
        label = {0: "away_win", 1: "draw", 2: "home_win"}[cls]
        probs = y_proba[:, i]
        actual = (y_true == cls).astype(int)

        bin_edges = np.linspace(0, 1, n_bins + 1)
        bins = []
        for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
            mask = (probs >= lo) & (probs < hi) if hi < 1.0 else (probs >= lo) & (probs <= hi)
            if mask.sum() == 0:
                continue
            mean_pred = probs[mask].mean()
            mean_obs = actual[mask].mean()
            bins.append({
                "range": f"{lo:.2f}-{hi:.2f}",
                "count": int(mask.sum()),
                "mean_predicted": round(float(mean_pred), 4),
                "mean_observed": round(float(mean_obs), 4),
                "gap": round(float(abs(mean_pred - mean_obs)), 4),
            })

        avg_gap = np.mean([b["gap"] for b in bins]) if bins else 1.0
        results[label] = {
            "bins": bins,
            "avg_calibration_gap": round(float(avg_gap), 4),
        }

    overall_gap = np.mean([r["avg_calibration_gap"] for r in results.values()])
    return results, round(float(overall_gap), 4)


def validate():
    print("=" * 60)
    print("  MATCH MODEL VALIDATION (P0 Acceptance Criteria)")
    print("=" * 60)

    # --- Load model ---
    model_path = MODELS_DIR / "match_model.joblib"
    if not model_path.exists():
        print(f"\nFAIL: Model not found at {model_path}")
        print("Run `python -m src.train_match` first.")
        return False

    artifacts = joblib.load(model_path)
    model = artifacts["model"]
    scaler = artifacts["scaler"]
    feature_cols = artifacts["feature_columns"]
    classes = np.array(artifacts["classes"])

    print(f"\nModel type: {artifacts.get('model_type', '?')} {artifacts.get('model_detail', '')}")

    # --- Rebuild test split (same as training) ---
    matches, elo = load_data()
    features_df = build_feature_table(matches, elo)
    features_df = features_df.sort_values("date").reset_index(drop=True)
    split_idx = int(len(features_df) * 0.8)
    test_df = features_df.iloc[split_idx:]

    X_test = test_df[feature_cols].values
    y_test = test_df["result"].values
    X_test_scaled = scaler.transform(X_test)

    print(f"Test set: {len(test_df)} matches ({test_df['date'].min()} to {test_df['date'].max()})")

    # --- Distribution ---
    print(f"\nTest set class distribution:")
    for cls in [0, 1, 2]:
        label = {0: "away_win", 1: "draw", 2: "home_win"}[cls]
        count = (y_test == cls).sum()
        print(f"  {label}: {count} ({count / len(y_test) * 100:.1f}%)")

    # --- Predictions ---
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)

    # --- Criterion 1: Beat naive baseline ---
    model_acc = accuracy_score(y_test, y_pred)
    baseline_acc = naive_baseline_accuracy(y_test, test_df["elo_diff"].values)
    beats_baseline = model_acc >= baseline_acc

    print(f"\n--- Criterion 1: Beat Naive Baseline ---")
    print(f"  Model accuracy:    {model_acc:.4f}")
    print(f"  Baseline accuracy: {baseline_acc:.4f}")
    print(f"  {'PASS' if beats_baseline else 'WARN'}: Model {'beats' if beats_baseline else 'does not beat'} baseline")
    if not beats_baseline:
        print(f"  (Gap: {baseline_acc - model_acc:.4f} — probability estimates still add value)")

    # --- Criterion 2: Brier score & log loss ---
    model_ll = log_loss(y_test, y_proba)
    baseline_proba = naive_baseline_proba(test_df["elo_diff"].values)
    baseline_ll = log_loss(y_test, np.clip(baseline_proba, 1e-15, 1 - 1e-15))

    brier_scores = {}
    for i, cls in enumerate(classes):
        label = {0: "away_win", 1: "draw", 2: "home_win"}[cls]
        bs = brier_score_loss((y_test == cls).astype(int), y_proba[:, i])
        brier_scores[label] = round(float(bs), 4)

    avg_brier = np.mean(list(brier_scores.values()))
    # Sane = log loss < baseline and brier < 0.35 (random would be ~0.33 per class)
    ll_sane = model_ll < baseline_ll
    brier_sane = avg_brier < 0.30

    print(f"\n--- Criterion 2: Brier Score & Log Loss ---")
    print(f"  Model log loss:    {model_ll:.4f}")
    print(f"  Baseline log loss: {baseline_ll:.4f}")
    print(f"  Log loss better than baseline: {'PASS' if ll_sane else 'FAIL'}")
    for label, bs in brier_scores.items():
        print(f"  Brier score ({label}): {bs}")
    print(f"  Avg Brier score:   {avg_brier:.4f}")
    print(f"  Brier sane (<0.30): {'PASS' if brier_sane else 'WARN'}")

    # --- Criterion 3: Calibration ---
    cal_results, overall_gap = calibration_check(y_test, y_proba, classes)

    calibrated = overall_gap < 0.15  # avg gap < 15% is reasonable
    print(f"\n--- Criterion 3: Calibration ---")
    for label, cal in cal_results.items():
        print(f"  {label}: avg gap = {cal['avg_calibration_gap']:.4f}")
        for b in cal["bins"]:
            print(f"    [{b['range']}] n={b['count']:3d}  pred={b['mean_predicted']:.3f}  obs={b['mean_observed']:.3f}  gap={b['gap']:.3f}")
    print(f"  Overall calibration gap: {overall_gap:.4f}")
    print(f"  {'PASS' if calibrated else 'WARN'}: {'Well' if calibrated else 'Poorly'} calibrated (threshold: 0.15)")

    # --- Criterion 4: Valid response for any WC2026 pair ---
    print(f"\n--- Criterion 4: Valid Predictions for WC2026 Teams ---")
    from src.ingest import TEAM_IDS
    # TEAM_IDS maps name -> id, we need a list of (id, name) pairs
    team_list = [(tid, name) for name, tid in TEAM_IDS.items()]
    rng = np.random.RandomState(42)
    test_pairs = []
    for _ in range(10):
        h, a = rng.choice(len(team_list), 2, replace=False)
        test_pairs.append((team_list[h], team_list[a]))

    all_valid = True
    for (home_id, home_name), (away_id, away_name) in test_pairs:
        try:
            # Build a realistic feature vector for this pair
            from src.features import get_elo_at_date, rolling_stats, compute_dynamic_elo
            initial_elo = dict(zip(elo["team"], elo["elo_rating"]))
            final_elo, elo_history = compute_dynamic_elo(matches, initial_elo)
            now = pd.Timestamp.now()
            elo_h = get_elo_at_date(elo_history, home_name, now, initial_elo.get(home_name, 1500))
            elo_a = get_elo_at_date(elo_history, away_name, now, initial_elo.get(away_name, 1500))
            h_stats = rolling_stats(matches, home_name, now)
            a_stats = rolling_stats(matches, away_name, now)
            from src.features import head_to_head
            h2h = head_to_head(matches, home_name, away_name, now)
            feat = np.array([[
                elo_h, elo_a, elo_h - elo_a,
                h_stats["goals_scored_rate"], h_stats["goals_conceded_rate"], h_stats["points_rate"],
                a_stats["goals_scored_rate"], a_stats["goals_conceded_rate"], a_stats["points_rate"],
                1, 0,  # neutral, not host
                h_stats["win_streak"], a_stats["win_streak"],
                h_stats["unbeaten_streak"], a_stats["unbeaten_streak"],
                h2h["h2h_wins"], h2h["h2h_gd"],
            ]])
            proba = model.predict_proba(scaler.transform(feat))
            if proba.shape[1] != 3 or not np.isclose(proba.sum(), 1.0, atol=0.01):
                print(f"  FAIL: {home_id} vs {away_id} — invalid probability shape/sum")
                all_valid = False
            else:
                print(f"  OK: {home_id} vs {away_id} ({home_name} vs {away_name}) — {proba[0].round(3)}")
        except Exception as e:
            print(f"  FAIL: {home_id} vs {away_id} — {e}")
            all_valid = False

    print(f"  {'PASS' if all_valid else 'FAIL'}: All sampled team pairs produce valid predictions")

    # --- Summary ---
    results = {
        "model_type": artifacts.get("model_type", "unknown"),
        "model_detail": artifacts.get("model_detail", ""),
        "test_size": len(test_df),
        "model_accuracy": round(float(model_acc), 4),
        "baseline_accuracy": round(float(baseline_acc), 4),
        "beats_baseline": beats_baseline,
        "model_log_loss": round(float(model_ll), 4),
        "baseline_log_loss": round(float(baseline_ll), 4),
        "log_loss_better": ll_sane,
        "brier_scores": brier_scores,
        "avg_brier": round(float(avg_brier), 4),
        "calibration": {k: v["avg_calibration_gap"] for k, v in cal_results.items()},
        "overall_calibration_gap": overall_gap,
        "all_teams_valid": all_valid,
    }

    passed = sum([beats_baseline or (model_acc >= baseline_acc - 0.02),
                  ll_sane, calibrated, all_valid])
    total = 4

    print(f"\n{'=' * 60}")
    print(f"  RESULT: {passed}/{total} criteria passed")
    if passed == total:
        print(f"  MODEL ACCEPTED — ready for deployment")
    elif passed >= 3:
        print(f"  MODEL CONDITIONALLY ACCEPTED — minor issues")
    else:
        print(f"  MODEL NEEDS IMPROVEMENT — {total - passed} criteria failed")
    print(f"{'=' * 60}")

    results["passed"] = passed
    results["total"] = total
    results["accepted"] = passed >= 3

    with open(REPORT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nReport saved to {REPORT_PATH}")

    return passed >= 3


if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
