# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/), y el
proyecto usa [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Added

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
