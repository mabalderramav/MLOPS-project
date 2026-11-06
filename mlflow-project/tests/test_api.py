import numpy as np
import pytest
from fastapi.testclient import TestClient

import api

SOLICITUD = {
    "age": 40, "workclass": "Private", "education": "Bachelors",
    "marital_status": "Married-civ-spouse", "occupation": "Exec-managerial",
    "relationship": "Husband", "capital_gain": 0, "capital_loss": 0, "hours_per_week": 45,
}


class ModeloFalso:
    def predict(self, X):
        return np.array([1])

    def predict_proba(self, X):
        return np.array([[0.2, 0.8]])


@pytest.fixture
def cliente(monkeypatch):
    # Sin "with TestClient", no se ejecuta el arranque y no se contacta a MLflow.
    monkeypatch.setattr(api, "estado", api.Estado())
    return TestClient(api.app)


def test_sin_modelo_no_esta_listo_pero_sigue_vivo(cliente):
    assert cliente.get("/health").status_code == 200
    assert cliente.get("/ready").status_code == 503
    assert cliente.post("/predecir", json=SOLICITUD).status_code == 503


def test_prediccion_devuelve_trazabilidad(cliente):
    api.estado.modelo = ModeloFalso()
    api.estado.nombre, api.estado.version, api.estado.run_id = "m", "2", "abc"
    assert cliente.get("/ready").status_code == 200
    cuerpo = cliente.post("/predecir", json=SOLICITUD).json()
    assert cuerpo["prediccion"] == 1
    assert cuerpo["probabilidad"] == 0.8
    assert (cuerpo["version_modelo"], cuerpo["run_id"]) == ("2", "abc")
    assert cuerpo["pod"]


def test_valida_la_entrada(cliente):
    api.estado.modelo = ModeloFalso()
    assert cliente.post("/predecir", json={**SOLICITUD, "age": -1}).status_code == 422
    sin_campo = {k: v for k, v in SOLICITUD.items() if k != "occupation"}
    assert cliente.post("/predecir", json=sin_campo).status_code == 422


def test_uri_debe_tener_alias():
    assert api.separar_uri("models:/m@production") == ("m", "production")
    with pytest.raises(ValueError):
        api.separar_uri("/ruta/al/modelo")
