from __future__ import annotations

import time

from civicmesh.analytics.convergence import perception_gap
from civicmesh.analytics.state import AnalyticsState
from civicmesh.analytics.writer import MetricsWriter
from civicmesh.pubsub.message import PubSubMessage


def _extract_value(message: PubSubMessage):
    """
    Extrae el valor numérico relevante del payload según el canal.

    Subjetivo: siempre "perception" (Sección 4.3, ambos dominios).
    Objetivo: "count" en delitos; pm2_5 en aire (mismo contaminante
    que usa por defecto el modelo de percepción del publicador).
    """

    payload = message.payload

    if message.channel == "subjective":
        return payload.get("perception")

    if "count" in payload:
        return payload["count"]

    return payload.get("pm2_5")


def build_analytics_delivery_function(
    peer_id: str,
    metrics_dir,
):
    """
    Reemplaza al delivery_function de solo-log de run_peer.py.

    Además de recibir el mensaje, actualiza el estado local del peer
    y escribe un snapshot a metrics/ para que el frontend (Sección 5.4)
    y los experimentos de partición puedan leerlo.
    """

    state = AnalyticsState()
    writer = MetricsWriter(metrics_dir, peer_id)

    def deliver(message: PubSubMessage) -> None:
        payload = message.payload
        value = _extract_value(message)
        timestamp = payload.get("timestamp")

        state.record(
            message.topic,
            message.channel,
            value,
            timestamp,
        )

        divergence = None

        if message.channel == "subjective":
            ground_truth = payload.get("ground_truth")
            perception = payload.get("perception")

            if (
                ground_truth is not None
                and perception is not None
            ):
                divergence = perception_gap(
                    ground_truth,
                    perception,
                )

        snapshot = {
            "peer_id": peer_id,
            "recorded_at": time.time(),
            "message_id": message.message_id,
            "topic": message.topic,
            "channel": message.channel,
            "domain": payload.get("domain"),
            "commune": payload.get("commune"),
            "origin": message.origin,
            "hop_count": message.hop_count,
            "timestamp": timestamp,
            "value": value,
            "divergence": divergence,
        }

        writer.write(snapshot)

    return deliver
