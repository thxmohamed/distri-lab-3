import argparse

import pytest

from civicmesh.pubsub.network_adapter import PubSubPeer
from civicmesh.pubsub.run_peer import (
    build_delivery_function,
    build_parser,
    build_peer,
    resolve_metrics_dir,
    validate_seed_args,
)


def make_args(
    **overrides,
) -> argparse.Namespace:
    values = {
        "peer_id": "peer-A",
        "host": "127.0.0.1",
        "port": 5000,
        "subscribe": [],
        "max_view_size": 10,
        "fanout": 2,
        "gossip_interval": 3.0,
        "random_seed": None,
        "failure_timeout": 10.0,
        "failure_check_interval": 2.0,
        "connection_timeout": 5.0,
        "seed_id": None,
        "seed_host": None,
        "seed_port": None,
        "metrics_dir": None,
        "run_id": None,
    }

    values.update(overrides)

    return argparse.Namespace(**values)


def test_parser_accepts_multiple_subscriptions():
    parser = build_parser()

    args = parser.parse_args(
        [
            "--id",
            "peer-A",
            "--port",
            "5000",
            "--subscribe",
            "estacion-central",
            "--subscribe",
            "santiago",
        ]
    )

    assert args.peer_id == "peer-A"
    assert args.port == 5000

    assert args.subscribe == [
        "estacion-central",
        "santiago",
    ]


def test_seed_arguments_can_be_absent():
    args = make_args()

    validate_seed_args(args)


def test_complete_seed_arguments_are_valid():
    args = make_args(
        seed_id="peer-seed",
        seed_host="127.0.0.1",
        seed_port=6000,
    )

    validate_seed_args(args)


def test_partial_seed_arguments_are_rejected():
    args = make_args(
        seed_id="peer-seed",
    )

    with pytest.raises(ValueError):
        validate_seed_args(args)


def test_build_peer_creates_pubsub_peer():
    args = make_args()

    peer = build_peer(args)

    assert isinstance(
        peer,
        PubSubPeer,
    )

    assert (
        peer.own_info.peer_id
        == "peer-A"
    )

    assert peer.own_info.port == 5000


def test_delivery_function_prints_message(capsys):
    from civicmesh.pubsub.message import PubSubMessage

    deliver = build_delivery_function(
        "peer-B"
    )

    message = PubSubMessage(
        message_id="message-1",
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 5},
        origin="peer-A",
        ttl=2,
        priority=100,
        hop_count=2,
    )

    deliver(message)

    output = capsys.readouterr().out

    assert '"peer_id": "peer-B"' in output
    assert '"topic": "estacion-central"' in output
    assert '"crime_count": 5' in output


def test_resolve_metrics_dir_defaults_to_none():
    args = make_args()

    assert resolve_metrics_dir(args) is None


def test_resolve_metrics_dir_prefers_explicit_flag():
    args = make_args(
        metrics_dir="/tmp/explicit/metrics",
        run_id="run-1",
    )

    from pathlib import Path

    assert resolve_metrics_dir(args) == Path(
        "/tmp/explicit/metrics"
    )


def test_resolve_metrics_dir_from_run_id(monkeypatch):
    from pathlib import Path

    monkeypatch.setenv(
        "CIVICMESH_RUNS", "/civicmesh-runs"
    )

    args = make_args(run_id="run-42")

    assert resolve_metrics_dir(args) == Path(
        "/civicmesh-runs"
    ) / "run-42" / "metrics"


def test_build_peer_uses_analytics_delivery_function_when_metrics_dir_set(
    tmp_path,
):
    args = make_args(
        metrics_dir=str(tmp_path / "metrics")
    )

    peer = build_peer(args)

    assert (
        peer.pubsub._delivery_function.__module__
        == "civicmesh.analytics.delivery"
    )