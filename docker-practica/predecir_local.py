# =============================================================================
# predecir_local.py — Así consume HOY el área de créditos el modelo :(
# Módulo: ML-Ops y Puesta en Producción · Clase 3 · Ejercicio "Del script al servicio"
#
# Este script representa la situación ACTUAL del proyecto: para evaluar un
# solicitante, un analista abre una terminal, edita estos valores a mano y
# ejecuta el script. Funciona… en la laptop del data scientist.
#
# Problemas (los mismos de la diapositiva "en mi máquina funciona"):
#   - Nadie más puede usarlo sin instalar Python y las librerías exactas.
#   - No se puede integrar con el sistema web de créditos del banco.
#   - Cada analista tiene una versión distinta del entorno.
#
# TU TRABAJO EN ESTE EJERCICIO: reemplazar este script por un servicio
# contenerizado (API REST + Docker). Este archivo NO forma parte de la
# entrega final: cuando tu API funcione, este script queda obsoleto.
#
# USO:  python predecir_local.py   (requiere haber ejecutado antes entrenar.py)
# =============================================================================
import joblib
import numpy as np

modelo = joblib.load("modelo_credito.joblib")

# El analista edita estos valores a mano para cada solicitante… 😱
solicitante = {
    "ingreso_mensual": 1800.0,      # USD
    "deuda_actual": 3500.0,         # USD
    "antiguedad_laboral": 4.0,      # años
    "monto_solicitado": 9000.0,     # USD
    "plazo_meses": 24,
}

X = np.array([[
    solicitante["ingreso_mensual"],
    solicitante["deuda_actual"],
    solicitante["antiguedad_laboral"],
    solicitante["monto_solicitado"],
    solicitante["plazo_meses"],
]])

prediccion = int(modelo.predict(X)[0])
probabilidad = float(modelo.predict_proba(X)[0][1])

print(f"Solicitante: {solicitante}")
print(f"¿Moroso?: {'SÍ' if prediccion == 1 else 'NO'}  (prob. de mora = {probabilidad:.2%})")
