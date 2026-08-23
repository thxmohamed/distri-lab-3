from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


VALID_CHANNELS = {"objective", "subjective"}


@dataclass
class PubSubMessage:
    topic: str
    channel: str
    payload: dict[str, Any]
    origin: str
    ttl: int
    priority: int
    hop_count: int = 0
    message_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if not self.topic:
            raise ValueError("topic cannot be empty")

        if self.channel not in VALID_CHANNELS:
            raise ValueError(
                f"channel must be one of: {sorted(VALID_CHANNELS)}"
            )

        if self.ttl < 0:
            raise ValueError("ttl cannot be negative")

        if self.priority < 0:
            raise ValueError("priority cannot be negative")

        if self.hop_count < 0:
            raise ValueError("hop_count cannot be negative")

    def forwarded_copy(self) -> "PubSubMessage":
        if self.ttl <= 0:
            raise ValueError("message TTL is exhausted")

        return PubSubMessage(
            message_id=self.message_id,
            topic=self.topic,
            channel=self.channel,
            payload=self.payload.copy(),
            origin=self.origin,
            ttl=self.ttl - 1,
            priority=self.priority,
            hop_count=self.hop_count + 1,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "topic": self.topic,
            "channel": self.channel,
            "payload": self.payload.copy(),
            "origin": self.origin,
            "ttl": self.ttl,
            "priority": self.priority,
            "hop_count": self.hop_count,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "PubSubMessage":
        return cls(
            message_id=data["message_id"],
            topic=data["topic"],
            channel=data["channel"],
            payload=data["payload"],
            origin=data["origin"],
            ttl=data["ttl"],
            priority=data["priority"],
            hop_count=data["hop_count"],
        )