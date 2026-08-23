from collections.abc import Iterable

from civicmesh.pubsub.config import get_channel_policy
from civicmesh.pubsub.message import PubSubMessage


def should_forward(
    msg: PubSubMessage,
    topic: str,
    local_view: Iterable[str],
) -> bool:
    """
    Decide si un mensaje debe seguir propagándose.

    Un mensaje se reenvía solamente si:
    - pertenece al tópico esperado;
    - todavía tiene TTL disponible;
    - no superó el máximo de saltos del canal;
    - cumple la prioridad mínima de su canal;
    - existen peers disponibles en la vista local.
    """

    if msg.topic != topic:
        return False

    if msg.ttl <= 0:
        return False

    policy = get_channel_policy(msg.channel)

    if msg.hop_count >= policy.ttl:
        return False

    if msg.priority < policy.priority:
        return False

    peers = list(local_view)

    if not peers:
        return False

    return True


def select_forward_targets(
    local_view: Iterable[str],
    fanout: int,
) -> list[str]:
    """
    Selecciona como máximo 'fanout' peers de la vista local.
    """

    if fanout <= 0:
        raise ValueError("fanout must be greater than zero")

    peers = list(dict.fromkeys(local_view))

    return peers[:fanout]