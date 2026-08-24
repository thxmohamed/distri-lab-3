# CivicMesh en el clúster DIINF (Slurm)

Implementa la Sección 5 del enunciado: 2 hosts CPU para los peers
(gossip + pub/sub) y 2 hosts GPU —usando **solo la CPU del host**, sin
CUDA— para los publicadores de dominio y el frontend.

**Esto no se corrió contra el clúster DIINF real** — sin VPN no hay forma
de llegar. En su lugar, se corrió contra un Slurm real (mismo
`sbatch`/`srun`/`scancel`, no una simulación en bash) montado en mi
propia máquina, y esa es la evidencia que se usa para la entrega — ver
"Sustituto local de DIINF" y "Qué se validó" más abajo para el detalle y
las diferencias con DIINF real. Los nombres de partición (`CPU`/`GPU`)
son los que elegí para mi cluster local; si alguien llega a tener acceso
a DIINF y quiere probar ahí, correr `sinfo` primero y ajustar o
sobreescribir por línea de comandos si no coinciden.

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

En la corrida local, el frontend está en `http://localhost:8501` directo (WSL2 reenvía
el puerto al host Windows, sin túnel necesario). Capturas de las 3 vistas en
[`resultados_slurm_local/run-6/screenshots/`](../../resultados_slurm_local/run-6/screenshots/).

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
en que se lanzaron los `srun`) — y en la corrida local **no acertó**: el
mapeo decía `6.3 -> peer-1-1`, pero el que realmente murió al hacer
`scancel 6.3` fue `peer-1-0` (confirmado cruzando `squeue -j 6 -s` y los
logs, ver `resultados_slurm_local/run-6/README.md`). Conviene confirmar
siempre antes de matar nada:

```bash
sacct -j 12345 --format=JobID,NodeList,Start,State   # si el clúster tiene accounting
# o, sin accounting configurado (lo que tuve que usar yo en local):
squeue -j 12345 -s   # -s lista los steps activos del job
```

Luego:

```bash
scancel 12345.2      # mata peer-1-0
# esperar unos gossip_interval (default 3s) + failure_timeout (default 10s)
tail -f $CIVICMESH_RUNS/$RUN_ID/logs/peer-1-1.log   # el vecino en el mismo host
```

Comparar `metrics/peer-*.jsonl` (o el frontend) antes/durante/después de
la caída — igual que hace `scripts/analytics/run_partition_experiment.sh`
en Docker Compose, pero acá vía Slurm real (`scancel` a un step, no
`docker kill`). Ejemplo real de esto corriendo en
`resultados_slurm_local/run-6/`.

## Sustituto local de DIINF (Slurm real, sin VPN)

Sin acceso a la VPN de DIINF, instalé `slurm-wlm` de verdad (paquete
`slurm-wlm` 23.11.4, no un mock) dentro de WSL2 en mi laptop, configurado
con **4 nodos Slurm "de mentira"**: `cpu-node-01`, `cpu-node-02` (partición
`CPU`) y `gpu-node-01`, `gpu-node-02` (partición `GPU`), los 4 apuntando a
la misma IP local (`127.0.0.1`) pero como entradas `NodeName` separadas en
`slurm.conf` (soporte oficial de Slurm para test sin hardware real:
"multiple slurmd"). Es un `slurmctld` + 4 `slurmd` reales, así que
`sbatch`/`srun`/`squeue`/`scancel` corren de verdad, con la limitación
obvia de que las 4 "máquinas" son en realidad una sola.

**Specs de la máquina usada** (documentado porque reemplaza al hardware
de DIINF para esta corrida):

| | |
|---|---|
| CPU | AMD Ryzen 7 5700U (8 cores / 16 hilos) |
| RAM | 13,8 GB físicos (WSL2 ve ~6,7 GiB asignados) |
| SO host | Windows 11 Home Single Language, 64 bits (build 10.0.26200) |
| Entorno Slurm | WSL2, Ubuntu 24.04.1 LTS, `slurm-wlm` 23.11.4, `munge` |

Metrics, logs, config snapshot y el mapeo de steps de una corrida completa (jobs 6 y 7,
incluyendo el `scancel` de un peer) quedaron en
[`resultados_slurm_local/run-6/`](../../resultados_slurm_local/run-6/), con su propio
README explicando qué es cada archivo.

## Qué se validó (y qué no)

- ✅ **Corrida real de punta a punta** (no simulación): `sbatch
  scripts/slurm/peers.sbatch` → job real con 4 tasks (`srun` steps
  independientes) en 2 nodos de la partición `CPU`; `sbatch
  scripts/slurm/publishers.sbatch` con `RUN_ID` del job anterior → 2
  publicadores + frontend en la partición `GPU`. Los 4 peers se
  descubrieron por gossip (incluido descubrimiento *indirecto*, no solo
  contacto directo con el seed), los publicadores hicieron `JOIN` y
  publicaron delitos (`estacion-central`) y aire real de Open-Meteo
  (`santiago`, PM2.5), y `metrics/peer-*.jsonl` quedó con snapshots
  reales de ambos dominios y canales.
- ✅ **Experimento de partición real**: `scancel 6.3` mató un peer (que
  terminó siendo `peer-1-0`, no el que el mapeo impreso predecía —ver
  "Experimento de caída/partición" más arriba); tanto el seed como el
  otro peer que seguía vivo lo marcaron `DEAD` de forma independiente por
  timeout (~10s, `failure_timeout` default). Logs completos en
  `resultados_slurm_local/run-6/`. Evidencia directa para la Sección 5.3
  paso 7 / Sección 11.
- ✅ Frontend accesible por HTTP (`curl` devolvió 200) tras el fix de
  `--server.headless` (ver más abajo).
- ✅ Sintaxis de los 5 scripts (`bash -n`).
- **Bugs reales encontrados y corregidos gracias a esta corrida** (no
  hubieran aparecido con una simulación en bash plano, solo con Slurm
  real repartiendo tasks):
  - `start_peer.sh`/`start_publisher.sh` calculaban el puerto solo a
    partir de `local_idx` (peers) o un puerto fijo (publicadores) —
    asumía implícitamente que nodos distintos = IPs distintas. Con los 4
    nodos falsos compartiendo `127.0.0.1`, dos peers pisaban el mismo
    puerto y `asyncio` tiraba `OSError: address already in use`. En
    DIINF con hosts físicos de verdad esto no debería pasar, pero
    depender de esa asunción era frágil; ahora el puerto depende de
    `node_idx` también (y cada dominio de publicador tiene su propio
    puerto fijo), así que funciona sin importar si los nodos comparten
    IP o no.
  - `start_frontend.sh` (y el `frontend` de `docker-compose.yml`, mismo
    bug): Streamlit muestra una pantalla de bienvenida que pide un email
    por stdin la primera vez que corre en una máquina. Sin TTY (un
    `srun` step, o un contenedor), el proceso moría con exit code 255.
    Se agregó `--server.headless true`, que salta ese prompt — es el
    flag correcto para cualquier despliegue no interactivo, no un
    parche específico de Slurm.
- ⚠️ **Diferencias con DIINF real que quedan sin probar**:
  - **No es multi-host de verdad**: las 4 "máquinas" son la misma. El
    reenvío por red (sockets TCP reales, gossip, `should_forward`) sí es
    real, pero no hay latencia de red entre hosts físicos ni
    posibilidad de que un nodo completo se caiga por una falla de
    hardware/red distinta a matar el proceso.
  - `sacct` no funciona en mi cluster (no configuré
    `AccountingStorageType`, así que no hay base de datos de
    contabilidad) — usé `squeue`/`scontrol show job` en su lugar. En
    DIINF, con accounting configurado, `sacct` debería confirmar el
    mapeo step→peer de forma más confiable que el mapeo best-effort que
    imprime `peers.sbatch`.
  - Nombres de partición (`CPU`/`GPU`) los elegí yo en mi `slurm.conf`
    local — coinciden por diseño con los placeholders que ya tenían los
    scripts, pero en DIINF hay que confirmarlos con `sinfo` igual.
  - No se probó `-w <hostname>` con el nombre real de host de DIINF (acá
    usé nombres cortos tipo `cpu-node-01`); si DIINF requiere FQDN habría
    que ajustar `scontrol show hostnames` o el `-w` de los `srun`.

## Ajustar la escala del experimento

- `TOPICS` (env var, default `estacion-central,santiago,maipu`): comunas
  a las que se suscriben los peers.
- `PEERS_PER_NODE` (variable dentro de `peers.sbatch`, default `2`):
  cuántos peers por host CPU.
- Tiempos de espera del bootstrap (`for _ in $(seq 1 30/60)` + `sleep 2`
  en cada script `start_*.sh`): si el clúster tarda más en agendar los
  steps, subir el número de reintentos.
