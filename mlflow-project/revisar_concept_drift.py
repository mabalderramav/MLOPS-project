"""Mide la métrica por lote, aplica el criterio de reentrenamiento y dibuja la línea temporal.

Termina con exit 1 si se dispara la alarma de reentrenamiento y con exit 0 si no.

    python revisar_concept_drift.py --escenario estable
    python revisar_concept_drift.py --escenario verano
    python revisar_concept_drift.py --escenario regla_nueva
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
from mlflow import MlflowClient
from sklearn.metrics import accuracy_score, roc_auc_score

from datos import OBJETIVO, SEMILLA, VARIABLES, particiones
from drift import (
    CAIDA_MINIMA,
    ESCENARIOS,
    LOTES_SOSTENIDOS,
    TAMANO_LOTE,
    hay_data_drift,
    linea_temporal,
    primer_sostenido,
    revisar,
    umbral_metrica,
)
from registrar import ALIAS, NOMBRE_MODELO

EXPERIMENTO_MONITOREO = "Adult Income Monitoring"
REPORTES = Path(__file__).parent / "reportes"
RETRASOS = [0, 3, 6]

SUPERFICIE = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_SECUNDARIO = "#52514e"
REJILLA = "#e6e5e0"
SERIE = "#2a78d6"
CRITICO = "#d03b3b"


def medir(modelo, lote) -> tuple[float, float]:
    probabilidad = modelo.predict_proba(lote[VARIABLES])[:, 1]
    return (
        float(roc_auc_score(lote[OBJETIVO], probabilidad)),
        float(accuracy_score(lote[OBJETIVO], modelo.predict(lote[VARIABLES]))),
    )


def referencia(modelo, test) -> tuple[list[float], float]:
    """ROC-AUC y accuracy de referencia, en lotes del mismo tamaño tomados del test."""
    mezclado = test.sample(frac=1, random_state=SEMILLA)
    lotes = [
        mezclado.iloc[i:i + TAMANO_LOTE]
        for i in range(0, len(mezclado) - TAMANO_LOTE + 1, TAMANO_LOTE)
    ]
    medidas = [medir(modelo, lote) for lote in lotes]
    aciertos = sum(m[1] for m in medidas) / len(medidas)
    return [m[0] for m in medidas], aciertos


def dibujar(ruta: Path, filas: list[dict], umbral: float, mu: float, alarma, titulo: str) -> None:
    lotes = [f["lote"] for f in filas]
    valores = [f["roc_auc"] for f in filas]
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=150, facecolor=SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)
    ax.grid(axis="y", color=REJILLA, linewidth=1)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(REJILLA)

    ax.axhline(mu, color=TEXTO_SECUNDARIO, linewidth=1)
    ax.axhline(umbral, color=CRITICO, linewidth=1.5)
    ax.plot(lotes, valores, color=SERIE, linewidth=2, marker="o", markersize=8,
            markeredgecolor=SUPERFICIE, markeredgewidth=2, zorder=3)

    ax.annotate(f"Referencia {mu:.3f}", (12.15, mu), va="center",
                color=TEXTO_SECUNDARIO, fontsize=10, annotation_clip=False)
    ax.annotate(f"Umbral {umbral:.3f}", (12.15, umbral), va="center",
                color=TEXTO, fontsize=10, annotation_clip=False)

    if alarma is not None:
        valor = valores[alarma - 1]
        ax.plot([alarma], [valor], marker="o", markersize=12, color=CRITICO,
                markeredgecolor=SUPERFICIE, markeredgewidth=2, zorder=4)
        ax.annotate(
            f"⚠ Alarma en el lote {alarma}\n3 lotes seguidos bajo el umbral ({valor:.3f})",
            (alarma, valor), xytext=(-14, -12), textcoords="offset points",
            ha="right", va="top", color=TEXTO, fontsize=10,
        )

    etiquetas = [
        f"{f['lote']}\n{f['fraccion_regla_nueva']:.0%}" if f["fraccion_regla_nueva"] else str(f["lote"])
        for f in filas
    ]
    ax.set_xticks(lotes, etiquetas, color=TEXTO_SECUNDARIO, fontsize=10)
    ax.tick_params(axis="y", colors=TEXTO_SECUNDARIO, length=0, labelsize=10)
    ax.tick_params(axis="x", length=0)
    ax.set_xlim(0.6, 12.1)
    ax.set_xlabel("Lote de 1.000 filas (debajo, % de filas elegibles con la regla nueva)",
                  color=TEXTO_SECUNDARIO, fontsize=10, labelpad=8)
    ax.set_ylabel("ROC-AUC", color=TEXTO_SECUNDARIO, fontsize=10)
    ax.set_title(titulo, loc="left", color=TEXTO, fontsize=13, pad=14)
    fig.tight_layout()
    fig.savefig(ruta, facecolor=SUPERFICIE)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--escenario", choices=ESCENARIOS, default="regla_nueva")
    args = parser.parse_args()

    train, test, produccion = particiones()
    uri = f"models:/{NOMBRE_MODELO}@{ALIAS}"
    version = MlflowClient().get_model_version_by_alias(NOMBRE_MODELO, ALIAS)
    modelo = mlflow.sklearn.load_model(f"models:/{NOMBRE_MODELO}/{version.version}")

    valores_ref, accuracy_ref = referencia(modelo, test)
    mu, sigma, umbral = umbral_metrica(valores_ref)
    print(f"Modelo: {uri} -> v{version.version} run={version.run_id}")
    print(f"Referencia: mu={mu:.4f} sigma={sigma:.4f} umbral={umbral:.4f} "
          f"(mu - max(2 sigma, {CAIDA_MINIMA})), sostenido {LOTES_SOSTENIDOS} lotes")
    print(f"\n{'lote':>4} {'regla nueva':>12} {'roc_auc':>8} {'accuracy':>9} "
          f"{'err/ref':>8} {'data drift':>11} {'bajo umbral':>12}")

    filas = []
    for numero, (lote, fraccion) in enumerate(linea_temporal(produccion, args.escenario), 1):
        roc_auc, accuracy = medir(modelo, lote)
        fila = {
            "lote": numero,
            "fraccion_regla_nueva": fraccion,
            "roc_auc": roc_auc,
            "accuracy": accuracy,
            "error_relativo": (1 - accuracy) / (1 - accuracy_ref),
            "data_drift": hay_data_drift(train, lote),
            "bajo_umbral": roc_auc < umbral,
        }
        filas.append(fila)
        print(f"{numero:>4} {fraccion:>12.0%} {roc_auc:>8.3f} {accuracy:>9.3f} "
              f"{fila['error_relativo']:>8.2f} {str(fila['data_drift']):>11} "
              f"{str(fila['bajo_umbral']):>12}")

    alarma = primer_sostenido([f["bajo_umbral"] for f in filas])
    drift_sostenido = primer_sostenido([f["data_drift"] for f in filas])
    regla_clase = next((f["lote"] for f in filas if f["error_relativo"] > 2), None)
    accion = revisar(drift_sostenido is not None, alarma is not None)
    retrasos = {k: (alarma + k if alarma else None) for k in RETRASOS}

    print(f"\nData drift sostenido: {'lote ' + str(drift_sostenido) if drift_sostenido else 'no'}")
    print(f"Alarma de la métrica: {'lote ' + str(alarma) if alarma else 'no'}")
    print(f"Contraste, error > 2x referencia (regla del notebook): "
          f"{'lote ' + str(regla_clase) if regla_clase else 'no'}")
    if alarma:
        print("Con etiquetas retrasadas k lotes, la alarma se conoce en: "
              + ", ".join(f"k={k}: lote {v}" for k, v in retrasos.items()))
    print(f"ACCIÓN: {accion}")

    REPORTES.mkdir(exist_ok=True)
    base = REPORTES / f"concept_drift_{args.escenario}"
    with base.with_suffix(".csv").open("w", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=filas[0].keys())
        escritor.writeheader()
        escritor.writerows(filas)
    resumen = {
        "escenario": args.escenario, "modelo": uri, "version": version.version,
        "run_id": version.run_id, "mu": mu, "sigma": sigma, "umbral": umbral,
        "lotes_sostenidos": LOTES_SOSTENIDOS, "lote_alarma": alarma,
        "lote_data_drift_sostenido": drift_sostenido, "lote_regla_notebook": regla_clase,
        "alarma_con_retraso": retrasos, "accion": accion,
    }
    base.with_suffix(".json").write_text(json.dumps(resumen, indent=2))
    titulos = {
        "estable": "Sin cambios: el ROC-AUC se mantiene sobre el umbral",
        "verano": "Cambian las entradas, no la regla: el ROC-AUC se mantiene",
        "regla_nueva": "Cambia la regla: el ROC-AUC cae y se dispara la alarma",
        "verano_fuerte": "Cambio fuerte de población, misma regla: el ROC-AUC también cae",
    }
    dibujar(base.with_suffix(".png"), filas, umbral, mu, alarma, titulos[args.escenario])

    mlflow.set_experiment(EXPERIMENTO_MONITOREO)
    with mlflow.start_run(run_name=f"linea-temporal_{args.escenario}"):
        mlflow.log_params({
            "escenario": args.escenario, "modelo_version": version.version,
            "modelo_run_id": version.run_id, "umbral": round(umbral, 6),
            "lotes_sostenidos": LOTES_SOSTENIDOS, "tamano_lote": TAMANO_LOTE,
        })
        mlflow.set_tag("accion", accion)
        for fila in filas:
            mlflow.log_metrics(
                {
                    "roc_auc": fila["roc_auc"],
                    "accuracy": fila["accuracy"],
                    "fraccion_regla_nueva": fila["fraccion_regla_nueva"],
                    "data_drift": float(fila["data_drift"]),
                },
                step=fila["lote"],
            )
        for sufijo in (".png", ".csv", ".json"):
            mlflow.log_artifact(str(base.with_suffix(sufijo)))

    return 1 if alarma else 0


if __name__ == "__main__":
    sys.exit(main())
