import random
from collections.abc import Iterable

from civicmesh.domains.common import (
    mean_rumor,
    poisson_sample,
    sigmoid,
    stable_seed,
)

from civicmesh.domains.config import (
    CrimePerceptionConfig,
)


class CrimeGenerator:

    def __init__(
        self,
        rates,
        seed,
        delta_t=1.0,
    ):
        self.rates = rates
        self.seed = seed
        self.delta_t = delta_t
        self._rngs = {}

    def _rng(
        self,
        commune,
        crime_type,
    ):
        key = (commune, crime_type)

        if key not in self._rngs:
            self._rngs[key] = random.Random(
                stable_seed(
                    self.seed,
                    "crime",
                    commune,
                    crime_type,
                )
            )

        return self._rngs[key]

    def generate_step(
        self,
        commune,
        timestamp,
    ):

        if commune not in self.rates:
            raise ValueError(
                f"unknown commune: {commune}"
            )

        events = []

        for crime_type, rate in (
            self.rates[commune].items()
        ):
            count = poisson_sample(
                mean=rate * self.delta_t,
                rng=self._rng(
                    commune,
                    crime_type,
                ),
            )

            events.append({
                "domain": "crime",
                "commune": commune,
                "crime_type": crime_type,
                "count": count,
                "timestamp": timestamp,
            })

        return events


class CrimePerceptionModel:

    def __init__(
        self,
        commune,
        config: CrimePerceptionConfig,
        seed,
    ):
        self.commune = commune
        self.config = config

        # M_c(0) = 0
        self.memory = 0.0

        self._rng = random.Random(
            stable_seed(
                seed,
                "crime-perception",
                commune,
            )
        )

    def step(
        self,
        ground_truth,
        gossip_values: Iterable[float],
        timestamp,
    ):

        gossip = mean_rumor(
            gossip_values
        )

        # M_c(t)
        self.memory = (
            self.config.alpha
            * self.memory
            + (1 - self.config.alpha)
            * ground_truth
        )

        epsilon = self._rng.gauss(
            0,
            self.config.sigma_epsilon,
        )

        # Z_c(t)
        z = (
            self.config.beta0
            + self.config.beta1
            * self.memory
            + self.config.beta2
            * gossip
            + epsilon
        )

        # P_c(t)
        perception = sigmoid(z)

        return {
            "domain": "crime",
            "commune": self.commune,
            "timestamp": timestamp,
            "ground_truth": float(
                ground_truth
            ),
            "memory": self.memory,
            "gossip": gossip,
            "perception": perception,
        }
