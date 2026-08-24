#!/usr/bin/env bash
# Arranca un peer de CivicMesh dentro de un srun step de peers.sbatch.
#
# Se lanza una vez POR PEER (no uno por nodo con varios ntasks): así cada
# peer queda en su propio Slurm step y se puede matar individualmente con
# `scancel <jobid>.<step>` para el experimento de caída/partición
# (Sección 5.3, paso 7 del enunciado).
#
# Uso: start_peer.sh <run_id> <topics> <node_idx> <local_idx>
set -euo pipefail

RUN_ID="$1"
TOPICS="$2"
NODE_IDX="$3"
LOCAL_IDX="$4"

: "${CIVICMESH_RUNS:?CIVICMESH_RUNS no está seteado}"

RUN_DIR="$CIVICMESH_RUNS/$RUN_ID"
HOSTFILE="$RUN_DIR/hostfile.txt"
PEER_ID="peer-${NODE_IDX}-${LOCAL_IDX}"
PORT=$((6001 + LOCAL_IDX))
HOST="$(hostname -s)"

# Append es seguro sin lock: en Linux, escrituras de una sola línea corta
# (<< PIPE_BUF) con O_APPEND son atómicas, así que varios peers pueden
# registrarse en paralelo sin pisarse.
echo "$PEER_ID $HOST $PORT" >>"$HOSTFILE"

COMMON_ARGS=(
  --id "$PEER_ID" --host "$HOST" --port "$PORT"
  --subscribe "$TOPICS"
  --run-id "$RUN_ID"
)

# peer-0-0 es el seed: no espera a nadie (Sección 5.3, paso 3).
if [ "$NODE_IDX" = "0" ] && [ "$LOCAL_IDX" = "0" ]; then
  echo "[$PEER_ID] soy el seed en $HOST:$PORT."
  exec python -m civicmesh.pubsub.run_peer "${COMMON_ARGS[@]}"
fi

# El resto espera a que el seed aparezca en el hostfile compartido y
# recién ahí hace JOIN contra él (Sección 5.3, paso 4).
echo "[$PEER_ID] esperando a peer-0-0 en $HOSTFILE..."
SEED_LINE=""
for _ in $(seq 1 30); do
  SEED_LINE="$(grep '^peer-0-0 ' "$HOSTFILE" || true)"
  [ -n "$SEED_LINE" ] && break
  sleep 2
done

if [ -z "$SEED_LINE" ]; then
  echo "[$PEER_ID] el seed no aparecio en el hostfile tras 60s" >&2
  exit 1
fi

SEED_HOST="$(awk '{print $2}' <<<"$SEED_LINE")"
SEED_PORT="$(awk '{print $3}' <<<"$SEED_LINE")"

exec python -m civicmesh.pubsub.run_peer "${COMMON_ARGS[@]}" \
  --seed-id peer-0-0 --seed-host "$SEED_HOST" --seed-port "$SEED_PORT"
