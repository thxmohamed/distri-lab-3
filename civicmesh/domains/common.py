from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Iterable


def stable_seed(base_seed: int, *parts: str) -> int:
    text = ":".join([str(base_seed), *parts])
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def mean_rumor(values: Iterable[float]) -> float:
    items = [float(value) for value in values]
    return sum(items) / len(items) if items else 0.0


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)

    z = math.exp(value)
    return z / (1.0 + z)


def poisson_sample(
    mean: float,
    rng: random.Random,
) -> int:

    if mean < 0:
        raise ValueError(
            "Poisson mean cannot be negative"
        )

    if mean == 0:
        return 0

    limit = math.exp(-mean)
    product = 1.0
    count = 0

    while product > limit:
        count += 1
        product *= rng.random()

    return count - 1
