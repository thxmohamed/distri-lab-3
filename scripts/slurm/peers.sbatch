#!/bin/bash
#SBATCH --job-name=civicmesh-peers
#SBATCH --partition=CPU
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=2
#SBATCH --cpus-per-task=1
#SBATCH --time=00:20:00
#SBATCH --output=civicmesh-peers-%j.out
#SBATCH --error=civicmesh-peers-%j.err
#
# 2 hosts CPU, 2 peers por host (Sección 5.1 del enunciado: "Varios
# procesos peer por host"). --partition=CPU es un placeholder: confirmar
# el nombre real con `sinfo` en DIINF (el enunciado no lo fija) y ajustar
# aquí, o sobreescribir sin tocar el archivo:
#   sbatch --partition=<nombre> scripts/slurm/peers.sbatch
#
# Requiere, antes de este sbatch:
#   export CIVICMESH_RUNS=<ruta en el shared FS de DIINF>
# Ver scripts/slurm/README.md para el orden completo de arranque
# (peers -> publishers, Sección 5.3).
#
# Ejecutar `sbatch` desde la raíz del repo (no desde scripts/slurm/):
# los procesos Python usan `python -m civicmesh...`, que necesita el repo
# en el cwd para resolver el paquete (mismo motivo que Makefile usa
# 'python -m pytest' en vez de 'pytest' a secas).

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

: "${CIVICMESH_RUNS:?Seteá CIVICMESH_RUNS antes de mandar este job (ver scripts/slurm/README.md)}"

RUN_ID="${RUN_ID:-$SLURM_JOB_ID}"
RUN_DIR="$CIVICMESH_RUNS/$RUN_ID"
TOPICS="${TOPICS:-estacion-central,santiago,maipu}"

mkdir -p "$RUN_DIR/metrics" "$RUN_DIR/logs"
: >"$RUN_DIR/hostfile.txt"

# Snapshot de la config usada en esta corrida (Sección 5.2: "config.yaml
# # seed, comunas, TTL, fanout, lambdas"). El repo usa dos archivos en
# vez de uno solo -- se copian ambos tal cual.
cp config/domains.yaml config/pubsub.yaml "$RUN_DIR/"

echo "$RUN_ID" >"$RUN_DIR/RUN_ID"
echo "RUN_ID=$RUN_ID" | tee "$RUN_DIR/logs/peers-submit.info"
echo "CIVICMESH_RUNS=$CIVICMESH_RUNS"

export CIVICMESH_RUNS RUN_ID

NODES=($(scontrol show hostnames "$SLURM_JOB_NODELIST"))
PEERS_PER_NODE=2

echo "Nodos asignados: ${NODES[*]}"
echo "Mapa de steps -> peer (para el experimento de caída, Sección 5.3 paso 7):"

step=0
for node_idx in "${!NODES[@]}"; do
  for local_idx in $(seq 0 $((PEERS_PER_NODE - 1))); do
    echo "  scancel ${SLURM_JOB_ID}.${step}  ->  peer-${node_idx}-${local_idx} (${NODES[$node_idx]})"

    srun --nodes=1 --ntasks=1 -w "${NODES[$node_idx]}" \
      bash scripts/slurm/start_peer.sh "$RUN_ID" "$TOPICS" "$node_idx" "$local_idx" \
      >"$RUN_DIR/logs/peer-${node_idx}-${local_idx}.log" 2>&1 &

    step=$((step + 1))
  done
done

wait
