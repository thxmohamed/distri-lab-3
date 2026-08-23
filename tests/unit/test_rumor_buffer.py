from civicmesh.domains.rumors import (
    RumorBuffer,
)

from civicmesh.pubsub.message import (
    PubSubMessage,
)


def test_rumor_buffer():

    buffer = RumorBuffer()

    message = PubSubMessage(
        topic="estacion-central",
        channel="subjective",
        payload={
            "perception": 0.7
        },
        origin="peer-b",
        ttl=2,
        priority=50,
    )

    buffer.record_message(
        message,
        own_peer_id="peer-a",
    )

    assert buffer.consume(
        "estacion-central"
    ) == [0.7]

    assert buffer.consume(
        "estacion-central"
    ) == []
