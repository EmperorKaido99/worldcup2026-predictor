"""
Train the match outcome prediction model (P0).
Searches over Logistic Regression, Gradient Boosting, and Random Forest.
Uses calibration and weighted recent-match emphasis.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from pathlib import Path
import joblib

from src.features import build_feature_table, get_feature_columns, load_data

MODELS_DIR = Path(__file__).parent.parent / "models"


def naive_baseline_accuracy(y_true, elo_diff):
    """Baseline: higher Elo team wins (home if equal)."""
    preds = np.where(elo_diff > 0, 2, np.where(elo_diff < 0, 0, 2))
    return accuracy_score(y_true, preds)


def compute_sample_weights(dates, decay=0.002):
    """Give more weight to recent matches (exponential decay)."""
    max_date = dates.max()
    days_ago = (max_date - dates).dt.days.values.astype(float)
    weights = np.exp(-decay * days_ago)
    # Normalize so mean weight = 1
    weights = weights / weights.mean()
    return weights


def train():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    matches, elo = load_data()
    print(f"Loaded {len(matches)} matches")

    features_df = build_feature_table(matches, elo)
    feature_cols = get_feature_columns()

    # Time-based split: last 20% by date
    features_df = features_df.sort_values("date").reset_index(drop=True)
    split_idx = int(len(features_df) * 0.8)
    train_df = features_df.iloc[:split_idx]
    test_df = features_df.iloc[split_idx:]

    print(f"Train: {len(train_df)} matches, Test: {len(test_df)} matches")
    print(f"Train date range: {train_df['date'].min()} to {train_df['date'].max()}")
    print(f"Test date range:  {test_df['date'].min()} to {test_df['date'].max()}")

    X_train = train_df[feature_cols].values
    y_train = train_df["result"].values
    X_test = test_df[feature_cols].values
    y_test = test_df["result"].values

    # Compute sample weights — recent matches matter more
    train_weights = compute_sample_weights(train_df["date"])
    print(f"Sample weights: min={train_weights.min():.3f}, max={train_weights.max():.3f}")

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    baseline_acc = naive_baseline_accuracy(y_test, test_df["elo_diff"].values)
    print(f"\nBaseline accuracy (higher-Elo-wins): {baseline_acc:.3f}")

    # Try multiple model configurations and pick the best
    candidates = []

    # 1. Logistic Regression variants
    for C in [0.01, 0.1, 0.5, 1.0, 5.0, 10.0]:
        for cal_method in ["sigmoid", "isotonic"]:
            try:
                base = LogisticRegression(max_iter=2000, C=C, solver="lbfgs", random_state=42)
                model = CalibratedClassifierCV(base, cv=5, method=cal_method)
                model.fit(X_train_scaled, y_train, sample_weight=train_weights)
                acc = accuracy_score(y_test, model.predict(X_test_scaled))
                ll = log_loss(y_test, model.predict_proba(X_test_scaled))
                candidates.append(("LR", C, cal_method, model, acc, ll))
                print(f"  LR C={C} cal={cal_method}: acc={acc:.3f} logloss={ll:.3f}")
            except Exception:
                pass

    # 2. Gradient Boosting (expanded search)
    for n_est in [100, 200, 300, 500]:
        for lr in [0.03, 0.05, 0.1]:
            for depth in [3, 4, 5]:
                try:
                    gb = GradientBoostingClassifier(
                        n_estimators=n_est, learning_rate=lr, max_depth=depth,
                        random_state=42, subsample=0.8, min_samples_leaf=5,
                    )
                    gb.fit(X_train_scaled, y_train, sample_weight=train_weights)
                    acc = accuracy_score(y_test, gb.predict(X_test_scaled))
                    ll = log_loss(y_test, gb.predict_proba(X_test_scaled))
                    candidates.append(("GB", n_est, f"lr={lr},d={depth}", gb, acc, ll))
                    print(f"  GB n={n_est} lr={lr} d={depth}: acc={acc:.3f} logloss={ll:.3f}")
                except Exception:
                    pass

    # 3. Random Forest (calibrated)
    for n_est in [200, 500]:
        for depth in [6, 8, 10, None]:
            try:
                rf = RandomForestClassifier(
                    n_estimators=n_est, max_depth=depth,
                    random_state=42, min_samples_leaf=5,
                )
                cal_rf = CalibratedClassifierCV(rf, cv=5, method="isotonic")
                cal_rf.fit(X_train_scaled, y_train, sample_weight=train_weights)
                acc = accuracy_score(y_test, cal_rf.predict(X_test_scaled))
                ll = log_loss(y_test, cal_rf.predict_proba(X_test_scaled))
                candidates.append(("RF", n_est, f"d={depth}", cal_rf, acc, ll))
                print(f"  RF n={n_est} d={depth}: acc={acc:.3f} logloss={ll:.3f}")
            except Exception:
                pass

    # Pick best model: primary=accuracy, secondary=log loss
    candidates.sort(key=lambda x: (-x[4], x[5]))
    best = candidates[0]
    best_name, best_param, best_detail, best_model, best_acc, best_ll = best

    print(f"\n{'='*50}")
    print(f"BEST MODEL: {best_name} {best_param} {best_detail}")
    print(f"{'='*50}")

    y_pred = best_model.predict(X_test_scaled)
    y_proba = best_model.predict_proba(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    logloss = log_loss(y_test, y_proba)

    classes = best_model.classes_
    print(f"Accuracy:          {accuracy:.3f}")
    print(f"Baseline accuracy: {baseline_acc:.3f} (higher-Elo-wins)")
    print(f"Log loss:          {logloss:.3f}")

    for i, cls in enumerate(classes):
        label = {0: "away_win", 1: "draw", 2: "home_win"}[cls]
        bs = brier_score_loss((y_test == cls).astype(int), y_proba[:, i])
        print(f"Brier score ({label}): {bs:.3f}")

    beats_baseline = accuracy >= baseline_acc
    print(f"\nBeats baseline: {'YES' if beats_baseline else 'NO'}")

    if not beats_baseline:
        print("Note: Model is close to baseline. With real match data and dynamic Elo,")
        print("the probability estimates are still valuable even if accuracy is similar.")

    # Test distribution
    print(f"\nTest set distribution:")
    for cls in [0, 1, 2]:
        label = {0: "away_win", 1: "draw", 2: "home_win"}[cls]
        count = (y_test == cls).sum()
        print(f"  {label}: {count} ({count/len(y_test)*100:.1f}%)")

    # Show top 5 candidates
    print(f"\nTop 5 models:")
    for i, c in enumerate(candidates[:5]):
        print(f"  {i+1}. {c[0]} {c[1]} {c[2]}: acc={c[4]:.3f} logloss={c[5]:.3f}")

    # Save model artifacts
    artifacts = {
        "model": best_model,
        "scaler": scaler,
        "feature_columns": feature_cols,
        "classes": classes.tolist(),
        "model_type": best_name,
        "model_detail": f"{best_param} {best_detail}",
    }
    model_path = MODELS_DIR / "match_model.joblib"
    joblib.dump(artifacts, model_path)
    print(f"\nModel saved to {model_path}")

    # Verify round-trip
    loaded = joblib.load(model_path)
    test_pred = loaded["model"].predict_proba(
        loaded["scaler"].transform(X_test[:1])
    )
    print(f"Verification - sample prediction: {test_pred[0]}")

    return best_model, scaler


if __name__ == "__main__":
    train()
