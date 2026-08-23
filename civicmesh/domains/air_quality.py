import csv
import random

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from civicmesh.domains.common import (
    mean_rumor,
    stable_seed,
)

from civicmesh.domains.config import (
    AirPerceptionConfig,
)


@dataclass(frozen=True)
class AirQualitySample:
    timestamp: str
    commune: str
    pm2_5: float
    pm10: float
    latitude: float
    longitude: float
    source: str

    def to_payload(self):
        return {
            "domain": "air_quality",
            "commune": self.commune,
            "timestamp": self.timestamp,
            "pm2_5": self.pm2_5,
            "pm10": self.pm10,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "source": self.source,
        }


def load_air_quality_csv(path):

    samples = []

    with Path(path).open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            samples.append(
                AirQualitySample(
                    timestamp=row["timestamp"],
                    commune=row["commune"],
                    pm2_5=float(
                        row["pm2_5"]
                    ),
                    pm10=float(
                        row["pm10"]
                    ),
                    latitude=float(
                        row["latitude"]
                    ),
                    longitude=float(
                        row["longitude"]
                    ),
                    source=row["source"],
                )
            )

    return sorted(
        samples,
        key=lambda sample: (
            sample.commune,
            sample.timestamp,
        ),
    )


class AirQualityReplay:

    def __init__(
        self,
        samples,
        commune,
    ):
        self.commune = commune

        self.samples = [
            sample
            for sample in samples
            if sample.commune == commune
        ]

        if not self.samples:
            raise ValueError(
                f"no samples for {commune}"
            )

        self._index = 0

    def next_sample(self):

        if self._index >= len(
            self.samples
        ):
            raise StopIteration

        sample = self.samples[
            self._index
        ]

        self._index += 1

        return sample

    def reset(self):
        self._index = 0


class AirPerceptionModel:

    def __init__(
        self,
        commune,
        config: AirPerceptionConfig,
        seed,
    ):
        self.commune = commune
        self.config = config

        # M_c(0) = 0
        self.memory = 0.0

        self._rng = random.Random(
            stable_seed(
                seed,
                "air-perception",
                commune,
            )
        )

    def step(
        self,
        value,
        gossip_values: Iterable[float],
        timestamp,
    ):

        gossip = mean_rumor(
            gossip_values
        )

        previous_memory = self.memory

        # u(t) = max(v(t), M(t-1))
        stimulus = max(
            float(value),
            previous_memory,
        )

        # M(t)
        self.memory = (
            self.config.alpha
            * previous_memory
            + (1 - self.config.alpha)
            * stimulus
        )

        epsilon = self._rng.gauss(
            0,
            self.config.sigma_epsilon,
        )

        # P(t)
        perception = (
            float(value)
            + self.config.gamma
            * (
                self.memory
                - float(value)
            )
            + self.config.delta
            * gossip
            + epsilon
        )

        perception = min(
            self.config.clip_max,
            max(
                self.config.clip_min,
                perception,
            ),
        )

        return {
            "domain": "air_quality",
            "commune": self.commune,
            "timestamp": timestamp,
            "ground_truth": float(value),
            "memory": self.memory,
            "gossip": gossip,
            "perception": perception,
        }
