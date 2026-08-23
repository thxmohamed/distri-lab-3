from collections import defaultdict

from civicmesh.pubsub.message import (
    PubSubMessage,
)


class RumorBuffer:

    def __init__(self):
        self._values = defaultdict(list)

    def push(
        self,
        topic,
        value,
    ):
        self._values[topic].append(
            float(value)
        )

    def consume(self, topic):
        return self._values.pop(
            topic,
            [],
        )

    def record_message(
        self,
        message: PubSubMessage,
        own_peer_id=None,
    ):

        if message.channel != "subjective":
            return

        # No considerar como rumor
        # la percepción propia.
        if (
            own_peer_id is not None
            and message.origin
            == own_peer_id
        ):
            return

        perception = (
            message.payload.get(
                "perception"
            )
        )

        if perception is None:
            return

        self.push(
            message.topic,
            perception,
        )
