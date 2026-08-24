# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/), y el
proyecto usa [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Added

- `scripts/slurm/{peers,publishers}.sbatch` + `start_{peer,publisher,frontend}.sh`:
  despliegue en el clúster DIINF (Sección 5) — 2 hosts CPU con 2 peers cada uno, 2
  hosts GPU (solo CPU del host, sin CUDA) con publicadores + frontend, coordinados por
  `$CIVICMESH_RUNS/$RUN_ID/hostfile.txt` en el shared FS. Cada peer es su propio `srun`
  step para poder matarlo individualmente con `scancel <jobid>.<step>` (experimento de
  partición, Sección 5.3 paso 7). Lógica de bootstrap (hostfile + espera al seed)
  validada localmente simulando dos nodos; los `#SBATCH` en sí no se probaron contra un
  clúster real (sin acceso desde este entorno) — detalle en `scripts/slurm/README.md`.
- `civicmesh/analytics/`: capa de métricas del Rol 4 (Sección 4.4 y 5.2).
  `convergence.py` implementa `perception_gap()` (brecha percepción-realidad,
  canal subjetivo) y `peer_convergence()` (dispersión del canal objetivo
  entre peers); `writer.py`/`delivery.py` vuelcan un snapshot JSONL por
  mensaje entregado a `$CIVICMESH_RUNS/<run_id>/metrics/<peer_id>.jsonl`.
  `civicmesh/pubsub/run_peer.py` lo engancha vía los flags nuevos
  `--metrics-dir`/`--run-id` (sin ellos, comportamiento idéntico al de antes).
- `civicmesh/frontend/app.py`: frontend mínimo (Streamlit, Sección 5.4) que
  lee `metrics/*.jsonl` de una corrida y muestra estado por tópico × canal,
  brecha percepción-realidad y convergencia entre peers. Agregado a
  `docker-compose.yml` como servicio `frontend` (puerto 8501), sobre el
  mismo volumen `./runs:/civicmesh-runs` que ahora montan los 3 peers.
- `scripts/analytics/run_partition_experiment.sh`: experimento de
  caída/partición (Sección 5.3 punto 7 / Sección 11) sobre Docker Compose:
  mata un peer, espera, lo revive, y deja instrucciones de qué comparar en
  `metrics/` y en el frontend antes/durante/después.
- `Dockerfile` + `docker-compose.yml`: levanta 3 peers (`peer-seed`, `peer-2`, `peer-3`)
  y `publisher-crime` (Dominio A) sobre una red interna; perfil `air` agrega
  `publisher-air` (Dominio B). Verificado en local con `docker compose up --build`:
  se observó reenvío multi-hop real (`hop_count=2` en peer-2) entre peers no
  conectados directamente.
- `civicmesh/pubsub/run_peer.py`: CLI nuevo para levantar un peer con pub/sub
  (`PubSubPeer`) sin publicar nada propio. Antes solo existía
  `civicmesh/network/run_peer.py` (que solo entiende JOIN/GOSSIP, no reenvía
  pub/sub) y `civicmesh/domains/run_publisher.py` (que exige `--domain`); no había
  forma de levantar un peer "puro" para Compose/Slurm.

- Estructura inicial del proyecto: paquete `civicmesh/`, `tests/unit/`, `tests/integration/`.
- Pipeline de CI (`ci.yml`) con `pytest`: unitarios obligatorios, integración como
  placeholder hasta que existan las capas de gossip/pub-sub (issues #1, #2).
- Protección de la rama `main` (PR obligatorio, 1 aprobación, sin force-push, CI
  requerido una vez que existió la primera corrida verde).
- Issues iniciales por rol (#1-#5) con labels `rol-1` a `rol-5`.
- Los tres agentes de IA (Documentador, Revisor de bugs, Revisor de MR), portados desde
  `distri-lab-1` y adaptados al dominio de CivicMesh (heurísticas de `should_forward`
  sin TTL/prioridad y de generadores sin `seed`, en vez de las de CUDA del Lab 2 previo).

### Fixed

- `Makefile`: usar `python -m pytest` en vez de `pytest` a secas, porque el import de
  `civicmesh` fallaba en CI (el cwd no queda en `sys.path` con la invocación directa).
- `.gitignore` reemplazado (traía un template de Dynamics 365 Business Central).
