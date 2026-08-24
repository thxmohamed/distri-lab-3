from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class TopicChannelState:
    """
    Estado local (por peer) de un tópico x canal.

    Guarda una ventana acotada de los últimos eventos entregados:
    suficiente para alimentar al writer sin crecer indefinidamente
    en memoria mientras el peer sigue vivo.
    """

    history: deque = field(
        default_factory=lambda: deque(maxlen=200)
    )
    last_value: float | None = None
    last_timestamp: str | None = None

    def record(self, value, timestamp) -> None:
        self.last_value = value
        self.last_timestamp = timestamp
        self.history.append((timestamp, value))


class AnalyticsState:
    """
    Estado agregado local de un peer.

    Un TopicChannelState por (topic, channel), poblado a medida
    que el delivery_function de analítica recibe mensajes.
    """

    def __init__(self) -> None:
        self._states: dict[
            tuple[str, str], TopicChannelState
        ] = {}

    def get(
        self,
        topic: str,
        channel: str,
    ) -> TopicChannelState:
        key = (topic, channel)

        if key not in self._states:
            self._states[key] = TopicChannelState()

        return self._states[key]

    def record(
        self,
        topic: str,
        channel: str,
        value,
        timestamp,
    ) -> None:
        self.get(topic, channel).record(value, timestamp)

    def snapshot(self) -> dict:
        return {
            f"{topic}:{channel}": {
                "last_value": state.last_value,
                "last_timestamp": state.last_timestamp,
                "history_size": len(state.history),
            }
            for (
                topic,
                channel,
            ), state in self._states.items()
        }
