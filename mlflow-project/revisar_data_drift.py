"""Control de data drift. Termina con exit 0 (VERDE) o exit 1 (ROJO).

    python revisar_data_drift.py --lote lotes/mismo_origen.csv
    python revisar_data_drift.py --lote lotes/verano.csv
    python revisar_data_drift.py --falsas-alarmas 300
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from datos import particiones
from drift import ALFA_KS, TAMANO_LOTE, UMBRAL_PSI, comparar_lote, revisar

REPORTES = Path(__file__).parent / "reportes"


def imprimir_tabla(filas: list[dict]) -> None:
    print(f"{'variable':<16}{'prueba':<14}{'estadistico':>12}  {'alerta si':<12}estado")
    for fila in filas:
        condicion = f"p < {ALFA_KS}" if fila["tipo"] == "numerica" else f"PSI > {UMBRAL_PSI}"
        estado = "ROJO" if fila["drift"] else "verde"
        print(f"{fila['variable']:<16}{fila['prueba']:<14}"
              f"{fila['estadistico']:>12.3g}  {condicion:<12}{estado}")


def revisar_lote(ruta: Path) -> int:
    train, _, _ = particiones()
    filas = comparar_lote(train, pd.read_csv(ruta))
    imprimir_tabla(filas)
    culpables = [fila["variable"] for fila in filas if fila["drift"]]
    print()
    if culpables:
        print(f"ESTADO: ROJO. Variables con drift: {', '.join(culpables)}")
    else:
        print("ESTADO: VERDE. Ninguna variable supera su umbral.")
    print(f"Acción sin alarma de la métrica: {revisar(bool(culpables), False)}")
    REPORTES.mkdir(exist_ok=True)
    (REPORTES / f"data_drift_{ruta.stem}.json").write_text(json.dumps(filas, indent=2))
    return 1 if culpables else 0


def medir_falsas_alarmas(lotes: int) -> int:
    """Mide cuántos lotes limpios saldrían en rojo con los umbrales elegidos."""
    train, _, produccion = particiones()
    rng = np.random.default_rng(1)
    rojos = {"ks": 0, "psi": 0, "cualquiera": 0}
    psi_maximo = 0.0
    for _ in range(lotes):
        lote = produccion.sample(TAMANO_LOTE, random_state=int(rng.integers(1_000_000_000)))
        filas = comparar_lote(train, lote)
        ks = any(f["drift"] for f in filas if f["tipo"] == "numerica")
        psi = any(f["drift"] for f in filas if f["tipo"] == "categorica")
        rojos["ks"] += ks
        rojos["psi"] += psi
        rojos["cualquiera"] += ks or psi
        psi_maximo = max(psi_maximo, *(f["estadistico"] for f in filas if f["tipo"] == "categorica"))
    resultado = {
        "lotes": lotes,
        "tamano_lote": TAMANO_LOTE,
        "tasa_ks": rojos["ks"] / lotes,
        "tasa_psi": rojos["psi"] / lotes,
        "tasa_total": rojos["cualquiera"] / lotes,
        "psi_maximo_en_lotes_limpios": psi_maximo,
    }
    REPORTES.mkdir(exist_ok=True)
    (REPORTES / "falsas_alarmas.json").write_text(json.dumps(resultado, indent=2))
    print(json.dumps(resultado, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--lote", type=Path, help="CSV con las variables de entrada")
    grupo.add_argument("--falsas-alarmas", type=int, metavar="N", help="Lotes limpios a medir")
    args = parser.parse_args()
    return revisar_lote(args.lote) if args.lote else medir_falsas_alarmas(args.falsas_alarmas)


if __name__ == "__main__":
    sys.exit(main())
