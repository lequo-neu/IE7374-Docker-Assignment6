import json
import os

import pytest

from app.train import CLASSES, FEATURES, MIN_ACCURACY, build_pipeline, load_penguins, train

ADELIE = ["Adelie", "Torgersen", "39.1", "18.7", "181", "3750", "male", "2007"]
GENTOO = ["Gentoo", "Biscoe", "46.1", "13.2", "211", "4500", "female", "2007"]
EMPTY = ["Adelie", "Torgersen", "NA", "NA", "NA", "NA", "NA", "2007"]


# ----------------- Loading ----------------- #
def test_rows_with_missing_measurements_are_dropped(write_csv):
    X, y, dropped = load_penguins(write_csv([ADELIE, EMPTY, GENTOO]))
    assert dropped == 1
    assert X == [[39.1, 18.7, 181.0, 3750.0], [46.1, 13.2, 211.0, 4500.0]]
    assert y == [CLASSES.index("Adelie"), CLASSES.index("Gentoo")]


def test_unknown_species_is_rejected(write_csv):
    with pytest.raises(ValueError, match="Unknown species"):
        load_penguins(write_csv([ADELIE, ["Emperor"] + ADELIE[1:]]))


def test_missing_column_is_rejected(write_csv):
    header = ["species", "island", "bill_length_mm", "bill_depth_mm", "flipper_length_mm", "sex", "year"]
    with pytest.raises(ValueError, match="body_mass_g"):
        load_penguins(write_csv([ADELIE[:5] + ADELIE[6:]], header=header))


# ----------------- Training ----------------- #
def test_training_writes_model_and_metadata(model_dir):
    assert os.path.exists(os.path.join(model_dir, "model.joblib"))
    with open(os.path.join(model_dir, "metadata.json")) as f:
        metadata = json.load(f)
    assert metadata["dataset"] == "Palmer Penguins"
    assert metadata["features"] == FEATURES
    assert metadata["classes"] == CLASSES
    assert metadata["test_accuracy"] >= MIN_ACCURACY
    assert metadata["rows_used"] + metadata["rows_dropped_for_missing_values"] == 344


def test_scaler_is_part_of_the_saved_pipeline():
    assert list(build_pipeline().named_steps) == ["scaler", "model"]


def test_training_is_rejected_below_the_minimum(tmp_path):
    with pytest.raises(ValueError, match="below the minimum"):
        train(str(tmp_path), min_accuracy=1.01)
    assert not os.path.exists(tmp_path / "model.joblib")
