import asyncio
import socket

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


def test_pubsub_reaches_subscriber_through_three_real_peers():
    async def scenario():
        ports = set()

        while len(ports) < 3:
            ports.add(get_free_port())

        port_a, port_b, port_c = list(ports)

        delivered_a = []
        delivered_b = []
        delivered_c = []

        peer_a = PubSubPeer(
            peer_id="peer-A",
            host="127.0.0.1",
            port=port_a,
            delivery_function=delivered_a.append,
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
            delivery_function=delivered_b.append,
            fanout=1,
            gossip_interval=60.0,
            failure_timeout=5.0,
            failure_check_interval=0.1,
            connection_timeout=0.3,
            random_seed=200,
        )

        peer_c = PubSubPeer(
            peer_id="peer-C",
            host="127.0.0.1",
            port=port_c,
            delivery_function=delivered_c.append,
            fanout=1,
            gossip_interval=60.0,
            failure_timeout=5.0,
            failure_check_interval=0.1,
            connection_timeout=0.3,
            random_seed=300,
        )

        try:
            await peer_a.start()
            await peer_b.start()
            await peer_c.start()

            seed_a = PeerInfo(
                peer_id="peer-A",
                host="127.0.0.1",
                port=port_a,
            )

            seed_b = PeerInfo(
                peer_id="peer-B",
                host="127.0.0.1",
                port=port_b,
            )

            # Topología controlada:
            #
            # peer-A <-> peer-B <-> peer-C
            #
            # A no conoce directamente a C.

            await peer_b.join(seed_a)
            await peer_c.join(seed_b)

            await wait_until(
                lambda: (
                    peer_a.membership.get_peer("peer-B")
                    is not None
                    and
                    peer_b.membership.get_peer("peer-C")
                    is not None
                )
            )

            peer_c.pubsub.subscribe(
                "estacion-central"
            )

            original = peer_a.pubsub.publish(
                topic="estacion-central",
                channel="objective",
                payload={
                    "crime_count": 5,
                },
            )

            await wait_until(
                lambda: len(delivered_c) == 1
            )

            assert delivered_a == []
            assert delivered_b == []

            assert len(delivered_c) == 1

            received = delivered_c[0]

            assert (
                received.message_id
                == original.message_id
            )

            assert (
                received.topic
                == "estacion-central"
            )

            assert (
                received.channel
                == "objective"
            )

            assert received.payload == {
                "crime_count": 5,
            }

            # objective comienza con TTL 4:
            #
            # A -> B : TTL 3 / hop 1
            # B -> C : TTL 2 / hop 2

            assert received.ttl == 2
            assert received.hop_count == 2

            # También comprobamos que realmente
            # pasó por el peer intermediario.

            assert (
                peer_a.pubsub.metrics.published
                == 1
            )

            assert (
                peer_b.pubsub.metrics.received
                == 1
            )

            assert (
                peer_b.pubsub.metrics.forwarded
                == 1
            )

            assert (
                peer_c.pubsub.metrics.received
                == 1
            )

            assert (
                peer_c.pubsub.metrics.delivered
                == 1
            )

        finally:
            await peer_c.stop()
            await peer_b.stop()
            await peer_a.stop()

    asyncio.run(scenario())