#!/bin/bash
#SBATCH --job-name=civicmesh-publishers
#SBATCH --partition=GPU
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:20:00
#SBATCH --output=civicmesh-publishers-%j.out
#SBATCH --error=civicmesh-publishers-%j.err
#
# 2 hosts GPU -- SOLO CPU del host, no se usa CUDA en este laboratorio
# (Sección 5, "Importante"). Corren los publicadores de dominio y el
# frontend de métricas (Rol 4). --partition=GPU es un placeholder:
# confirmar el nombre real con `sinfo` y ajustar aquí, o:
#   sbatch --partition=<nombre> scripts/slurm/publishers.sbatch
#
# Requiere que peers.sbatch ya esté corriendo (o haya corrido) con el
# mismo RUN_ID, y las mismas variables antes de este sbatch:
#   export CIVICMESH_RUNS=<misma ruta que en peers.sbatch>
#   export RUN_ID=<job id que imprimió peers.sbatch>
# Ver scripts/slurm/README.md para el orden completo de arranque.

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

: "${CIVICMESH_RUNS:?Seteá CIVICMESH_RUNS (mismo valor que en peers.sbatch)}"
: "${RUN_ID:?Seteá RUN_ID=<job id de peers.sbatch> antes de mandar este job}"

RUN_DIR="$CIVICMESH_RUNS/$RUN_ID"
HOSTFILE="$RUN_DIR/hostfile.txt"

export CIVICMESH_RUNS RUN_ID

echo "Esperando el hostfile de peers.sbatch en $HOSTFILE (RUN_ID=$RUN_ID)..."
SEED_LINE=""
for _ in $(seq 1 60); do
  if [ -s "$HOSTFILE" ]; then
    SEED_LINE="$(grep '^peer-0-0 ' "$HOSTFILE" || true)"
    [ -n "$SEED_LINE" ] && break
  fi
  sleep 2
done

if [ -z "$SEED_LINE" ]; then
  echo "No aparecio el peer seed tras 120s. ¿Esta corriendo peers.sbatch con RUN_ID=$RUN_ID?" >&2
  exit 1
fi

SEED_HOST="$(awk '{print $2}' <<<"$SEED_LINE")"
SEED_PORT="$(awk '{print $3}' <<<"$SEED_LINE")"
echo "Seed encontrado: $SEED_HOST:$SEED_PORT"

NODES=($(scontrol show hostnames "$SLURM_JOB_NODELIST"))
echo "Nodos asignados: ${NODES[*]}"

srun --nodes=1 --ntasks=1 -w "${NODES[0]}" \
  bash scripts/slurm/start_publisher.sh crime estacion-central "$SEED_HOST" "$SEED_PORT" \
  >"$RUN_DIR/logs/publisher-crime.log" 2>&1 &

srun --nodes=1 --ntasks=1 -w "${NODES[1]}" \
  bash scripts/slurm/start_publisher.sh air santiago "$SEED_HOST" "$SEED_PORT" \
  >"$RUN_DIR/logs/publisher-air.log" 2>&1 &

# El frontend no habla pub/sub: comparte el segundo nodo GPU con el
# publicador de aire, cada uno como step independiente.
srun --nodes=1 --ntasks=1 -w "${NODES[1]}" \
  bash scripts/slurm/start_frontend.sh \
  >"$RUN_DIR/logs/frontend.log" 2>&1 &

wait
