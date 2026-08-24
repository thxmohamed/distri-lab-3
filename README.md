# CivicMesh

Framework P2P de gossip + publish/subscribe geográfico para monitoreo ciudadano
distribuido, instanciado en dos dominios (delitos y calidad del aire) que separan un
canal objetivo (ground truth) de un canal subjetivo (percepción), sobre la misma
infraestructura de comunicación.

Laboratorio 3 — Sistemas Distribuidos y Paralelos, DIINF, Universidad de Santiago de
Chile, Semestre 1-2026.

## Roles del equipo

| Nombre | Rol | Responsabilidades |
|---|---|---|
| Macarena García | Rol 1 — Capa de Red / Gossip | Membresía, descubrimiento, tolerancia a fallos |
| Sebastián del Solar | Rol 2 — Capa Pub/Sub | Tópicos, suscripciones, `should_forward`, fanout |
| Camila Lagos | Rol 3 — Datos | Ingesta/cache Dominio B (SINCA/Open-Meteo), generadores Poisson y percepción |
| Giuseppe Cavallieri | Rol 4 — Analítica y Estadística | Métricas de convergencia/divergencia, frontend, experimentos de caída/partición |
| Mohamed Al-Marzuk | Rol 5 — CI/CD, Git y agentes | Pipeline CI, Docker/Compose, ramas/issues/MR, scripts Slurm, los tres agentes de IA, README |

> Estado: proyecto recién iniciado. Cada sección de este README se irá completando a
> medida que avancen los issues [#1](https://github.com/thxmohamed/distri-lab-3/issues/1)-[#5](https://github.com/thxmohamed/distri-lab-3/issues/5).

## Flujo Git

- Rama `main` protegida: sin push directo, merge solo vía pull request, 1 aprobación
  requerida, conversaciones deben resolverse, sin force-push.
- Ramas de trabajo: `feature/<nombre>` para funcionalidad nueva, `fix/<nombre>` para
  correcciones. Cada PR referencia al menos un issue (`Closes #N` o `Refs #N`).
- Labels de rol: `rol-1` a `rol-5`. Labels adicionales: `bug`, `documentation`, `agent`,
  `infraestructure`.
- `CHANGELOG.md` sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## Estructura de archivos (actual)

```
distri-lab-3/
├── .github/
│   └── workflows/
│       ├── ci.yml                   # pytest: unitarios (obligatorio) + integración
│       ├── agent-documentation.yml
│       ├── agent-bug-review.yml
│       └── agent-mr-review.yml
├── civicmesh/
│   ├── network/            # Rol 1: membresía/gossip (Peer, Membership, FailureDetector)
│   │   ├── peer.py         #   entiende JOIN/GOSSIP únicamente
│   │   └── run_peer.py     #   CLI: peer solo-gossip (no relay de pub/sub)
│   ├── pubsub/              # Rol 2: tópicos, should_forward, TTL/prioridad/fanout
│   │   ├── network_adapter.py  # PubSubPeer(Peer): agrega manejo de mensajes PUBSUB
│   │   └── run_peer.py         # CLI: peer con pub/sub -- el que usa docker-compose/Slurm
│   ├── domains/             # Rol 3: generadores + replay (Sección 4.3)
│   │   ├── crime.py / air_quality.py / rumors.py
│   │   └── run_publisher.py    # CLI: publicador de un dominio en una comuna
│   ├── analytics/           # Rol 4: convergencia/divergencia + writer de métricas
│   │   ├── convergence.py      # perception_gap() y peer_convergence() (Sección 4.4)
│   │   ├── state.py            # estado local por (topic, channel)
│   │   ├── writer.py           # vuelca snapshots JSONL a metrics/ (Sección 5.2)
│   │   └── delivery.py         # delivery_function que engancha todo lo anterior
│   └── frontend/            # Rol 4: frontend mínimo de estadísticas (Sección 5.4)
│       └── app.py               # Streamlit: lee metrics/*.jsonl de un run_id
├── config/
│   ├── domains.yaml         # seed, tasas de delitos, params de percepción, comunas
│   └── pubsub.yaml          # TTL/prioridad/fanout por canal (objetivo/subjetivo)
├── data/air_quality/         # dataset de Open-Meteo cacheado (Apéndice A)
├── scripts/
│   ├── agents/                # Los tres agentes de IA (ver sección Agentes de IA)
│   │   ├── documentador.md / bug-reviewer.md / mr-reviewer.md
│   │   └── run_ollama.sh / ollama_generate.py / apply_edits.py / parse_mr_response.py
│   ├── analytics/
│   │   └── run_partition_experiment.sh  # experimento de caída/partición (Compose)
│   ├── data/download_open_meteo.py
│   └── slurm/                # sbatch/srun para el clúster DIINF (Sección 5)
│       ├── peers.sbatch / publishers.sbatch
│       ├── start_peer.sh / start_publisher.sh / start_frontend.sh
│       └── README.md            # orden de arranque, túnel SSH, experimento de caída
├── tests/
│   ├── unit/
│   └── integration/
├── Dockerfile
├── docker-compose.yml       # ≥3 peers + publicador(es) sobre una red interna
├── requirements.txt
├── pytest.ini
├── Makefile
├── CHANGELOG.md
└── README.md
```

## Cómo correr los tests

```bash
make install
make test            # unitarios + integración
make test-unit        # solo unitarios
make test-integration # solo integración
```

Equivalente directo: `python -m pytest tests/unit -q` / `python -m pytest tests/integration -q`
(con `pytest` a secas en vez de `python -m pytest`, el import del paquete `civicmesh` falla
porque el directorio del repo no queda en `sys.path`).

## Docker / Docker Compose

```bash
docker compose build                    # primera vez / tras tocar requirements.txt: ~3 min
docker compose up -d                    # 3 peers + publicador de delitos (Dominio A) + frontend
docker compose --profile air up -d      # además, publicador de aire (Dominio B)
docker compose down                     # o --profile air down si se levantó con ese perfil
```

> **Por qué `build` separado de `up`**: la imagen instala `streamlit`+`pandas` (para el
> frontend, Rol 4) además de las dependencias livianas de los peers, así que el primer
> build tarda bastante (~3 min) en descargarlas. Si se usa `docker compose up --build`
> directo y el build no alcanza a terminar (o el runner tiene poco ancho de banda),
> Compose puede terminar intentando *pull* de una imagen `civicmesh:local` que nunca se
> construyó, y falla con `pull access denied` (no existe un repo público con ese nombre).
> Separar los dos pasos evita esa carrera. Si de todos modos ves ese error: `docker
> compose build` de nuevo y revisa que termine con `Built` antes de hacer `up`.

Levanta `peer-seed` (bootstrap), `peer-2` y `peer-3` (hacen `JOIN` contra `peer-seed`),
`publisher-crime` (comuna `estacion-central`) y el `frontend` (Rol 4, puerto 8501). Los
peers **no** están conectados directamente entre sí más que a través del seed: los
mensajes de `publisher-crime` se propagan al resto vía `should_forward`
(TTL/prioridad/fanout de `civicmesh/pubsub`), no por conexión directa — se puede
confirmar en los logs (`docker compose logs peer-2`) porque los mensajes que no
vinieron del seed llegan con `hop_count=2`.

> **Nota de diseño**: `civicmesh.network.run_peer` (Rol 1) solo entiende mensajes
> `JOIN`/`GOSSIP` -- no reenvía pub/sub. El proceso que corre en Compose/Slurm como
> "peer" es `civicmesh.pubsub.run_peer`, que instancia `PubSubPeer` (Rol 1 + Rol 2
> integrados). Se agregó como CLI nuevo porque antes solo `run_publisher.py` instanciaba
> `PubSubPeer`, y no existía forma de levantar un peer "puro" (sin publicar nada) que
> igual pudiera suscribirse y reenviar.

## Métricas, frontend y experimento de partición (Rol 4)

### Convención de `metrics/`

El bus de configuración/métricas entre Slurm (o Compose/local) y el
frontend es el filesystem compartido, bajo
`$CIVICMESH_RUNS/<run_id>/metrics/`. `civicmesh.pubsub.run_peer` acepta dos
flags nuevos para activar esto (si no se pasan, el peer solo imprime por
stdout como antes):

```bash
python -m civicmesh.pubsub.run_peer --id peer-A --port 6001 \
  --subscribe estacion-central \
  --run-id mi-corrida          # arma $CIVICMESH_RUNS/mi-corrida/metrics/
  # o, para fijar la ruta directo:
  # --metrics-dir ./runs/mi-corrida/metrics
```

`CIVICMESH_RUNS` por defecto es `./runs` si la variable de entorno no está
seteada (útil para correr localmente sin Slurm ni Compose). Cada peer
escribe su propio `metrics/<peer_id>.jsonl`, un JSON por línea, con el
snapshot de cada mensaje entregado: `topic`, `channel`, `domain`,
`commune`, `value` (el dato relevante del canal), y `divergence`
(`|percepción - realidad|`, solo en el canal subjetivo).

En `docker-compose.yml` los 3 peers ya corren con `--run-id compose` y
montan `./runs:/civicmesh-runs`, así que basta con `docker compose up
--build` para tener métricas reales en `./runs/compose/metrics/` del host.

### Frontend de estadísticas

```bash
# Local (fuera de Compose), apuntando a una corrida existente:
CIVICMESH_RUNS=./runs RUN_ID=mi-corrida streamlit run civicmesh/frontend/app.py

# Vía Docker Compose (ya incluido como servicio `frontend`):
docker compose build && docker compose up -d   # levanta también el frontend en :8501
```

Abrir `http://localhost:8501`. Muestra las tres vistas mínimas de la
Sección 5.4: estado por tópico × canal, brecha percepción-realidad por
comuna, y convergencia entre peers del canal objetivo (dispersión de los
valores que cada peer ve para el mismo tópico/timestamp).

### Experimento de caída/partición

Es un script bash (`.sh`): en Windows correrlo desde una terminal **Git
Bash** (clic derecho en la carpeta del repo → "Git Bash Here"), no desde
PowerShell/cmd. Si preferís quedarte en PowerShell, invocá bash a mano:
`bash scripts/analytics/run_partition_experiment.sh`.

```bash
docker compose build && docker compose up -d
./scripts/analytics/run_partition_experiment.sh   # mata peer-3, espera, lo revive
```

El script mata un contenedor peer a mitad de la corrida (`docker kill`),
espera, y lo revive con `docker compose up -d`. Compara
`metrics/peer-*.jsonl` (o la tabla de convergencia del frontend)
antes/durante/después.

## Clúster DIINF (Slurm)

```bash
sinfo                                            # confirmar nombres de partición
export CIVICMESH_RUNS=/home/$USER/civicmesh-runs
sbatch --partition=<CPU> scripts/slurm/peers.sbatch        # -> "Submitted batch job 12345"
export RUN_ID=12345
sbatch --partition=<GPU> scripts/slurm/publishers.sbatch
```

2 hosts CPU corren los peers (`peers.sbatch`, 2 por host); 2 hosts GPU —solo su CPU, sin
CUDA— corren los publicadores y el frontend (`publishers.sbatch`). Los dos jobs se
coordinan por `$CIVICMESH_RUNS/$RUN_ID/hostfile.txt` en el shared FS (Sección 5.2/5.3 del
enunciado), no por variables internas de Slurm entre jobs — mismo mecanismo que ya usan
Compose/local, solo que ahí `--run-id` es `compose`/manual en vez de `$SLURM_JOB_ID`.

Sin VPN a DIINF, esto se corrió de punta a punta (peers + publicadores + frontend +
experimento de partición con `scancel`) contra un `slurm-wlm` real montado en WSL2, no
una simulación — specs de esa máquina, qué es evidencia real y qué falta correr en
DIINF de verdad, en [`scripts/slurm/README.md`](scripts/slurm/README.md).

## Agentes de IA

Igual que en `distri-lab-1` (Lab 1/2 de este mismo curso), el repo corre tres agentes en
CI usando **[Ollama](https://ollama.com/) local, dentro del propio runner de GitHub
Actions**, con el modelo open-source `qwen2.5-coder:7b-instruct-q4_K_M`. Es gratuito y no
depende de ninguna API de terceros ni requiere secrets.

El diseño es "el modelo responde JSON en texto plano → un script determinista valida y
ejecuta la acción" (Ollama no es un agente autónomo con acceso a shell/archivos, es una
llamada de inferencia):

1. El workflow instala Ollama, descarga el modelo (cacheado entre corridas con
   `actions/cache`) y reúne contexto (README/CHANGELOG, diffs recientes, diff del PR) en
   un archivo de texto.
2. [`scripts/agents/run_ollama.sh`](scripts/agents/run_ollama.sh) levanta `ollama serve`
   y llama a `/api/generate` con `format: "json"`, usando el system prompt de
   `scripts/agents/*.md` y el contexto como `prompt`.
3. [`scripts/agents/apply_edits.py`](scripts/agents/apply_edits.py) (documentador y
   revisor de bugs) y [`scripts/agents/parse_mr_response.py`](scripts/agents/parse_mr_response.py)
   (revisor de MR) extraen el JSON de la respuesta de forma tolerante, y degradan de
   forma segura (`action: none` / `classification: human_review`) si no encuentran nada
   parseable.
4. Un "fix mecánico" solo se aplica si el archivo está en una lista blanca y cada
   reemplazo de texto propuesto aparece **exactamente una vez** en el archivo; si no,
   degrada automáticamente a abrir un issue.

| Agente | Workflow | Prompt | Frecuencia | Criterio mecánico (arregla solo) | Criterio humano (solo comenta/issue) |
|---|---|---|---|---|---|
| Documentador | [`agent-documentation.yml`](.github/workflows/agent-documentation.yml) | [`documentador.md`](scripts/agents/documentador.md) | Semanal (lunes) + al fusionar a `main` + manual | Entrada de CHANGELOG faltante en `CHANGELOG.md` | Enlaces rotos en `README.md`, o explicar decisiones de arquitectura |
| Revisor de bugs | [`agent-bug-review.yml`](.github/workflows/agent-bug-review.yml) | [`bug-reviewer.md`](scripts/agents/bug-reviewer.md) | Diaria (cron) + manual | Fixture de test desalineado — solo si el archivo está bajo `tests/` | `should_forward` sin TTL/prioridad visible, generador sin `seed` documentada, o cualquier cambio a las fórmulas del canal objetivo/subjetivo (Sección 4.3) |
| Revisor de MR | [`agent-mr-review.yml`](.github/workflows/agent-mr-review.yml) | [`mr-reviewer.md`](scripts/agents/mr-reviewer.md) | Al terminar el CI de cada PR (`workflow_run` sobre el workflow `CI`) | Solo docs/formato/tests/infra en verde, vinculado a un issue | Cambia protocolo (gossip, `should_forward`, TTL/fanout) o fórmulas del canal subjetivo sin issue, o CI en rojo |

Reglas comunes a los tres agentes:

- Nunca pushean directo a `main` (la protección de rama lo bloquearía igualmente).
- El documentador y el revisor de bugs solo abren PRs mecánicos vía rama
  `agent/<slug>-<run_id>` + `gh pr create`, etiquetados `agent:auto-fix`; para hallazgos
  que requieren criterio, solo abren un issue con `Requiere intervención humana: <motivo>`.
- El revisor de MR **nunca** ejecuta `gh pr merge`: solo comenta la clasificación del PR.
- El documentador y el revisor de bugs se limitan a **1 issue abierto propio a la vez**
  (label `agent`+`documentation` o `agent`+`bug`), para no inundar el tablero si el mismo
  hallazgo (o una alucinación) se repite en corridas sucesivas.

### Requisitos y límites conocidos

- **Sin secrets**: no se necesita ninguna API key. Sí se necesita que
  Settings → Actions → General → Workflow permissions tenga marcado **"Allow GitHub
  Actions to create and approve pull requests"** — sin esto, el documentador y el revisor
  de bugs fallan en `gh pr create` con `GitHub Actions is not permitted to create or
  approve pull requests` cuando encuentran un fix mecánico (y degradan a issue).
- **Sin GPU en el runner gratuito**: la inferencia corre en CPU y puede tardar varios
  minutos por respuesta. Cada workflow le da `timeout-minutes: 35` al paso de inferencia.
  Si el job se cae por timeout, bajar `OLLAMA_MODEL` a `qwen2.5-coder:3b`.
- **Cache del modelo obligatorio**: sin `actions/cache` sobre `~/.ollama`, cada corrida
  descargaría el modelo (~4-5 GB) de nuevo.
- Para iterar más rápido, corran Ollama localmente (`ollama pull qwen2.5-coder:7b-instruct-q4_K_M`
  + `bash scripts/agents/run_ollama.sh scripts/agents/<agente>.md <archivo-de-contexto> <salida>`)
  antes de probar contra CI.

## Próximos pasos

- Correr los scripts Slurm contra el clúster DIINF real (issue #5): ya se validaron de
  punta a punta contra un Slurm real en local (WSL2, ver `scripts/slurm/README.md`),
  falta la corrida "oficial" en DIINF — alguien del equipo con VPN debería repetirla y
  ajustar lo que `sinfo`/`sacct` digan que no calza (nombres de partición, `-w
  <hostname>` con FQDN si hace falta).
- Con esa corrida real, dejar evidencia del experimento de caída/partición en DIINF
  (Sección 8 lo prefiere ahí; en Compose/local ya está cubierto).
