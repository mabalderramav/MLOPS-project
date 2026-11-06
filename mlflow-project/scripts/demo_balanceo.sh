#!/usr/bin/env bash
# Envía N peticiones al Service y cuenta qué pod atendió cada una.
# El Service reparte por conexión: cada curl es un proceso y una conexión nuevos.
set -euo pipefail

N="${1:-60}"
URL="${API_URL:-http://localhost:31446}"
SOLICITUD="$(dirname "$0")/solicitud.json"

echo "Enviando $N peticiones a $URL/predecir"
for _ in $(seq 1 "$N"); do
  curl -s --max-time 5 -X POST "$URL/predecir" \
    -H 'Content-Type: application/json' -d @"$SOLICITUD" \
    | grep -o '"pod":"[^"]*"' | cut -d'"' -f4
done | sort | uniq -c | awk '{print $1 " peticiones -> " $2}'
