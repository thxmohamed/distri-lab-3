# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/), y el
proyecto usa [Semantic Versioning](https://semver.org/lang/es/).

## [Unreleased]

### Added

- Estructura inicial del proyecto: paquete `civicmesh/`, `tests/unit/`, `tests/integration/`.
- Pipeline de CI (`ci.yml`) con `pytest`: unitarios obligatorios, integración como
  placeholder hasta que existan las capas de gossip/pub-sub (issues #1, #2).
- Protección de la rama `main` (PR obligatorio, 1 aprobación, sin force-push).
- Issues iniciales por rol (#1-#5) con labels `rol-1` a `rol-5`.
