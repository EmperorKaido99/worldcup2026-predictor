"""
Train the match outcome prediction model (P0).
Multinomial Logistic Regression with calibration.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss
from sklearn.preprocessing import StandardScaler
from pathlib import Path
import joblib

from src.features import build_feature_table, get_feature_columns, load_data

MODELS_DIR = Path(__file__).parent.parent / "models"


def naive_baseline_accuracy(y_true, elo_diff):
    """Baseline: higher Elo team wins (home if equal)."""
    preds = np.where(elo_diff > 0, 2, np.where(elo_diff < 0, 0, 2))
    return accuracy_score(y_true, preds)


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

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train calibrated logistic regression
    base_model = LogisticRegression(
        max_iter=1000,
        C=1.0,
        solver="lbfgs",
        random_state=42,
    )
    model = CalibratedClassifierCV(base_model, cv=5, method="isotonic")
    model.fit(X_train_scaled, y_train)

    # Evaluate
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)

    accuracy = accuracy_score(y_test, y_pred)
    logloss = log_loss(y_test, y_proba)
    baseline_acc = naive_baseline_accuracy(y_test, test_df["elo_diff"].values)

    # Per-class Brier scores
    classes = model.classes_
    print(f"\n{'='*50}")
    print(f"MODEL EVALUATION")
    print(f"{'='*50}")
    print(f"Accuracy:          {accuracy:.3f}")
    print(f"Baseline accuracy: {baseline_acc:.3f} (higher-Elo-wins)")
    print(f"Log loss:          {logloss:.3f}")

    for i, cls in enumerate(classes):
        label = {0: "away_win", 1: "draw", 2: "home_win"}[cls]
        bs = brier_score_loss((y_test == cls).astype(int), y_proba[:, i])
        print(f"Brier score ({label}): {bs:.3f}")

    beats_baseline = accuracy >= baseline_acc
    print(f"\nBeats baseline: {'YES' if beats_baseline else 'NO'}")

    # Test distribution
    print(f"\nTest set distribution:")
    for cls in [0, 1, 2]:
        label = {0: "away_win", 1: "draw", 2: "home_win"}[cls]
        count = (y_test == cls).sum()
        print(f"  {label}: {count} ({count/len(y_test)*100:.1f}%)")

    # Save model artifacts
    artifacts = {
        "model": model,
        "scaler": scaler,
        "feature_columns": feature_cols,
        "classes": classes.tolist(),
    }
    model_path = MODELS_DIR / "match_model.joblib"
    joblib.dump(artifacts, model_path)
    print(f"\nModel saved to {model_path}")

    # Verify round-trip
    loaded = joblib.load(model_path)
    test_pred = loaded["model"].predict_proba(
        loaded["scaler"].transform(X_test[:1])
    )
    print(f"Verification — sample prediction: {test_pred[0]}")

    return model, scaler


if __name__ == "__main__":
    train()
