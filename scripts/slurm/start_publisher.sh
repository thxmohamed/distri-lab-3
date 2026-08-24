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

# Puerto distinto por dominio: en DIINF cada publicador corre en un host
# GPU distinto (misma razón que start_peer.sh no puede asumir puerto fijo
# por índice local -- si dos "nodos" llegaran a compartir IP, como pasa al
# probar esto localmente con Slurm de un solo nodo, un puerto fijo choca).
EXTRA_ARGS=()
if [ "$DOMAIN" = "air" ]; then
  PORT=7002
  EXTRA_ARGS=(--pollutant pm2_5)
else
  PORT=7001
fi

echo "[publisher-$DOMAIN] $HOST:$PORT, comuna=$COMMUNE, seed=$SEED_HOST:$SEED_PORT"

exec python -m civicmesh.domains.run_publisher \
  --domain "$DOMAIN" --commune "$COMMUNE" \
  --id "publisher-$DOMAIN" --host "$HOST" --port "$PORT" \
  --seed-id peer-0-0 --seed-host "$SEED_HOST" --seed-port "$SEED_PORT" \
  --interval 2 "${EXTRA_ARGS[@]}"
