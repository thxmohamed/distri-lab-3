#!/usr/bin/env bash
#
# Experimento de caída/partición.
#
# Mata un peer a mitad de una corrida de Docker Compose y deja evidencia
# en metrics/ de cómo se comporta la malla mientras el peer caído no
# puede reenviar nada: caída de convergencia entre los peers
# sobrevivientes, huecos de tiempo en su .jsonl.
#
# Asume que la malla ya está arriba:
#   docker compose up --build -d
#
# Uso (bash -- en Windows, correr desde Git Bash, no PowerShell/cmd):
#   ./scripts/analytics/run_partition_experiment.sh [target] [warmup_s] [downtime_s]
#
#   target:     contenedor a matar (default: civicmesh-peer-3)
#   warmup_s:   segundos a esperar antes de matar el peer, para tener
#               baseline en metrics/ (default: 20)
#   downtime_s: segundos que el peer permanece caído antes de revivirlo
#               (default: 20)
set -euo pipefail

TARGET="${1:-civicmesh-peer-3}"
WARMUP_S="${2:-20}"
DOWNTIME_S="${3:-20}"
SERVICE="${TARGET#civicmesh-}"
METRICS_DIR="${CIVICMESH_RUNS:-./runs}/compose/metrics"

snapshot() {
    local label="$1"

    echo "==> Snapshot ${label} (líneas por peer en metrics/):"

    if compgen -G "${METRICS_DIR}/*.jsonl" > /dev/null; then
        wc -l "${METRICS_DIR}"/*.jsonl
    else
        echo "(todavía no hay métricas en ${METRICS_DIR})"
    fi
}

echo "==> Warmup: esperando ${WARMUP_S}s con la malla sana..."
sleep "$WARMUP_S"

snapshot "ANTES de la partición"

echo "==> Matando ${TARGET} (simula caída/partición de peer)..."
docker kill "$TARGET"

echo "==> Peer caído. Esperando ${DOWNTIME_S}s para observar el efecto..."
sleep "$DOWNTIME_S"

snapshot "DURANTE la partición"

echo "==> Reviviendo ${TARGET} (docker compose up -d ${SERVICE})..."
docker compose up -d "$SERVICE"

echo "==> Esperando ${WARMUP_S}s a que ${TARGET} se reincorpore (JOIN + gossip)..."
sleep "$WARMUP_S"

snapshot "DESPUÉS de la recuperación"

cat <<'EOF'

==> Listo. Qué revisar:
    - Compara metrics/peer-*.jsonl antes / durante / después: el peer
      caído no debe escribir snapshots nuevos mientras estuvo fuera, y
      los peers sobrevivientes deberían mostrar mayor "convergence"
      (civicmesh.analytics.convergence.peer_convergence) durante ese
      tramo, porque dejan de ver los valores que ese peer reportaba.
    - Abre el frontend (http://localhost:8501) y compara la tabla de
      "Convergencia entre peers" antes/durante/después.
    - Qué pasó con should_forward y el hop_count una vez que el peer
      se reincorpora.
EOF
