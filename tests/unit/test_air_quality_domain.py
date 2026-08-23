from pathlib import Path

from civicmesh.domains.air_quality import (
    AirPerceptionModel,
    AirQualityReplay,
    load_air_quality_csv,
)

from civicmesh.domains.config import (
    AirPerceptionConfig,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "air_quality_sample.csv"
)


def test_air_replay():

    samples = load_air_quality_csv(
        FIXTURE
    )

    replay = AirQualityReplay(
        samples,
        "estacion-central",
    )

    first = replay.next_sample()
    second = replay.next_sample()

    assert first.pm2_5 == 18.0
    assert second.pm2_5 == 20.0

    assert (
        first.source
        == "open-meteo"
    )

def test_air_perception_same_seed():

    config = AirPerceptionConfig(
        alpha=0.85,
        gamma=0.6,
        delta=0.3,
        sigma_epsilon=2.0,
    )

    first = AirPerceptionModel(
        "estacion-central",
        config,
        seed=123,
    )

    second = AirPerceptionModel(
        "estacion-central",
        config,
        seed=123,
    )

    sequence_a = [
        first.step(
            value=20 + i,
            gossip_values=[10.0],
            timestamp=str(i),
        )
        for i in range(10)
    ]

    sequence_b = [
        second.step(
            value=20 + i,
            gossip_values=[10.0],
            timestamp=str(i),
        )
        for i in range(10)
    ]

    assert sequence_a == sequence_b
