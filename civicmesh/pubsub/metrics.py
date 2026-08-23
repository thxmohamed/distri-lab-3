from dataclasses import asdict, dataclass


@dataclass
class PubSubMetrics:
    published: int = 0
    received: int = 0
    delivered: int = 0
    forwarded: int = 0
    dropped_duplicate: int = 0

    def snapshot(self) -> dict[str, int]:
        return asdict(self)