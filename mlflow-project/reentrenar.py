"""Reproduce el Paso 5 y el ejercicio 3 del notebook: modelo viejo, mezclado y nuevo.

Entrena con los lotes 9 a 12 (regla nueva) y evalúa con el resto de `produccion`, bajo
esa misma regla. El ganador se registra con el alias `candidato`: `production` no se
mueve porque la regla nueva es simulada. Si el alias ya existe, no registra otra versión.
"""
import json
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException
from mlflow.models import infer_signature
from sklearn.base import clone
from sklearn.metrics import roc_auc_score

from datos import OBJETIVO, SEMILLA, SHA256, VARIABLES, particiones
from drift import TAMANO_LOTE, aplicar_regla_nueva, linea_temporal
from registrar import ALIAS, NOMBRE_MODELO
from revisar_concept_drift import EXPERIMENTO_MONITOREO

ALIAS_CANDIDATO = "candidato"
REPORTES = Path(__file__).parent / "reportes"


def auc(modelo, datos: pd.DataFrame) -> float:
    return float(roc_auc_score(datos[OBJETIVO], modelo.predict_proba(datos[VARIABLES])[:, 1]))


def main() -> None:
    train, _, produccion = particiones()
    cliente = MlflowClient()
    version = cliente.get_model_version_by_alias(NOMBRE_MODELO, ALIAS)
    viejo = mlflow.sklearn.load_model(f"models:/{NOMBRE_MODELO}/{version.version}")

    lotes = linea_temporal(produccion, "regla_nueva")
    regla_nueva = pd.concat([lote for lote, _ in lotes[8:12]])
    # Mismo orden que linea_temporal: lo que queda después del lote 12 no se usó en ninguno.
    mezclada = produccion.sample(frac=1, random_state=SEMILLA).reset_index(drop=True)
    evaluacion = aplicar_regla_nueva(
        mezclada.iloc[12 * TAMANO_LOTE:], 1.0, np.random.default_rng(SEMILLA)
    )

    # clone() conserva hiperparámetros y preprocesamiento, sin los datos ajustados.
    nuevo = clone(viejo).fit(regla_nueva[VARIABLES], regla_nueva[OBJETIVO])
    combinados = pd.concat([train, regla_nueva])
    mezclado = clone(viejo).fit(combinados[VARIABLES], combinados[OBJETIVO])

    resultados = {
        "filas_entrenamiento_regla_nueva": len(regla_nueva),
        "filas_evaluacion": len(evaluacion),
        "viejo_produccion": auc(viejo, evaluacion),
        "mezclado": auc(mezclado, evaluacion),
        "nuevo_solo_regla_nueva": auc(nuevo, evaluacion),
    }
    print(json.dumps(resultados, indent=2))
    REPORTES.mkdir(exist_ok=True)
    ruta = REPORTES / "reentrenamiento.json"
    ruta.write_text(json.dumps(resultados, indent=2))

    try:
        existente = cliente.get_model_version_by_alias(NOMBRE_MODELO, ALIAS_CANDIDATO)
        print(f"El alias {ALIAS_CANDIDATO} ya apunta a v{existente.version}: no se registra otra.")
        return
    except MlflowException:
        pass

    mlflow.set_experiment(EXPERIMENTO_MONITOREO)
    with mlflow.start_run(run_name="reentrenamiento_regla-nueva") as run:
        mlflow.log_params({
            "modelo_base_version": version.version,
            "filas_entrenamiento": len(regla_nueva),
            "filas_evaluacion": len(evaluacion),
        })
        mlflow.log_metrics({
            "roc_auc_viejo": resultados["viejo_produccion"],
            "roc_auc_mezclado": resultados["mezclado"],
            "roc_auc_nuevo": resultados["nuevo_solo_regla_nueva"],
        })
        mlflow.set_tags({"dataset": "uci-adult+regla-simulada", "dataset_sha256": SHA256})
        mlflow.log_artifact(str(ruta))
        mlflow.sklearn.log_model(
            sk_model=nuevo,
            name="modelo",
            signature=infer_signature(regla_nueva[VARIABLES], nuevo.predict(regla_nueva[VARIABLES])),
            input_example=regla_nueva[VARIABLES].head(3),
        )

    registrada = mlflow.register_model(f"runs:/{run.info.run_id}/modelo", NOMBRE_MODELO)
    cliente.update_model_version(
        NOMBRE_MODELO, registrada.version,
        "Reentrenado con la regla nueva simulada. No es el modelo en producción.",
    )
    cliente.set_registered_model_alias(NOMBRE_MODELO, ALIAS_CANDIDATO, registrada.version)
    print(f"{ALIAS_CANDIDATO} -> v{registrada.version}; {ALIAS} sigue en v{version.version}")


if __name__ == "__main__":
    main()
