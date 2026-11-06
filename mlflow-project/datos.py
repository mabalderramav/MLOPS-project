"""Descarga, verifica y limpia UCI Adult, y genera las particiones del proyecto."""
import hashlib
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

URL = "https://archive.ics.uci.edu/static/public/2/adult.zip"
SHA256 = "7537312dd56c2b98035880805ce99e68183a30ee468aa5329d6df0fbb3cc21bb"
CARPETA = Path(__file__).parent / "datos"
SEMILLA = 42

COLUMNAS = [
    "age", "workclass", "fnlwgt", "education", "education_num", "marital_status",
    "occupation", "relationship", "race", "sex", "capital_gain", "capital_loss",
    "hours_per_week", "native_country", "income",
]
NUMERICAS = ["age", "capital_gain", "capital_loss", "hours_per_week"]
CATEGORICAS = ["workclass", "education", "marital_status", "occupation", "relationship"]
VARIABLES = NUMERICAS + CATEGORICAS
OBJETIVO = "y"


def descargar() -> Path:
    """Descarga el zip una sola vez y falla si el contenido no es el esperado."""
    CARPETA.mkdir(exist_ok=True)
    archivo = CARPETA / "adult.zip"
    if not archivo.exists():
        urllib.request.urlretrieve(URL, archivo)
    obtenido = hashlib.sha256(archivo.read_bytes()).hexdigest()
    if obtenido != SHA256:
        raise ValueError(f"SHA-256 inesperado en {archivo}: {obtenido}")
    with zipfile.ZipFile(archivo) as z:
        z.extractall(CARPETA, members=["adult.data", "adult.test"])
    return CARPETA


def cargar() -> pd.DataFrame:
    """Une adult.data y adult.test, y deja el objetivo y las variables listas."""
    carpeta = descargar()
    opciones = {"names": COLUMNAS, "skipinitialspace": True, "na_values": "?"}
    entrenamiento = pd.read_csv(carpeta / "adult.data", **opciones)
    # La primera línea de adult.test es un comentario, no un registro.
    prueba = pd.read_csv(carpeta / "adult.test", skiprows=1, **opciones)
    df = pd.concat([entrenamiento, prueba], ignore_index=True).dropna(subset=["income"])
    # Se quitan duplicados antes de descartar columnas: dos personas distintas
    # pueden coincidir en las 9 variables usadas sin ser el mismo registro.
    df = df.drop_duplicates().reset_index(drop=True)
    # En adult.test las etiquetas terminan en punto: ">50K."
    df[OBJETIVO] = df["income"].str.rstrip(".").eq(">50K").astype(int)
    df[CATEGORICAS] = df[CATEGORICAS].fillna("Unknown")
    return df[VARIABLES + [OBJETIVO]]


def particiones() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Devuelve train (50 %), test (20 %) y produccion (30 %), estratificadas."""
    df = cargar()
    train, resto = train_test_split(
        df, train_size=0.5, random_state=SEMILLA, stratify=df[OBJETIVO]
    )
    test, produccion = train_test_split(
        resto, train_size=0.4, random_state=SEMILLA, stratify=resto[OBJETIVO]
    )
    return train, test, produccion


if __name__ == "__main__":
    train, test, produccion = particiones()
    print(f"train={len(train)} test={len(test)} produccion={len(produccion)}")
    print(f"positivos={train[OBJETIVO].mean():.3f} sha256={SHA256}")
