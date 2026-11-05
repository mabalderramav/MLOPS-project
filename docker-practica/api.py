import joblib
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field

modelo = joblib.load("modelo_credito.joblib")

app = FastAPI(
    title="API de riesgo crediticio",
    description="Modelo entrenado",
    version="1.0.0"
)

class Solicitante(BaseModel):
    ingreso_mensual: float = Field(gt=0, description="Ingreso mensual (USD)")
    deuda_actual: float = Field(ge=0, description="Deuda actual (USD)")
    antiguedad_laboral: float = Field(ge=0, description="Antiguedad laboral (anios)")
    monto_solicitado: float = Field(gt=0, description="Monto solicitado (USD)")
    plazo_meses: int = Field(gt=0, description="Plazo del credito (meses)")
    
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predecir")
def predecir(solicitante: Solicitante):
    X = np.array([[solicitante.ingreso_mensual, solicitante.deuda_actual, solicitante.antiguedad_laboral, solicitante.monto_solicitado, solicitante.plazo_meses]])
    
    prediccion = int(modelo.predict(X)[0])
    probabilidad = float(modelo.predict_proba(X)[0][1])
    
    return {
        "moroso": prediccion,
        "probabilidad": probabilidad,
        "version_modelo": "1.0.0"
    }