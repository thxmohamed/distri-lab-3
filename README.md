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
│       └── ci.yml           # pytest: unitarios (obligatorio) + integración
├── civicmesh/                # Paquete del framework (Rol 1/2) y dominios (Rol 3)
│   └── __init__.py
├── tests/
│   ├── unit/
│   │   └── test_smoke.py
│   └── integration/
│       └── test_placeholder.py   # placeholder hasta que exista la malla real
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

Equivalente directo: `pytest tests/unit -q` / `pytest tests/integration -q`.

## Próximos pasos

- Docker / Docker Compose (issue #5).
- Scripts Slurm + convención `$CIVICMESH_RUNS/<run_id>/` (issue #5).
- Port de los tres agentes de IA (Documentador, Revisor de bugs, Revisor de MR) desde
  `distri-lab-1` (issue #5).
- Framework de gossip (issue #1) y pub/sub (issue #2).
