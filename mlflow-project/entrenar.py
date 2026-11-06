"""Entrena los 8 runs del proyecto. Sigue el bucle de entrenar2.py de la práctica."""
import subprocess

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from datos import CATEGORICAS, NUMERICAS, OBJETIVO, SEMILLA, SHA256, VARIABLES, particiones

EXPERIMENTO = "Adult Income Classification"

VALORES_C = [0.01, 0.10, 1.00, 10.0, 100.0]
BOSQUES = [(100, 8), (200, 12), (300, 16)]


def crear_pipeline(clasificador) -> Pipeline:
    """El preprocesamiento viaja dentro del artefacto del modelo."""
    preparacion = ColumnTransformer([
        ("numericas", StandardScaler(), NUMERICAS),
        ("categoricas", OneHotEncoder(handle_unknown="ignore"), CATEGORICAS),
    ])
    return Pipeline([("preparacion", preparacion), ("clasificador", clasificador)])


def info_git() -> tuple[str, bool]:
    def git(*args):
        return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()
    return git("rev-parse", "HEAD"), bool(git("status", "--porcelain", "."))


def configuraciones():
    for valor_c in VALORES_C:
        yield (
            f"regresion-logistica_c-{valor_c}",
            "regresion-logistica",
            {"C": valor_c, "max_iter": 1000},
            LogisticRegression(C=valor_c, max_iter=1000, random_state=SEMILLA),
        )
    for n_estimators, max_depth in BOSQUES:
        yield (
            f"random-forest_n-{n_estimators}_d-{max_depth}",
            "random-forest",
            {"n_estimators": n_estimators, "max_depth": max_depth},
            RandomForestClassifier(
                n_estimators=n_estimators, max_depth=max_depth,
                random_state=SEMILLA, n_jobs=-1,
            ),
        )


def main() -> None:
    train, test, produccion = particiones()
    X_train, y_train = train[VARIABLES], train[OBJETIVO]
    X_test, y_test = test[VARIABLES], test[OBJETIVO]
    commit, sucio = info_git()

    mlflow.set_experiment(EXPERIMENTO)

    for nombre, algoritmo, parametros, clasificador in configuraciones():
        with mlflow.start_run(run_name=nombre):
            modelo = crear_pipeline(clasificador)
            # El modelo se elige por validación cruzada; el test solo se informa.
            cv_roc_auc = cross_val_score(
                modelo, X_train, y_train, cv=3, scoring="roc_auc"
            ).mean()
            modelo.fit(X_train, y_train)
            y_pred = modelo.predict(X_test)
            probabilidad = modelo.predict_proba(X_test)[:, 1]

            metricas = {
                "cv_roc_auc": cv_roc_auc,
                "test_roc_auc": roc_auc_score(y_test, probabilidad),
                "accuracy": accuracy_score(y_test, y_pred),
                "f1": f1_score(y_test, y_pred),
            }
            mlflow.log_params(parametros)
            mlflow.log_params({
                "semilla": SEMILLA,
                "filas_train": len(train),
                "filas_test": len(test),
                "filas_produccion": len(produccion),
            })
            mlflow.log_metrics(metricas)
            mlflow.set_tags({
                "algoritmo": algoritmo,
                "dataset": "uci-adult",
                "dataset_sha256": SHA256,
                "git_commit": commit,
                "git_dirty": str(sucio).lower(),
            })
            mlflow.log_dict(
                {
                    "etiquetas": ["<=50K", ">50K"],
                    "matriz": confusion_matrix(y_test, y_pred).tolist(),
                },
                "matriz_confusion.json",
            )
            mlflow.log_artifact("datos.py", "codigo")
            mlflow.log_artifact("entrenar.py", "codigo")
            mlflow.sklearn.log_model(
                sk_model=modelo,
                name="modelo",
                signature=infer_signature(X_train, modelo.predict(X_train)),
                input_example=X_train.head(3),
            )
            print(f"{nombre}: cv_roc_auc={cv_roc_auc:.4f} "
                  f"test_roc_auc={metricas['test_roc_auc']:.4f}")


if __name__ == "__main__":
    main()
