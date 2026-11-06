#!/usr/bin/env bash
# Copia la base de datos y los artefactos de MLflow a backups/. Ejecutar sin entrenamientos en curso.
set -euo pipefail

CARPETA="$(dirname "$0")/../backups"
mkdir -p "$CARPETA"
ARCHIVO="$CARPETA/mlflow-$(date +%Y%m%d-%H%M%S).tar.gz"
kubectl exec -n mlops deployment/mlflow -- tar czf - -C /mlflow . > "$ARCHIVO"
# Sin grep -q: cerraría la tubería antes de tiempo y pipefail daría un falso negativo.
tar tzf "$ARCHIVO" | grep 'mlflow.db' > /dev/null || { echo "Copia inválida: falta mlflow.db" >&2; exit 1; }
echo "Copia guardada: $ARCHIVO ($(du -h "$ARCHIVO" | cut -f1))"
