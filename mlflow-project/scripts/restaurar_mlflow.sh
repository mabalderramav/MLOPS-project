#!/usr/bin/env bash
# Restaura una copia de backup_mlflow.sh sobre el PVC y reinicia MLflow y la API.
# Uso: scripts/restaurar_mlflow.sh backups/mlflow-AAAAMMDD-HHMMSS.tar.gz
set -euo pipefail

ARCHIVO="${1:?Indicar el archivo de copia}"
kubectl exec -i -n mlops deployment/mlflow -- tar xzf - -C /mlflow < "$ARCHIVO"
kubectl rollout restart deployment/mlflow -n mlops
kubectl rollout status deployment/mlflow -n mlops --timeout=240s
kubectl rollout restart deployment/adult-api -n mlops
kubectl rollout status deployment/adult-api -n mlops --timeout=240s
