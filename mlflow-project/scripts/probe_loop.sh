#!/usr/bin/env bash
# Envía peticiones continuas durante SEGUNDOS y registra el resultado de cada una.
# Termina con exit 1 si alguna falló. Sirve para demostrar la autorreparación.
set -uo pipefail

SEGUNDOS="${1:-30}"
URL="${API_URL:-http://localhost:31446}"
SOLICITUD="$(dirname "$0")/solicitud.json"
fin=$(( $(date +%s) + SEGUNDOS ))
total=0
fallos=0
anterior=""

while [ "$(date +%s)" -lt "$fin" ]; do
  salida=$(curl -s --max-time 3 -w ' %{http_code}' -X POST "$URL/predecir" \
    -H 'Content-Type: application/json' -d @"$SOLICITUD")
  codigo="${salida##* }"
  pod=$(printf '%s' "$salida" | grep -o '"pod":"[^"]*"' | cut -d'"' -f4)
  total=$((total + 1))
  if [ "$codigo" != "200" ]; then
    fallos=$((fallos + 1))
    echo "$(date +%T) FALLO codigo=$codigo"
  elif [ "$pod" != "$anterior" ] && [ "${VERBOSO:-0}" = "1" ]; then
    echo "$(date +%T) 200 pod=$pod"
  fi
  anterior="$pod"
  sleep 0.1
done

echo "Peticiones: $total | Fallidas: $fallos"
[ "$fallos" -eq 0 ]
