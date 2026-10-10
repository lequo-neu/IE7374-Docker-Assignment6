import pytest

from app.main import create_app

SETOSA = {"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}
VERSICOLOR = {"sepal_length": 6.0, "sepal_width": 2.7, "petal_length": 4.5, "petal_width": 1.4}
VIRGINICA = {"sepal_length": 6.9, "sepal_width": 3.1, "petal_length": 5.8, "petal_width": 2.2}


# ----------------- Health and page ----------------- #
def test_health_reports_the_model(client):
    body = client.get("/health").get_json()
    assert body["status"] == "ok"
    assert body["test_accuracy"] >= 0.9
    assert "image_revision" in body


def test_home_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Iris Classifier" in response.data


def test_missing_model_fails_at_startup(tmp_path):
    with pytest.raises(FileNotFoundError, match="Run python -m app.train"):
        create_app(str(tmp_path))


# ----------------- Predictions ----------------- #
@pytest.mark.parametrize("sample, expected", [
    (SETOSA, "Setosa"), (VERSICOLOR, "Versicolor"), (VIRGINICA, "Virginica"),
])
def test_predicts_each_species_from_raw_measurements(client, sample, expected):
    body = client.post("/predict", json=sample).get_json()
    assert body["predicted_class"] == expected
    assert sum(body["probabilities"].values()) == pytest.approx(1.0, abs=1e-3)


def test_form_data_from_the_web_page_is_accepted(client):
    form = {k: str(v) for k, v in SETOSA.items()}
    assert client.post("/predict", data=form).get_json()["predicted_class"] == "Setosa"


# ----------------- Invalid input ----------------- #
def test_missing_field_returns_400_and_names_it(client):
    response = client.post("/predict", json={"sepal_length": 5.1})
    assert response.status_code == 400
    assert "petal_width" in response.get_json()["error"]


@pytest.mark.parametrize("bad_value", ["abc", -1, 0, "nan"])
def test_invalid_value_returns_400(client, bad_value):
    response = client.post("/predict", json={**SETOSA, "petal_length": bad_value})
    assert response.status_code == 400
    assert "petal_length" in response.get_json()["error"]


def test_get_on_predict_is_not_allowed(client):
    assert client.get("/predict").status_code == 405
