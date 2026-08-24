import json

from civicmesh.analytics import build_analytics_delivery_function
from civicmesh.pubsub.message import PubSubMessage


def _read_snapshots(metrics_dir, peer_id):

    path = metrics_dir / f"{peer_id}.jsonl"

    return [
        json.loads(line)
        for line in path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]


def test_delivery_writes_objective_crime_snapshot(tmp_path):

    deliver = build_analytics_delivery_function(
        "peer-1",
        tmp_path,
    )

    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={
            "domain": "crime",
            "commune": "estacion-central",
            "crime_type": "robo",
            "count": 3,
            "timestamp": "t1",
        },
        origin="publisher-crime",
        ttl=4,
        priority=1,
    )

    deliver(message)

    snapshots = _read_snapshots(
        tmp_path, "peer-1"
    )

    assert len(snapshots) == 1
    assert snapshots[0]["value"] == 3
    assert snapshots[0]["divergence"] is None
    assert snapshots[0]["channel"] == "objective"


def test_delivery_computes_divergence_for_subjective(tmp_path):

    deliver = build_analytics_delivery_function(
        "peer-1",
        tmp_path,
    )

    message = PubSubMessage(
        topic="estacion-central",
        channel="subjective",
        payload={
            "domain": "crime",
            "commune": "estacion-central",
            "timestamp": "t1",
            "ground_truth": 3.0,
            "memory": 1.5,
            "gossip": 0.0,
            "perception": 0.8,
        },
        origin="publisher-crime",
        ttl=4,
        priority=1,
    )

    deliver(message)

    snapshots = _read_snapshots(
        tmp_path, "peer-1"
    )

    assert snapshots[0]["value"] == 0.8
    assert snapshots[0]["divergence"] == 2.2


def test_delivery_extracts_pm2_5_for_air_quality_objective(tmp_path):

    deliver = build_analytics_delivery_function(
        "peer-1",
        tmp_path,
    )

    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={
            "domain": "air_quality",
            "commune": "estacion-central",
            "timestamp": "t1",
            "pm2_5": 18.0,
            "pm10": 30.0,
            "latitude": -33.45,
            "longitude": -70.66,
            "source": "open-meteo",
        },
        origin="publisher-air",
        ttl=4,
        priority=1,
    )

    deliver(message)

    snapshots = _read_snapshots(
        tmp_path, "peer-1"
    )

    assert snapshots[0]["value"] == 18.0
