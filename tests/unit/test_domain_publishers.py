from pathlib import Path

from civicmesh.domains import (
    AirPerceptionModel,
    AirQualityPublisher,
    AirQualityReplay,
    CrimeGenerator,
    CrimePerceptionModel,
    CrimePublisher,
    load_air_quality_csv,
    load_domain_config,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "air_quality_sample.csv"
)


def test_crime_publisher():

    config = load_domain_config()

    published = []

    def publish(topic, channel, payload):
        published.append(
            (topic, channel, payload)
        )

    publisher = CrimePublisher(
        commune="estacion-central",

        generator=CrimeGenerator(
            config.crime_rates,
            config.seed,
            config.delta_t,
        ),

        perception=CrimePerceptionModel(
            "estacion-central",
            config.crime_perception,
            config.seed,
        ),

        publish=publish,

        rumor_provider=lambda topic: [],
    )

    publisher.tick("t1")

    channels = [
        item[1]
        for item in published
    ]

    assert channels == [
        "objective",
        "objective",
        "subjective",
    ]


def test_air_quality_publisher():

    config = load_domain_config()

    samples = load_air_quality_csv(
        FIXTURE
    )

    published = []

    def publish(topic, channel, payload):
        published.append(
            (topic, channel, payload)
        )

    publisher = AirQualityPublisher(
        commune="estacion-central",

        replay=AirQualityReplay(
            samples,
            "estacion-central",
        ),

        perception=AirPerceptionModel(
            "estacion-central",
            config.air_perception,
            config.seed,
        ),

        publish=publish,

        rumor_provider=lambda topic: [],
    )

    publisher.tick()

    assert [
        item[1]
        for item in published
    ] == [
        "objective",
        "subjective",
    ]

    assert (
        published[0][2]["pm2_5"]
        == 18.0
    )
