"""Registra v1 (mejor regresión logística) y v2 (mejor run global) y asigna el alias.

Consulta MLflow para elegir los runs: no hay identificadores escritos a mano.
Se puede repetir: un run ya registrado no crea una versión nueva.
"""
import mlflow
from mlflow import MlflowClient

from entrenar import EXPERIMENTO

NOMBRE_MODELO = "adult-income-classifier"
ALIAS = "production"


def mejor_run(filtro: str = ""):
    experimento = mlflow.get_experiment_by_name(EXPERIMENTO)
    runs = MlflowClient().search_runs(
        [experimento.experiment_id],
        filter_string=filtro,
        order_by=["metrics.cv_roc_auc DESC"],
        max_results=1,
    )
    if not runs:
        raise SystemExit(f"No hay runs en '{EXPERIMENTO}' con el filtro '{filtro}'.")
    return runs[0]


def registrar(run, descripcion: str) -> str:
    cliente = MlflowClient()
    existentes = cliente.search_model_versions(f"name='{NOMBRE_MODELO}'")
    for version in existentes:
        if version.run_id == run.info.run_id:
            return version.version
    version = mlflow.register_model(f"runs:/{run.info.run_id}/modelo", NOMBRE_MODELO)
    cliente.update_model_version(NOMBRE_MODELO, version.version, descripcion)
    return version.version


def main() -> None:
    linea_base = mejor_run("tags.algoritmo = 'regresion-logistica'")
    mejor = mejor_run()
    if linea_base.info.run_id == mejor.info.run_id:
        raise SystemExit("El mejor run global es la línea base: revisar los resultados.")

    v1 = registrar(linea_base, "Línea base: mejor regresión logística por cv_roc_auc.")
    v2 = registrar(mejor, "Mejor run del experimento por cv_roc_auc.")
    MlflowClient().set_registered_model_alias(NOMBRE_MODELO, ALIAS, v2)

    for version, run in ((v1, linea_base), (v2, mejor)):
        print(f"v{version}: {run.info.run_name} run={run.info.run_id} "
              f"cv_roc_auc={run.data.metrics['cv_roc_auc']:.4f}")
    print(f"models:/{NOMBRE_MODELO}@{ALIAS} -> v{v2}")


if __name__ == "__main__":
    main()
