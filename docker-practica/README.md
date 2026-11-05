# Proyecto base — Modelo de riesgo crediticio (SIN dockerizar)

**Módulo:** ML-Ops y Puesta en Producción · Clase 3
**Ejercicio:** "Del script al servicio: dockeriza el modelo de crédito"

## Situación actual

El equipo de ciencia de datos de un banco entrenó un modelo que predice si un
solicitante de crédito será **moroso** (1) o **cumplirá** sus pagos (0).
Hoy el modelo solo se puede usar ejecutando un script en la laptop del data
scientist. Tu misión (ver el enunciado del ejercicio) es convertirlo en un
**servicio contenerizado** que cualquier sistema pueda consumir por API.

## Contenido

| Archivo | Qué es | ¿Se modifica? |
|---|---|---|
| `entrenar.py` | Entrena el modelo y genera `modelo_credito.joblib` | No |
| `predecir_local.py` | Cómo se consume HOY el modelo (script manual) | No (queda obsoleto al final) |
| `requirements.txt` | Dependencias actuales | Sí (agregarás las de la API) |

## Para empezar

> ⚠️ **Usa Python 3.10–3.12** (recomendado: 3.11, la misma versión de la
> imagen Docker del ejercicio). Con Python 3.13/3.14 pip no encuentra wheels
> de estas versiones de scikit-learn y pydantic e intenta compilarlas desde
> el fuente ("Failed to build installable wheels") — y falla.
> Verifica con `python3 --version`; si tienes uno muy nuevo, crea el venv
> apuntando a la versión correcta: `python3.11 -m venv .venv`.

```bash
python3.11 -m venv .venv         # o python -m venv .venv si tu python es 3.10-3.12
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python entrenar.py               # genera modelo_credito.joblib
python predecir_local.py         # así funciona hoy… tu trabajo es superarlo
```

## Las 5 características del modelo (en este orden)

1. `ingreso_mensual` (USD)
2. `deuda_actual` (USD)
3. `antiguedad_laboral` (años)
4. `monto_solicitado` (USD)
5. `plazo_meses`

El resto de las instrucciones está en el enunciado del ejercicio.
