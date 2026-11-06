# Proyecto MLOps: del entrenamiento con MLflow al despliegue en Kubernetes

Clasificador de ingresos (UCI Adult) con trazabilidad en MLflow, servicio en Kubernetes con réplicas y pruebas de data drift y concept drift. Las decisiones y sus justificaciones están en [`docs/arquitectura.md`](docs/arquitectura.md).

| Servicio | URL |
| --- | --- |
| API | <http://localhost:31446/docs> |
| MLflow | <http://localhost:5001> |
| UI | <http://localhost:5002> |

## Requisitos

- Python 3.12 y [uv](https://docs.astral.sh/uv/)
- Docker
- kubectl y k3d, con un clúster `local` que publique los puertos `31446`, `5001` y `5002`

Los comandos se ejecutan desde `mlflow-project/`. [`command.txt`](command.txt) los reúne todos, en orden.

## Puesta en marcha

### 1. Entorno

En WSL, conviene crear el entorno fuera de `/mnt/c`, porque ahí es mucho más lento.

```bash
uv venv --python 3.12 ~/.venvs/mlflow-project
source ~/.venvs/mlflow-project/bin/activate
uv pip install -r requirements.txt
```

### 2. MLflow en el clúster

```bash
kubectl apply -f k8s/namespace.yaml -f k8s/mlflow.yaml
kubectl rollout status deployment/mlflow -n mlops
export MLFLOW_TRACKING_URI=http://localhost:5001
```

### 3. Entrenar y registrar

```bash
python entrenar.py     # 8 runs; descarga y verifica el dataset la primera vez
python registrar.py    # v1, v2 y alias production -> v2
```

### 4. Servicio

```bash
docker build -t adult-api:0.1.0 servicio/
k3d image import adult-api:0.1.0 -c local
kubectl apply -f k8s/api.yaml
kubectl rollout status deployment/adult-api -n mlops
curl -s localhost:31446/info
```

### 5. UI

```bash
docker build -t adult-ui:0.1.0 ui/
k3d image import adult-ui:0.1.0 -c local
kubectl apply -f k8s/ui.yaml
```

## Demostraciones de Kubernetes

```bash
kubectl get pods -n mlops -l app=adult-api -o wide           # 3 réplicas
scripts/demo_balanceo.sh 60                                  # reparto entre pods
scripts/probe_loop.sh 40                                     # y en otra terminal:
kubectl delete pod <pod> -n mlops                            # autorreparación
kubectl scale deployment/adult-api --replicas=5 -n mlops     # escalado
```

**Promover otra versión:** mover el alias en MLflow y ejecutar `kubectl rollout restart deployment/adult-api -n mlops`. Sin el reinicio, los pods siguen sirviendo la versión que tienen en memoria.

## Pruebas de drift

```bash
python generar_lotes.py
python revisar_data_drift.py --lote lotes/mismo_origen.csv        # VERDE, exit 0
python revisar_data_drift.py --lote lotes/verano.csv              # ROJO, exit 1
python revisar_data_drift.py --falsas-alarmas 300                 # tasa medida

python revisar_concept_drift.py --escenario estable               # todo bien, exit 0
python revisar_concept_drift.py --escenario verano                # vigilar, exit 0
python revisar_concept_drift.py --escenario regla_nueva           # REENTRENAR, exit 1
python reentrenar.py                                              # viejo, mezclado y nuevo
```

Cada revisión de concept drift crea un run nuevo en `Adult Income Monitoring`. Las pruebas unitarias se ejecutan con `python -m pytest`; algunas descargan el dataset si no está, pero ninguna necesita MLflow.

## Copia de seguridad

**Borrar el clúster, el namespace o el PVC destruye el registro.** Reentrenar no lo recupera, porque generaría otros `run_id`, distintos de los documentados.

```bash
scripts/backup_mlflow.sh
scripts/restaurar_mlflow.sh backups/mlflow-AAAAMMDD-HHMMSS.tar.gz
```

Para restaurar en un clúster nuevo, primero se aplican los manifiestos del paso 2.

## Guion de la interfaz de MLflow

1. Abrir `Adult Income Classification` y explicar qué representa cada run: una combinación de algoritmo e hiperparámetros.
2. Filtrar con `metrics.cv_roc_auc > 0.91` y ordenar por `cv_roc_auc`.
3. Seleccionar `random-forest_n-300_d-16`, `random-forest_n-200_d-12` y `regresion-logistica_c-1.0`, y usar **Compare**: `C` apenas cambia el resultado desde 0.1, y el bosque gana cerca de 0,009.
4. Abrir **Model Registry** → `adult-income-classifier`: `production` en la versión 2 y `candidato` en la 3.
5. Ejecutar `curl -s localhost:31446/info` y mostrar que el `run_id` coincide.

## Evidencias

| # | Evidencia | Archivo |
| --- | --- | --- |
| 1 | Runs ordenados por la métrica principal | [`01-mlflow-runs.png`](evidencias/01-mlflow-runs.png) |
| 2 | Comparación de runs | [`02-mlflow-comparacion.png`](evidencias/02-mlflow-comparacion.png) |
| 3 | Model Registry con versiones y alias | [`03-mlflow-registry.png`](evidencias/03-mlflow-registry.png) |
| 4 | Build y respuesta del contenedor | [`04-docker-run.txt`](evidencias/04-docker-run.txt) |
| 5 | Réplicas en `Running` | [`05-replicas.txt`](evidencias/05-replicas.txt) |
| 6 | Reparto de tráfico | [`06-balanceo.txt`](evidencias/06-balanceo.txt) |
| 7 | Autorreparación sin fallos | [`07-autorreparacion.txt`](evidencias/07-autorreparacion.txt) |
| 8 | Escalado a 5 y vuelta a 3 | [`08-escalado.txt`](evidencias/08-escalado.txt) |
| 9 | Promoción y `/info` | [`09-promocion.txt`](evidencias/09-promocion.txt) |
| 10 | Data drift en verde | [`10-data-drift-verde.txt`](evidencias/10-data-drift-verde.txt) |
| 11 | Data drift en rojo | [`11-data-drift-rojo.txt`](evidencias/11-data-drift-rojo.txt) |
| 12 | Gráfica temporal de concept drift | [`12-concept-drift.png`](evidencias/12-concept-drift.png) |
| 13 | Alarma de concept drift | [`13-concept-alarma.txt`](evidencias/13-concept-alarma.txt) |
| 14 | Modelo viejo, mezclado y nuevo | [`14-reentrenamiento.txt`](evidencias/14-reentrenamiento.txt) |
| 15 | UI con el pod que respondió | [`15-ui-k8s.png`](evidencias/15-ui-k8s.png) |
| 16 | Servicio con MLflow caído | [`16-mlflow-caido.txt`](evidencias/16-mlflow-caido.txt) |

Los nombres de pods difieren entre evidencias, porque se tomaron en distintos momentos y los pods se reemplazan.
