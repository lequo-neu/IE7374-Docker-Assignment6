import json
import os

import pytest

from app.train import CLASSES, FEATURES, MIN_ACCURACY, build_pipeline, train


def test_training_writes_model_and_metadata(model_dir):
    assert os.path.exists(os.path.join(model_dir, "model.joblib"))
    with open(os.path.join(model_dir, "metadata.json")) as f:
        metadata = json.load(f)
    assert metadata["features"] == FEATURES
    assert metadata["classes"] == CLASSES
    assert metadata["test_accuracy"] >= MIN_ACCURACY


def test_scaler_is_part_of_the_saved_pipeline():
    assert list(build_pipeline().named_steps) == ["scaler", "model"]


def test_training_is_rejected_below_the_minimum(tmp_path):
    with pytest.raises(ValueError, match="below the minimum"):
        train(str(tmp_path), min_accuracy=1.01)
    assert not os.path.exists(tmp_path / "model.joblib")
