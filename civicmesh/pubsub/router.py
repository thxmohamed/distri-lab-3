from collections.abc import Callable, Iterable
from typing import Any

from civicmesh.pubsub.config import get_channel_policy
from civicmesh.pubsub.deduplication import MessageTracker
from civicmesh.pubsub.forwarding import (
    select_forward_targets,
    should_forward,
)
from civicmesh.pubsub.message import PubSubMessage
from civicmesh.pubsub.metrics import PubSubMetrics
from civicmesh.pubsub.subscriptions import SubscriptionManager


LocalViewProvider = Callable[[], Iterable[str]]
SendFunction = Callable[[str, PubSubMessage], None]
DeliveryFunction = Callable[[PubSubMessage], None]


class PubSubRouter:
    def __init__(
        self,
        node_id: str,
        local_view_provider: LocalViewProvider,
        send_function: SendFunction,
        delivery_function: DeliveryFunction,
        geography: dict[str, list[str]] | None = None,
        tracker_size: int = 1000,
    ) -> None:
        if not node_id:
            raise ValueError("node_id cannot be empty")

        self.node_id = node_id
        self._local_view_provider = local_view_provider
        self._send_function = send_function
        self._delivery_function = delivery_function

        self.subscriptions = SubscriptionManager(geography)
        self.tracker = MessageTracker(max_size=tracker_size)
        self.metrics = PubSubMetrics()

    def subscribe(
        self,
        topic: str,
        include_neighbors: bool = False,
    ) -> None:
        self.subscriptions.subscribe(
            topic,
            include_neighbors=include_neighbors,
        )

    def unsubscribe(self, topic: str) -> None:
        self.subscriptions.unsubscribe(topic)

    def publish(
        self,
        topic: str,
        channel: str,
        payload: dict[str, Any],
    ) -> PubSubMessage:
        self.metrics.published += 1

        policy = get_channel_policy(channel)

        message = PubSubMessage(
            topic=topic,
            channel=channel,
            payload=payload,
            origin=self.node_id,
            ttl=policy.ttl,
            priority=policy.priority,
        )

        self.tracker.mark_seen(message.message_id)

        if self.subscriptions.is_subscribed(topic):
            self.metrics.delivered += 1
            self._delivery_function(message)

        self._forward(message)

        return message

    def receive(
        self,
        message: PubSubMessage,
        sender: str | None = None,
    ) -> bool:
        self.metrics.received += 1

        if not self.tracker.check_and_mark(message.message_id):
            self.metrics.dropped_duplicate += 1
            return False

        if self.subscriptions.is_subscribed(message.topic):
            self.metrics.delivered += 1
            self._delivery_function(message)

        self._forward(
            message,
            sender=sender,
        )

        return True

    def _forward(
        self,
        message: PubSubMessage,
        sender: str | None = None,
    ) -> list[str]:
        local_view = list(self._local_view_provider())

        eligible_peers = [
            peer
            for peer in local_view
            if peer != self.node_id
            and peer != sender
            and peer != message.origin
        ]

        if not should_forward(
            message,
            message.topic,
            eligible_peers,
        ):
            return []

        policy = get_channel_policy(message.channel)

        targets = select_forward_targets(
            eligible_peers,
            policy.fanout,
        )

        if not targets:
            return []

        self.metrics.forwarded += len(targets)

        forwarded_message = message.forwarded_copy()

        for target in targets:
            self._send_function(
                target,
                forwarded_message,
            )

        return targets