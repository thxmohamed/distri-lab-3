from __future__ import annotations

import json
from pathlib import Path


class MetricsWriter:
    """
    Vuelca snapshots de métricas a
    $CIVICMESH_RUNS/<run_id>/metrics/<peer_id>.jsonl (Sección 5.2),
    un JSON por línea para que el frontend los pueda leer en streaming.
    """

    def __init__(self, metrics_dir, peer_id: str) -> None:
        self.path = Path(metrics_dir) / f"{peer_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, snapshot: dict) -> None:
        with self.path.open(
            "a", encoding="utf-8"
        ) as file:
            file.write(
                json.dumps(snapshot, ensure_ascii=False)
            )
            file.write("\n")
