"""Detectores de drift, escenarios simulados y revisor, a partir de clase_drift.ipynb."""
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from datos import CATEGORICAS, NUMERICAS, OBJETIVO, SEMILLA

ALFA_KS = 0.05  # Regla de la clase; la tasa real de falsas alarmas se mide aparte.
UMBRAL_PSI = 0.25  # Valor convencional de "cambio importante".
SUAVIZADO_PSI = 1e-4
TAMANO_LOTE = 1000
LOTES_SOSTENIDOS = 3
CAIDA_MINIMA = 0.03  # Caída de ROC-AUC que el equipo considera relevante.
OTRAS = "__otras__"
OCUPACIONES_VERANO = ["Exec-managerial", "Prof-specialty"]
# Fracción de filas con la regla nueva en cada lote de la línea temporal.
FRACCIONES_REGLA_NUEVA = [0, 0, 0, 0, 0.25, 0.50, 0.75, 1, 1, 1, 1, 1]
ESCENARIOS = ["estable", "verano", "regla_nueva", "verano_fuerte"]


# ----- Detectores ------------------------------------------------------------
def psi(referencia: pd.Series, nuevo: pd.Series) -> float:
    """Índice de estabilidad poblacional. Las categorías nuevas se agrupan en OTRAS."""
    esperado = referencia.value_counts(normalize=True)
    nuevo = nuevo.where(nuevo.isin(esperado.index), OTRAS)
    categorias = esperado.index.union(pd.Index([OTRAS]))
    p = esperado.reindex(categorias, fill_value=0).to_numpy() + SUAVIZADO_PSI
    q = (
        nuevo.value_counts(normalize=True).reindex(categorias, fill_value=0).to_numpy()
        + SUAVIZADO_PSI
    )
    return float(((q - p) * np.log(q / p)).sum())


def comparar_lote(referencia: pd.DataFrame, lote: pd.DataFrame) -> list[dict]:
    """Compara cada variable de entrada del lote contra la referencia de entrenamiento."""
    filas = []
    for variable in NUMERICAS:
        prueba = ks_2samp(referencia[variable], lote[variable])
        filas.append({
            "variable": variable, "tipo": "numerica", "prueba": "KS (p-valor)",
            "estadistico": float(prueba.pvalue), "umbral": ALFA_KS,
            "drift": bool(prueba.pvalue < ALFA_KS),
        })
    for variable in CATEGORICAS:
        valor = psi(referencia[variable], lote[variable])
        filas.append({
            "variable": variable, "tipo": "categorica", "prueba": "PSI",
            "estadistico": valor, "umbral": UMBRAL_PSI, "drift": valor > UMBRAL_PSI,
        })
    return filas


def hay_data_drift(referencia: pd.DataFrame, lote: pd.DataFrame) -> bool:
    return any(fila["drift"] for fila in comparar_lote(referencia, lote))


# ----- Escenarios ------------------------------------------------------------
def pesos_verano(produccion: pd.DataFrame, edad: float = 2.0, ocupacion: float = 3.0):
    """Remuestrear filas reales mueve las entradas sin alterar la regla."""
    return (
        np.where(produccion["age"] > 45, edad, 1.0)
        * np.where(produccion["occupation"].isin(OCUPACIONES_VERANO), ocupacion, 1.0)
    )


def aplicar_regla_nueva(
    lote: pd.DataFrame, fraccion: float, rng: np.random.Generator
) -> pd.DataFrame:
    """Invierte la etiqueta en casados: las entradas no cambian, cambia la regla."""
    lote = lote.copy()
    elegidas = (lote["marital_status"] == "Married-civ-spouse").to_numpy() & (
        rng.random(len(lote)) < fraccion
    )
    lote[OBJETIVO] = np.where(elegidas, 1 - lote[OBJETIVO], lote[OBJETIVO])
    return lote


def linea_temporal(produccion: pd.DataFrame, escenario: str) -> list[tuple[pd.DataFrame, float]]:
    """Devuelve 12 lotes sucesivos de 1.000 filas, con la fracción de regla nueva."""
    if escenario in ("verano", "verano_fuerte"):
        edad, ocupacion = (2.0, 3.0) if escenario == "verano" else (6.0, 4.0)
        pesos = pesos_verano(produccion, edad, ocupacion)
        return [
            (produccion.sample(TAMANO_LOTE, weights=pesos, random_state=SEMILLA + i), 0.0)
            for i in range(12)
        ]
    mezclada = produccion.sample(frac=1, random_state=SEMILLA).reset_index(drop=True)
    fracciones = FRACCIONES_REGLA_NUEVA if escenario == "regla_nueva" else [0.0] * 12
    rng = np.random.default_rng(SEMILLA)
    return [
        (
            aplicar_regla_nueva(
                mezclada.iloc[i * TAMANO_LOTE:(i + 1) * TAMANO_LOTE], fraccion, rng
            ),
            fraccion,
        )
        for i, fraccion in enumerate(fracciones)
    ]


# ----- Criterio de reentrenamiento y revisor ----------------------------------
def umbral_metrica(valores_referencia: list[float]) -> tuple[float, float, float]:
    """Devuelve (mu, sigma, umbral) con umbral = mu - max(2 sigma, CAIDA_MINIMA)."""
    mu = float(np.mean(valores_referencia))
    sigma = float(np.std(valores_referencia, ddof=1))
    return mu, sigma, mu - max(2 * sigma, CAIDA_MINIMA)


def primer_sostenido(senales: list[bool], lotes: int = LOTES_SOSTENIDOS) -> int | None:
    """Número de lote (desde 1) en el que se cumplen `lotes` señales consecutivas."""
    seguidas = 0
    for numero, senal in enumerate(senales, start=1):
        seguidas = seguidas + 1 if senal else 0
        if seguidas == lotes:
            return numero
    return None


def revisar(data_drift: bool, alarma_metrica: bool) -> str:
    """Igual que revisar() del notebook: lo más grave primero."""
    if alarma_metrica:
        return "REENTRENAR"
    if data_drift:
        return "vigilar"
    return "todo bien"
