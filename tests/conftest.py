import csv

import pytest

from app.main import create_app
from app.train import train


@pytest.fixture(scope="session")
def model_dir(tmp_path_factory):
    """Train the real model on data/penguins.csv once for the whole test run."""
    path = tmp_path_factory.mktemp("model")
    train(str(path))
    return str(path)


@pytest.fixture
def client(model_dir):
    return create_app(model_dir).test_client()


@pytest.fixture
def write_csv(tmp_path):
    """Write a small penguins style file with the given rows and return its path."""
    def _write(rows, header=None):
        header = header or ["species", "island", "bill_length_mm", "bill_depth_mm",
                            "flipper_length_mm", "body_mass_g", "sex", "year"]
        path = tmp_path / "penguins.csv"
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        return str(path)
    return _write
