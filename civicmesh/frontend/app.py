from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# `streamlit run civicmesh/frontend/app.py` ejecuta este archivo directo
# (no como `python -m`), así que Python solo agrega la carpeta del propio
# script a sys.path, no la raíz del repo. Sin esto, "import civicmesh..."
# falla con ModuleNotFoundError.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2])
)

import pandas as pd
import streamlit as st

from civicmesh.analytics.convergence import peer_convergence


METRICS_COLUMNS = [
    "peer_id",
    "recorded_at",
    "topic",
    "channel",
    "domain",
    "commune",
    "value",
    "divergence",
]


def load_snapshots(metrics_dir: Path) -> pd.DataFrame:
    """
    Lee todos los metrics/<peer_id>.jsonl de una corrida (convención
    compartida por FS) y los junta en un único DataFrame.
    """

    rows = []

    if metrics_dir.is_dir():
        for path in sorted(metrics_dir.glob("*.jsonl")):
            for line in path.read_text(
                encoding="utf-8"
            ).splitlines():
                if line.strip():
                    rows.append(json.loads(line))

    if not rows:
        return pd.DataFrame(columns=METRICS_COLUMNS)

    df = pd.DataFrame(rows)

    # recorded_at se guarda en metrics/*.jsonl como epoch (time.time());
    # acá se muestra como fecha/hora legible, no como número crudo.
    df["recorded_at"] = pd.to_datetime(
        df["recorded_at"], unit="s"
    )

    return df


def render_topic_channel_state(df: pd.DataFrame) -> None:
    st.subheader("Estado por tópico x canal")

    if df.empty:
        st.info("Todavía no hay métricas en este run_id.")
        return

    latest = (
        df.sort_values("recorded_at")
        .groupby(["topic", "channel"])
        .last()
        .reset_index()
    )

    st.dataframe(
        latest[
            [
                "topic",
                "channel",
                "domain",
                "commune",
                "value",
                "recorded_at",
            ]
        ]
    )


def render_perception_gap(df: pd.DataFrame) -> None:
    st.subheader("Brecha percepción-realidad (canal subjetivo)")

    subjective = df[
        (df["channel"] == "subjective")
        & df["divergence"].notna()
    ]

    if subjective.empty:
        st.info("Sin eventos del canal subjetivo todavía.")
        return

    for commune, group in subjective.groupby("commune"):
        st.caption(commune)
        st.line_chart(
            group.sort_values("recorded_at").set_index(
                "recorded_at"
            )["divergence"]
        )


def render_peer_convergence(df: pd.DataFrame) -> None:
    st.subheader("Convergencia entre peers (canal objetivo)")

    objective = df[
        (df["channel"] == "objective") & df["value"].notna()
    ]

    if objective.empty:
        st.info("Sin eventos del canal objetivo todavía.")
        return

    rows = [
        {
            "topic": topic,
            "timestamp": timestamp,
            "n_peers": group["peer_id"].nunique(),
            "convergence": peer_convergence(group["value"]),
        }
        for (topic, timestamp), group in objective.groupby(
            ["topic", "timestamp"]
        )
    ]

    convergence_df = pd.DataFrame(rows).sort_values(
        ["topic", "timestamp"]
    )

    st.dataframe(convergence_df)


def main() -> None:
    st.set_page_config(
        page_title="CivicMesh — Métricas", layout="wide"
    )
    st.title("CivicMesh — Frontend de métricas")

    runs_root = Path(
        os.environ.get("CIVICMESH_RUNS", "./runs")
    )
    default_run_id = os.environ.get("RUN_ID", "")

    run_id = st.sidebar.text_input(
        "run_id", value=default_run_id
    )

    if not run_id:
        st.warning(
            "Indica un run_id en la barra lateral "
            "(o la variable de entorno RUN_ID)."
        )
        return

    metrics_dir = runs_root / run_id / "metrics"

    st.sidebar.caption(f"Leyendo desde: {metrics_dir}")

    df = load_snapshots(metrics_dir)

    render_topic_channel_state(df)
    render_perception_gap(df)
    render_peer_convergence(df)


if __name__ == "__main__":
    main()
