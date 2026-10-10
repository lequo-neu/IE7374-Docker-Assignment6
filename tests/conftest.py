import pytest

from app.main import create_app
from app.train import train


@pytest.fixture(scope="session")
def model_dir(tmp_path_factory):
    """Train the real model once into a temporary folder for the whole test run."""
    path = tmp_path_factory.mktemp("model")
    train(str(path))
    return str(path)


@pytest.fixture
def client(model_dir):
    return create_app(model_dir).test_client()
