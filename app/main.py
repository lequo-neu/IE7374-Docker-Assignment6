"""
Flask service that serves the Iris model baked into the image.

Run in the container with gunicorn:
    gunicorn --bind 0.0.0.0:8080 "app.main:create_app()"
"""

import json
import math
import os

import joblib
from flask import Flask, jsonify, render_template, request

from app.train import CLASSES, FEATURES

DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model")


def load_artifacts(model_dir: str) -> tuple:
    """
    Load the model and its metadata.

    Args:
        model_dir (str): Folder written by app.train.
    Returns:
        tuple: (fitted pipeline, metadata dict)
    Raises:
        FileNotFoundError: If the model or metadata file is missing.
    """
    model_path = os.path.join(model_dir, "model.joblib")
    metadata_path = os.path.join(model_dir, "metadata.json")
    for path in (model_path, metadata_path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"{path} not found. Run python -m app.train first.")
    with open(metadata_path) as f:
        metadata = json.load(f)
    return joblib.load(model_path), metadata


def parse_features(payload: dict) -> list:
    """
    Read the four measurements from a JSON body or a form.

    Args:
        payload (dict): Request data.
    Returns:
        list: Four floats in the order of FEATURES.
    Raises:
        ValueError: With a message naming the field that is missing or invalid.
    """
    missing = [f for f in FEATURES if payload.get(f) in (None, "")]
    if missing:
        raise ValueError(f"Missing fields: {', '.join(missing)}")
    values = []
    for field in FEATURES:
        try:
            value = float(payload[field])
        except (TypeError, ValueError):
            raise ValueError(f"Field {field} must be a number") from None
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"Field {field} must be a positive number")
        values.append(value)
    return values


def create_app(model_dir: str = None) -> Flask:
    """
    Build the Flask app. The model is loaded once, when the app is created.

    Args:
        model_dir (str): Folder with model.joblib and metadata.json.
            Defaults to the MODEL_DIR environment variable, then ./model.
    Returns:
        Flask: The configured application.
    """
    model_dir = model_dir or os.environ.get("MODEL_DIR", DEFAULT_MODEL_DIR)
    model, metadata = load_artifacts(model_dir)
    app = Flask(__name__)

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify({
            "status": "ok",
            "model": metadata["model"],
            "test_accuracy": metadata["test_accuracy"],
            "trained_at": metadata["trained_at"],
            "image_revision": os.environ.get("GIT_SHA", "local"),
        })

    @app.post("/predict")
    def predict():
        payload = request.get_json(silent=True) or request.form.to_dict()
        try:
            values = parse_features(payload)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        probabilities = model.predict_proba([values])[0]
        best = max(range(len(CLASSES)), key=lambda i: probabilities[i])
        return jsonify({
            "predicted_class": CLASSES[best],
            "probabilities": {c: round(float(p), 4) for c, p in zip(CLASSES, probabilities)},
        })

    return app
