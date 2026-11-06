"""API de inferencia. Carga el modelo desde el Model Registry de MLflow al arrancar."""
import logging
import os
import threading
import time
from contextlib import asynccontextmanager

import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException
from mlflow import MlflowClient
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("adult-api")

MODEL_URI = os.environ.get("MODEL_URI", "models:/adult-income-classifier@production")
POD = os.environ.get("POD_NAME") or os.environ.get("HOSTNAME", "desconocido")
ESPERA_REINTENTO = 5


class Estado:
    modelo = None
    nombre = None
    alias = None
    version = None
    run_id = None
    error = None


estado = Estado()


def separar_uri(uri: str) -> tuple[str, str]:
    """Convierte models:/nombre@alias en (nombre, alias)."""
    referencia = uri.removeprefix("models:/")
    if "@" not in referencia:
        raise ValueError(f"MODEL_URI debe tener la forma models:/nombre@alias: {uri}")
    nombre, alias = referencia.split("@", 1)
    return nombre, alias


def cargar_modelo() -> None:
    # El alias se resuelve una sola vez, para que la versión expuesta y la versión
    # cargada sean la misma aunque alguien mueva el alias durante la descarga.
    nombre, alias = separar_uri(MODEL_URI)
    version = MlflowClient().get_model_version_by_alias(nombre, alias)
    modelo = mlflow.sklearn.load_model(f"models:/{nombre}/{version.version}")
    # Con n_jobs=-1 se lanzaría un hilo por cada CPU del nodo, no del pod.
    clasificador = modelo.named_steps["clasificador"]
    if hasattr(clasificador, "n_jobs"):
        clasificador.n_jobs = 1
    estado.nombre, estado.alias = nombre, alias
    estado.version, estado.run_id = version.version, version.run_id
    estado.modelo = modelo
    estado.error = None
    log.info("Modelo cargado: %s v%s run=%s", nombre, version.version, version.run_id)


def cargar_con_reintentos() -> None:
    # Si MLflow no está disponible, el pod queda NotReady y no entra en CrashLoopBackOff.
    while estado.modelo is None:
        try:
            cargar_modelo()
        except Exception as exc:
            estado.error = f"{type(exc).__name__}: {exc}"
            log.warning("No se pudo cargar el modelo: %s", estado.error)
            time.sleep(ESPERA_REINTENTO)


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    threading.Thread(target=cargar_con_reintentos, daemon=True).start()
    yield


app = FastAPI(
    title="API de ingresos (UCI Adult)",
    description="Predice si una persona gana más de 50K al año.",
    version="0.1.0",
    lifespan=ciclo_de_vida,
)


class Solicitud(BaseModel):
    age: int = Field(ge=0, le=120, description="Edad (años)")
    workclass: str = Field(min_length=1, description="Tipo de empleo")
    education: str = Field(min_length=1, description="Nivel educativo")
    marital_status: str = Field(min_length=1, description="Estado civil")
    occupation: str = Field(min_length=1, description="Ocupación")
    relationship: str = Field(min_length=1, description="Rol en el hogar")
    capital_gain: float = Field(ge=0, description="Ganancia de capital")
    capital_loss: float = Field(ge=0, description="Pérdida de capital")
    hours_per_week: int = Field(ge=0, le=168, description="Horas de trabajo por semana")


@app.get("/health")
def health():
    """Liveness: no consulta MLflow, para que su caída no reinicie los pods."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness: el pod solo recibe tráfico con el modelo en memoria."""
    if estado.modelo is None:
        raise HTTPException(503, detail={"status": "cargando", "error": estado.error})
    return {"status": "ready"}


@app.get("/info")
def info():
    return {
        "modelo": estado.nombre,
        "alias": estado.alias,
        "version_modelo": estado.version,
        "run_id": estado.run_id,
        "model_uri": MODEL_URI,
        "cargado": estado.modelo is not None,
        "pod": POD,
    }


@app.post("/predecir")
def predecir(solicitud: Solicitud):
    if estado.modelo is None:
        raise HTTPException(503, detail="El modelo aún no está cargado.")
    X = pd.DataFrame([solicitud.model_dump()])
    return {
        "prediccion": int(estado.modelo.predict(X)[0]),
        "probabilidad": float(estado.modelo.predict_proba(X)[0][1]),
        "modelo": estado.nombre,
        "version_modelo": estado.version,
        "run_id": estado.run_id,
        "pod": POD,
    }
