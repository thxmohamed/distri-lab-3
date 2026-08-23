from collections.abc import Iterable, Mapping


class SubscriptionManager:
    def __init__(
        self,
        geography: Mapping[str, Iterable[str]] | None = None,
    ) -> None:
        self._subscriptions: set[str] = set()

        self._geography = {
            topic: set(neighbors)
            for topic, neighbors in (geography or {}).items()
        }

    def subscribe(
        self,
        topic: str,
        include_neighbors: bool = False,
    ) -> None:
        if not topic:
            raise ValueError("topic cannot be empty")

        self._subscriptions.add(topic)

        if include_neighbors:
            neighbors = self._geography.get(topic, set())
            self._subscriptions.update(neighbors)

    def unsubscribe(self, topic: str) -> None:
        self._subscriptions.discard(topic)

    def is_subscribed(self, topic: str) -> bool:
        return topic in self._subscriptions

    def get_subscriptions(self) -> set[str]:
        return self._subscriptions.copy()