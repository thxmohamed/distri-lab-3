#!/usr/bin/env bash
# Arranca el frontend de métricas (Rol 4, Sección 5.4) dentro de un srun
# step de publishers.sbatch. Lee metrics/*.jsonl del mismo shared FS que
# escriben los peers -- no habla pub/sub ni gossip, así que puede correr
# en cualquiera de los hosts GPU (solo CPU) de la asignación.
set -euo pipefail

: "${CIVICMESH_RUNS:?CIVICMESH_RUNS no está seteado}"
: "${RUN_ID:?RUN_ID no está seteado}"

HOST="$(hostname -s)"
echo "[frontend] levantando en $HOST:8501 (RUN_ID=$RUN_ID)"

# Se deja constancia del host real para armar el túnel SSH (Sección 5.4:
# "puerto + tunnel SSH si aplica; documentar en el README") sin tener que
# adivinarlo revisando squeue.
mkdir -p "$CIVICMESH_RUNS/$RUN_ID/logs"
echo "$HOST" >"$CIVICMESH_RUNS/$RUN_ID/logs/frontend_host.txt"

exec streamlit run civicmesh/frontend/app.py \
  --server.port 8501 --server.address 0.0.0.0
