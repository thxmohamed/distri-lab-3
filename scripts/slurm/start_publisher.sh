#!/usr/bin/env bash
# Arranca un publicador de dominio dentro de un srun step de
# publishers.sbatch. Corre en un host GPU del clúster, pero usa solo la
# CPU del nodo (sin CUDA, ver el "Importante" de la Sección 5).
#
# Uso: start_publisher.sh <crime|air> <comuna> <seed_host> <seed_port>
set -euo pipefail

DOMAIN="$1"
COMMUNE="$2"
SEED_HOST="$3"
SEED_PORT="$4"

HOST="$(hostname -s)"
PORT=7001

EXTRA_ARGS=()
if [ "$DOMAIN" = "air" ]; then
  EXTRA_ARGS=(--pollutant pm2_5)
fi

echo "[publisher-$DOMAIN] $HOST:$PORT, comuna=$COMMUNE, seed=$SEED_HOST:$SEED_PORT"

exec python -m civicmesh.domains.run_publisher \
  --domain "$DOMAIN" --commune "$COMMUNE" \
  --id "publisher-$DOMAIN" --host "$HOST" --port "$PORT" \
  --seed-id peer-0-0 --seed-host "$SEED_HOST" --seed-port "$SEED_PORT" \
  --interval 2 "${EXTRA_ARGS[@]}"
