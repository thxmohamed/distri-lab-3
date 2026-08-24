import asyncio
import json
import socket

from civicmesh.analytics import build_analytics_delivery_function
from civicmesh.network.peer_info import PeerInfo
from civicmesh.pubsub.network_adapter import PubSubPeer


def get_free_port() -> int:
    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def wait_until(
    condition,
    timeout: float = 3.0,
    interval: float = 0.05,
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    while loop.time() < deadline:
        if condition():
            return

        await asyncio.sleep(interval)

    raise AssertionError(
        f"La condición no se cumplió antes de {timeout} segundos"
    )


def test_delivered_message_is_written_to_metrics_dir(tmp_path):
    async def scenario():
        ports = set()

        while len(ports) < 2:
            ports.add(get_free_port())

        port_a, port_b = list(ports)

        metrics_dir = tmp_path / "metrics"

        peer_a = PubSubPeer(
            peer_id="peer-A",
            host="127.0.0.1",
            port=port_a,
            delivery_function=lambda message: None,
            fanout=1,
            gossip_interval=60.0,
            failure_timeout=5.0,
            failure_check_interval=0.1,
            connection_timeout=0.3,
            random_seed=100,
        )

        peer_b = PubSubPeer(
            peer_id="peer-B",
            host="127.0.0.1",
            port=port_b,
            delivery_function=(
                build_analytics_delivery_function(
                    "peer-B",
                    metrics_dir,
                )
            ),
            fanout=1,
            gossip_interval=60.0,
            failure_timeout=5.0,
            failure_check_interval=0.1,
            connection_timeout=0.3,
            random_seed=200,
        )

        try:
            await peer_a.start()
            await peer_b.start()

            seed_a = PeerInfo(
                peer_id="peer-A",
                host="127.0.0.1",
                port=port_a,
            )

            await peer_b.join(seed_a)

            await wait_until(
                lambda: (
                    peer_a.membership.get_peer("peer-B")
                    is not None
                )
            )

            peer_b.pubsub.subscribe(
                "estacion-central"
            )

            peer_a.pubsub.publish(
                topic="estacion-central",
                channel="objective",
                payload={
                    "domain": "crime",
                    "commune": "estacion-central",
                    "crime_type": "robo",
                    "count": 5,
                    "timestamp": "t1",
                },
            )

            snapshot_path = (
                metrics_dir / "peer-B.jsonl"
            )

            await wait_until(
                lambda: snapshot_path.exists()
            )

            snapshot = json.loads(
                snapshot_path.read_text(
                    encoding="utf-8"
                ).splitlines()[0]
            )

            assert snapshot["peer_id"] == "peer-B"
            assert snapshot["topic"] == "estacion-central"
            assert snapshot["channel"] == "objective"
            assert snapshot["value"] == 5
            assert snapshot["divergence"] is None

        finally:
            await peer_b.stop()
            await peer_a.stop()

    asyncio.run(scenario())
