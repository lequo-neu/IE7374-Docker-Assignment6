"""
Train the penguin species classifier that ships inside the container image.

This runs during `docker build`, so every image carries a model that was
trained and checked in the same environment it will be served from. If the
model misses the minimum accuracy, the script exits with an error and the
build stops.

Usage:
    python -m app.train --data data/penguins.csv --output-dir model
"""

import argparse
import csv
import json
import os
import platform
import sys
from datetime import datetime, timezone

import joblib
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "penguins.csv")
FEATURES = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
CLASSES = ["Adelie", "Chinstrap", "Gentoo"]
TARGET = "species"
RANDOM_STATE = 42
MIN_ACCURACY = 0.9


def load_penguins(path: str = DATA_PATH) -> tuple:
    """
    Read the Palmer Penguins CSV with the standard library csv module.

    Using csv instead of pandas keeps pandas out of the image. Rows where any
    measurement is missing are dropped, because the model needs all four.

    Args:
        path (str): Path to penguins.csv.
    Returns:
        tuple: (X as a list of four float lists, y as a list of class indices,
            number of rows dropped for missing values)
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If a column is missing or a species is not one of CLASSES.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found")
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in FEATURES + [TARGET] if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        X, y, dropped = [], [], 0
        for row in reader:
            if any(row[c] in ("", "NA") for c in FEATURES):
                dropped += 1
                continue
            if row[TARGET] not in CLASSES:
                raise ValueError(f"Unknown species {row[TARGET]!r}, expected one of {CLASSES}")
            X.append([float(row[c]) for c in FEATURES])
            y.append(CLASSES.index(row[TARGET]))
    return X, y, dropped


def build_pipeline() -> Pipeline:
    """
    Scaler and classifier in one object.

    Keeping the scaler inside the pipeline means the exact same scaling is
    applied at prediction time. The original lab scaled the training data but
    sent raw values to the model when serving.
    """
    return Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
    ])


def train(output_dir: str, data_path: str = DATA_PATH, min_accuracy: float = MIN_ACCURACY) -> dict:
    """
    Train, evaluate and save the model with a metadata file next to it.

    Args:
        output_dir (str): Folder for model.joblib and metadata.json.
        data_path (str): Path to penguins.csv.
        min_accuracy (float): Lowest test accuracy allowed to ship.
    Returns:
        dict: The metadata that was written.
    Raises:
        ValueError: If test accuracy is below min_accuracy.
    """
    X, y, dropped = load_penguins(data_path)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    pipeline = build_pipeline().fit(X_train, y_train)
    accuracy = float(accuracy_score(y_test, pipeline.predict(X_test)))
    if accuracy < min_accuracy:
        raise ValueError(f"Test accuracy {accuracy:.4f} is below the minimum of {min_accuracy}")

    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(pipeline, os.path.join(output_dir, "model.joblib"))
    metadata = {
        "dataset": "Palmer Penguins",
        "model": "StandardScaler + LogisticRegression",
        "features": FEATURES,
        "classes": CLASSES,
        "test_accuracy": round(accuracy, 4),
        "rows_used": len(X),
        "rows_dropped_for_missing_values": dropped,
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Rows used: {len(X)}, dropped for missing values: {dropped}")
    print(f"Test accuracy: {accuracy:.4f} (minimum {min_accuracy})")
    print(f"Model and metadata saved to {output_dir}")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the penguin species classifier")
    parser.add_argument("--data", default=DATA_PATH)
    parser.add_argument("--output-dir", default="model")
    args = parser.parse_args()
    try:
        train(args.output_dir, data_path=args.data)
    except ValueError as e:
        print(f"Training rejected: {e}", file=sys.stderr)
        sys.exit(1)
