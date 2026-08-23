from dataclasses import dataclass
from pathlib import Path

import yaml


DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "domains.yaml"
)


@dataclass(frozen=True)
class CrimePerceptionConfig:
    alpha: float
    beta0: float
    beta1: float
    beta2: float
    sigma_epsilon: float


@dataclass(frozen=True)
class AirPerceptionConfig:
    alpha: float
    gamma: float
    delta: float
    sigma_epsilon: float
    clip_min: float = 0.0
    clip_max: float = 500.0


@dataclass(frozen=True)
class DomainConfig:
    seed: int
    delta_t: float

    crime_rates: dict[str, dict[str, float]]
    crime_perception: CrimePerceptionConfig

    air_perception: AirPerceptionConfig
    air_dataset: str

    air_locations: dict[str, dict[str, float]]
    air_start_date: str
    air_end_date: str


def load_domain_config(
    path=DEFAULT_CONFIG_PATH,
) -> DomainConfig:

    with Path(path).open(
        "r",
        encoding="utf-8",
    ) as file:
        raw = yaml.safe_load(file)

    crime = raw["crime"]
    air = raw["air"]

    cp = crime["perception"]
    ap = air["perception"]

    rates = {
        commune: {
            crime_type: float(rate)
            for crime_type, rate in values.items()
        }
        for commune, values
        in crime["rates"].items()
    }

    locations = {
        commune: {
            "latitude": float(
                values["latitude"]
            ),
            "longitude": float(
                values["longitude"]
            ),
        }
        for commune, values
        in air["locations"].items()
    }

    return DomainConfig(
        seed=int(raw["seed"]),
        delta_t=float(
            raw.get("delta_t", 1.0)
        ),

        crime_rates=rates,

        crime_perception=CrimePerceptionConfig(
            alpha=float(cp["alpha"]),
            beta0=float(cp["beta0"]),
            beta1=float(cp["beta1"]),
            beta2=float(cp["beta2"]),
            sigma_epsilon=float(
                cp["sigma_epsilon"]
            ),
        ),

        air_perception=AirPerceptionConfig(
            alpha=float(ap["alpha"]),
            gamma=float(ap["gamma"]),
            delta=float(ap["delta"]),
            sigma_epsilon=float(
                ap["sigma_epsilon"]
            ),
            clip_min=float(
                ap.get("clip_min", 0)
            ),
            clip_max=float(
                ap.get("clip_max", 500)
            ),
        ),

        air_dataset=air["dataset"],
        air_locations=locations,
        air_start_date=air["start_date"],
        air_end_date=air["end_date"],
    )
