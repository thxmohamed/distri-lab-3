# CivicMesh en el clúster DIINF (Slurm)

Implementa la Sección 5 del enunciado: 2 hosts CPU para los peers
(gossip + pub/sub) y 2 hosts GPU —usando **solo la CPU del host**, sin
CUDA— para los publicadores de dominio y el frontend.

No se testeó contra un clúster DIINF real (no tenemos acceso desde acá):
los scripts están escritos y verificados sintácticamente (`bash -n`), y la
lógica de arranque se probó localmente simulando lo que hace Slurm (ver
sección "Qué se validó" más abajo). Los nombres de partición son
placeholders — **correr `sinfo` primero** y ajustar o sobreescribir por
línea de comandos.

## Orden de arranque

```bash
# 0. Desde la raíz del repo, en el clúster (el checkout debe vivir en el
#    shared FS -- home o proyecto montado en todos los nodos, Sección 5.2).
sinfo   # confirmar nombres reales de partición CPU/GPU

# 1. Elegir dónde viven las corridas en el shared FS y exportarlo.
export CIVICMESH_RUNS=/home/$USER/civicmesh-runs

# 2. Lanzar los peers (2 hosts CPU). RUN_ID por defecto es $SLURM_JOB_ID.
sbatch --partition=<nombre-CPU-real> scripts/slurm/peers.sbatch
# -> "Submitted batch job 12345"

# 3. Pasarle ese mismo id a los publicadores (2 hosts GPU) + frontend.
export RUN_ID=12345
sbatch --partition=<nombre-GPU-real> scripts/slurm/publishers.sbatch

# 4. Seguir el progreso.
squeue -u $USER
tail -f civicmesh-peers-12345.out civicmesh-publishers-*.out
```

El resto de la coordinación (quién es el seed, a qué host:puerto unirse)
pasa por `$CIVICMESH_RUNS/$RUN_ID/hostfile.txt` en el shared FS, tal como
describe la Sección 5.3 del enunciado — no por MPI ni por variables de
Slurm entre los dos jobs.

## Ver el frontend (túnel SSH)

El frontend queda en un nodo de cómputo, no en el login node:

```bash
cat $CIVICMESH_RUNS/$RUN_ID/logs/frontend_host.txt   # ej: gpu-node-02

# Desde tu máquina local:
ssh -L 8501:gpu-node-02:8501 <usuario>@<login-node-diinf>
# Abrir http://localhost:8501 -- el run_id ya viene precargado (env RUN_ID)
```

## Experimento de caída/partición (Sección 5.3 paso 7 / Sección 11)

`peers.sbatch` imprime, al arrancar, el mapeo `step -> peer` (cada peer es
su propio `srun` step, justamente para poder matarlo individualmente):

```
Mapa de steps -> peer (para el experimento de caída, Sección 5.3 paso 7):
  scancel 12345.0  ->  peer-0-0 (cpu-node-01)
  scancel 12345.1  ->  peer-0-1 (cpu-node-01)
  scancel 12345.2  ->  peer-1-0 (cpu-node-02)
  scancel 12345.3  ->  peer-1-1 (cpu-node-02)
```

Ese mapeo es best-effort (asume que Slurm asigna los step id en el orden
en que se lanzaron los `srun`); confirmar antes de matar nada con:

```bash
sacct -j 12345 --format=JobID,NodeList,Start,State
```

Luego:

```bash
scancel 12345.2      # mata peer-1-0
# esperar unos gossip_interval (default 3s) + failure_timeout (default 10s)
tail -f $CIVICMESH_RUNS/$RUN_ID/logs/peer-1-1.log   # el vecino en el mismo host
```

Comparar `metrics/peer-*.jsonl` (o el frontend) antes/durante/después de
la caída — igual que hace `scripts/analytics/run_partition_experiment.sh`
en Docker Compose, pero acá con evidencia real multi-host en DIINF
(preferido por la Sección 8 del enunciado).

## Qué se validó (y qué no)

- ✅ `python -m civicmesh.pubsub.run_peer` / `run_publisher` con
  `--seed-*`, `--run-id` y `CIVICMESH_RUNS`: probado en Docker Compose
  (`docker-compose.yml`) con 3 peers reales y reenvío multi-hop
  confirmado (`hop_count=2` en los logs).
- ✅ Sintaxis de los 5 scripts (`bash -n`).
- ✅ Lógica de `start_peer.sh` (registro en hostfile + espera al seed):
  simulada en local con dos procesos en `127.0.0.1` en vez de nodos
  Slurm reales.
- ❌ **No probado**: los `#SBATCH` reales contra un scheduler Slurm (no
  hay acceso al clúster DIINF desde este entorno). Antes de la entrega,
  correr una vez de verdad y ajustar lo que `sinfo`/`sacct` digan que no
  calza (nombres de partición, límites de tiempo, si `-w <hostname>`
  necesita el nombre corto o el FQDN, etc.) y dejarlo como evidencia en
  el informe (Sección 8, entregable "Mapa proceso↔nodo Slurm").

## Ajustar la escala del experimento

- `TOPICS` (env var, default `estacion-central,santiago,maipu`): comunas
  a las que se suscriben los peers.
- `PEERS_PER_NODE` (variable dentro de `peers.sbatch`, default `2`):
  cuántos peers por host CPU.
- Tiempos de espera del bootstrap (`for _ in $(seq 1 30/60)` + `sleep 2`
  en cada script `start_*.sh`): si el clúster tarda más en agendar los
  steps, subir el número de reintentos.
