import pytest

from app.main import create_app

ADELIE = {"bill_length_mm": 39.1, "bill_depth_mm": 18.7, "flipper_length_mm": 181, "body_mass_g": 3750}
CHINSTRAP = {"bill_length_mm": 46.5, "bill_depth_mm": 17.9, "flipper_length_mm": 192, "body_mass_g": 3500}
GENTOO = {"bill_length_mm": 46.1, "bill_depth_mm": 13.2, "flipper_length_mm": 211, "body_mass_g": 4500}


# ----------------- Health and page ----------------- #
def test_health_reports_the_model(client):
    body = client.get("/health").get_json()
    assert body["status"] == "ok"
    assert body["dataset"] == "Palmer Penguins"
    assert body["test_accuracy"] >= 0.9
    assert "image_revision" in body


def test_home_page_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Penguin Species Classifier" in response.data


def test_missing_model_fails_at_startup(tmp_path):
    with pytest.raises(FileNotFoundError, match="Run python -m app.train"):
        create_app(str(tmp_path))


# ----------------- Predictions ----------------- #
@pytest.mark.parametrize("sample, expected", [
    (ADELIE, "Adelie"), (CHINSTRAP, "Chinstrap"), (GENTOO, "Gentoo"),
])
def test_predicts_each_species_from_raw_measurements(client, sample, expected):
    body = client.post("/predict", json=sample).get_json()
    assert body["predicted_species"] == expected
    assert sum(body["probabilities"].values()) == pytest.approx(1.0, abs=1e-3)


def test_form_data_is_accepted(client):
    form = {k: str(v) for k, v in ADELIE.items()}
    assert client.post("/predict", data=form).get_json()["predicted_species"] == "Adelie"


# ----------------- Invalid input ----------------- #
def test_missing_field_returns_400_and_names_it(client):
    response = client.post("/predict", json={"bill_length_mm": 39.1})
    assert response.status_code == 400
    assert "body_mass_g" in response.get_json()["error"]


@pytest.mark.parametrize("bad_value", ["abc", -1, 0, "nan"])
def test_invalid_value_returns_400(client, bad_value):
    response = client.post("/predict", json={**ADELIE, "flipper_length_mm": bad_value})
    assert response.status_code == 400
    assert "flipper_length_mm" in response.get_json()["error"]


def test_get_on_predict_is_not_allowed(client):
    assert client.get("/predict").status_code == 405
