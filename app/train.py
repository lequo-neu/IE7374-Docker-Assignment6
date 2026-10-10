"""
Train the Iris classifier that ships inside the container image.

This runs during `docker build`, so every image carries a model that was
trained and checked in the same environment it will be served from. If the
model misses the minimum accuracy, the script exits with an error and the
build stops.

Usage:
    python -m app.train --output-dir model
"""

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone

import joblib
import sklearn
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["sepal_length", "sepal_width", "petal_length", "petal_width"]
CLASSES = ["Setosa", "Versicolor", "Virginica"]
RANDOM_STATE = 42
MIN_ACCURACY = 0.9


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


def train(output_dir: str, min_accuracy: float = MIN_ACCURACY) -> dict:
    """
    Train, evaluate and save the model with a metadata file next to it.

    Args:
        output_dir (str): Folder for model.joblib and metadata.json.
        min_accuracy (float): Lowest test accuracy allowed to ship.
    Returns:
        dict: The metadata that was written.
    Raises:
        ValueError: If test accuracy is below min_accuracy.
    """
    X, y = load_iris(return_X_y=True)
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
        "model": "StandardScaler + LogisticRegression",
        "features": FEATURES,
        "classes": CLASSES,
        "test_accuracy": round(accuracy, 4),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Test accuracy: {accuracy:.4f} (minimum {min_accuracy})")
    print(f"Model and metadata saved to {output_dir}")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the Iris classifier")
    parser.add_argument("--output-dir", default="model")
    args = parser.parse_args()
    try:
        train(args.output_dir)
    except ValueError as e:
        print(f"Training rejected: {e}", file=sys.stderr)
        sys.exit(1)
