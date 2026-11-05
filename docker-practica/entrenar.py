# =============================================================================
# entrenar.py — Entrena el modelo de riesgo crediticio y lo guarda en disco
# Módulo: ML-Ops y Puesta en Producción · Clase 3 · Ejercicio "Del script al servicio"
#
# ESTE ARCHIVO NO SE MODIFICA. Su único propósito es dejar el artefacto
# 'modelo_credito.joblib' en disco. Ese artefacto es el que tu API cargará
# y el que empaquetarás dentro de la imagen de Docker.
#
# USO:  python entrenar.py
# =============================================================================
import random

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

N = 3000

# -----------------------------------------------------------------------------
# Dataset sintético de solicitudes de crédito. Cada fila es un solicitante
# con 5 características (en este orden — tu API debe respetarlo):
#   1. ingreso_mensual      (USD)
#   2. deuda_actual         (USD)
#   3. antiguedad_laboral   (años en el empleo actual)
#   4. monto_solicitado     (USD)
#   5. plazo_meses          (duración del crédito)
# La etiqueta es 1 = "moroso" (incumplió el pago), 0 = "cumplió".
# -----------------------------------------------------------------------------
ingreso_mensual = np.random.gamma(shape=4.0, scale=400.0, size=N) + 300
deuda_actual = np.random.gamma(shape=2.0, scale=900.0, size=N)
antiguedad_laboral = np.random.exponential(scale=5.0, size=N).clip(0, 35)
monto_solicitado = np.random.gamma(shape=2.5, scale=2200.0, size=N) + 500
plazo_meses = np.random.choice([6, 12, 18, 24, 36, 48, 60], size=N)

# Regla generadora (oculta para el modelo): la morosidad sube cuando la carga
# financiera (deuda + cuota) es alta respecto al ingreso, y baja con la
# estabilidad laboral. Se añade ruido para que el problema no sea trivial.
cuota_mensual = monto_solicitado / plazo_meses
carga = (deuda_actual * 0.04 + cuota_mensual) / ingreso_mensual
score_riesgo = 2.2 * carga - 0.06 * antiguedad_laboral + np.random.normal(0, 0.35, N)
y = (score_riesgo > 0.55).astype(int)

X = np.column_stack([
    ingreso_mensual,
    deuda_actual,
    antiguedad_laboral,
    monto_solicitado,
    plazo_meses,
])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=SEED, stratify=y
)

modelo = RandomForestClassifier(n_estimators=150, max_depth=10, random_state=SEED)
modelo.fit(X_train, y_train)
acc = accuracy_score(y_test, modelo.predict(X_test))
print(f"[train] muestras={N}  morosos={y.mean():.1%}  accuracy={acc:.4f}")

joblib.dump(modelo, "modelo_credito.joblib")
print("[train] modelo_credito.joblib guardado — este es el artefacto a servir")
