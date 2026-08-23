import pytest

from civicmesh.domains.config import (
    CrimePerceptionConfig,
)

from civicmesh.domains.crime import (
    CrimeGenerator,
    CrimePerceptionModel,
)


def test_same_seed():

    rates = {
        "estacion-central": {
            "robbery": 0.4,
            "theft": 0.7,
        }
    }

    first = CrimeGenerator(
        rates,
        seed=123,
    )

    second = CrimeGenerator(
        rates,
        seed=123,
    )

    a = [
        first.generate_step(
            "estacion-central",
            str(i),
        )
        for i in range(20)
    ]

    b = [
        second.generate_step(
            "estacion-central",
            str(i),
        )
        for i in range(20)
    ]

    assert a == b


def test_crime_perception():

    config = CrimePerceptionConfig(
        alpha=0.8,
        beta0=-1,
        beta1=0.4,
        beta2=0.8,
        sigma_epsilon=0,
    )

    model = CrimePerceptionModel(
        "estacion-central",
        config,
        seed=123,
    )

    result = model.step(
        ground_truth=5,
        gossip_values=[0.5, 0.7],
        timestamp="t1",
    )

    assert result["memory"] == (
        pytest.approx(1.0)
    )

    assert result["gossip"] == (
        pytest.approx(0.6)
    )

def test_crime_perception_same_seed():

    config = CrimePerceptionConfig(
        alpha=0.8,
        beta0=-1.0,
        beta1=0.4,
        beta2=0.8,
        sigma_epsilon=0.1,
    )

    first = CrimePerceptionModel(
        "estacion-central",
        config,
        seed=123,
    )

    second = CrimePerceptionModel(
        "estacion-central",
        config,
        seed=123,
    )

    sequence_a = [
        first.step(
            ground_truth=3,
            gossip_values=[0.4, 0.6],
            timestamp=str(i),
        )
        for i in range(10)
    ]

    sequence_b = [
        second.step(
            ground_truth=3,
            gossip_values=[0.4, 0.6],
            timestamp=str(i),
        )
        for i in range(10)
    ]

    assert sequence_a == sequence_b
