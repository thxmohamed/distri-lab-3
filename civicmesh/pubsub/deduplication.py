from collections import deque


class MessageTracker:
    def __init__(self, max_size: int = 1000) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be greater than zero")

        self._max_size = max_size
        self._seen_ids: set[str] = set()
        self._order: deque[str] = deque()

    def has_seen(self, message_id: str) -> bool:
        return message_id in self._seen_ids

    def mark_seen(self, message_id: str) -> None:
        if not message_id:
            raise ValueError("message_id cannot be empty")

        if message_id in self._seen_ids:
            return

        if len(self._seen_ids) >= self._max_size:
            oldest_id = self._order.popleft()
            self._seen_ids.remove(oldest_id)

        self._seen_ids.add(message_id)
        self._order.append(message_id)

    def check_and_mark(self, message_id: str) -> bool:
        if self.has_seen(message_id):
            return False

        self.mark_seen(message_id)
        return True

    def size(self) -> int:
        return len(self._seen_ids)