# MLOps: prácticas y proyecto

Prácticas del módulo de ML-Ops y puesta en producción, desde contenerizar un modelo hasta desplegarlo y monitorearlo en Kubernetes.

| Carpeta | Tema | Resumen |
| --- | --- | --- |
| [`docker-practica/`](docker-practica/) | Docker | Modelo de riesgo crediticio convertido en una API con FastAPI y contenerizado. |
| [`kubernetes-practica/`](kubernetes-practica/) | Kubernetes | Ejercicios sobre un clúster local k3d y una práctica con NGINX. |
| [`mlffow-practicas/`](mlffow-practicas/) | MLflow | Registro de experimentos con el dataset Iris. |
| [`drift-practica/`](drift-practica/) | Drift | Notebook que explica data drift y concept drift con el ejemplo de una heladería. |
| [`mlflow-project/`](mlflow-project/) | Proyecto integrador | Clasificador de ingresos con MLflow, despliegue en Kubernetes y pruebas de drift. |

## Docker

Parte de un modelo que solo se podía usar con un script local y lo expone como servicio, con los endpoints `/health` y `/predecir`. La imagen usa `python:3.11-slim` y se ejecuta con un usuario sin privilegios. La versión final está en `entrega/`, junto con las respuestas y las evidencias.

## Kubernetes

Las carpetas numeradas siguen un orden progresivo:

| Carpeta | Tema |
| --- | --- |
| `00-base` | Configuración del clúster k3d |
| `01-pod` | Pods |
| `02-deployment` | Deployments |
| `03-services` | Services |
| `04-namespace` | Namespaces y cuotas |
| `05-rolling-update` | Actualizaciones progresivas |
| `06-resources` | Recursos: Pods en `Pending`, falta de memoria y límites de CPU |

[`practica-01/`](kubernetes-practica/practica-01/README.md) despliega `nginx:alpine` como Pod y luego como Deployment con un Service, y documenta con evidencias la recuperación, el escalado, la actualización y la reversión.

## MLflow

- `entrenar.py` compara regresiones logísticas con distintos valores de `max_iter`.
- `entrenar2.py` compara distintos valores de regularización `C`, y registra cada modelo con su firma en un servidor de MLflow en `http://127.0.0.1:5050`.

## Drift

[`clase_drift.ipynb`](drift-practica/clase_drift.ipynb) entrena una regresión lineal que predice las ventas de helados según la temperatura y muestra la diferencia entre los dos tipos de drift:

- **Data drift:** cambian los datos de entrada. Se detecta con la prueba KS.
- **Concept drift:** cambia la relación entre los datos y el resultado. Se detecta comparando las predicciones con los valores reales, y suele requerir reentrenar.

## Proyecto integrador

Reúne los temas anteriores con un clasificador de ingresos (UCI Adult):

- **Entrenamiento:** runs comparados en MLflow y versiones con alias en el Model Registry.
- **Servicio:** API con FastAPI y UI con Streamlit, desplegadas en Kubernetes con réplicas.
- **Monitoreo:** revisiones de data drift y concept drift, y reentrenamiento.
- **Operación:** scripts de copia de seguridad y restauración de MLflow.

Las instrucciones están en su [`README.md`](mlflow-project/README.md), y las decisiones de diseño en [`docs/arquitectura.md`](mlflow-project/docs/arquitectura.md).
