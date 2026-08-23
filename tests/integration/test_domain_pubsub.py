import asyncio
import socket

from civicmesh.domains import (
    CrimeGenerator,
    CrimePerceptionModel,
    CrimePublisher,
    RumorBuffer,
    load_domain_config,
)

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
        f"La condición no se cumplió "
        f"antes de {timeout} segundos"
    )


def test_crime_publisher_uses_real_pubsub_network():

    async def scenario():

        ports = set()

        while len(ports) < 3:
            ports.add(get_free_port())

        port_a, port_b, port_c = list(ports)

        delivered_c = []

        rumors_a = RumorBuffer()

        def deliver_a(message):
            rumors_a.record_message(
                message,
                own_peer_id="publisher-A",
            )

        peer_a = PubSubPeer(
            peer_id="publisher-A",
            host="127.0.0.1",
            port=port_a,
            delivery_function=deliver_a,
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
            delivery_function=lambda message: None,
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

            # Levantar los 3 peers
            await peer_a.start()
            await peer_b.start()
            await peer_c.start()

            # Crear topología:
            #
            # publisher-A <-> peer-B <-> peer-C

            await peer_b.join(
                PeerInfo(
                    peer_id="publisher-A",
                    host="127.0.0.1",
                    port=port_a,
                )
            )

            await peer_c.join(
                PeerInfo(
                    peer_id="peer-B",
                    host="127.0.0.1",
                    port=port_b,
                )
            )

            await wait_until(
                lambda: (
                    peer_a.membership.get_peer(
                        "peer-B"
                    )
                    is not None
                    and
                    peer_b.membership.get_peer(
                        "peer-C"
                    )
                    is not None
                )
            )

            # El publisher escucha rumores
            peer_a.pubsub.subscribe(
                "estacion-central"
            )

            # C será el receptor final
            peer_c.pubsub.subscribe(
                "estacion-central"
            )

            config = load_domain_config()

            generator = CrimeGenerator(
                config.crime_rates,
                config.seed,
                config.delta_t,
            )

            perception = CrimePerceptionModel(
                commune="estacion-central",
                config=config.crime_perception,
                seed=config.seed,
            )

            publisher = CrimePublisher(
                commune="estacion-central",
                generator=generator,
                perception=perception,

                # Pub/Sub REAL del Rol 2
                publish=peer_a.pubsub.publish,

                rumor_provider=rumors_a.consume,
            )

            # Ejecutar un paso real
            publisher.tick("t1")

            # Esperar 2 objetivos + 1 subjetivo
            await wait_until(
                lambda: len(delivered_c) == 3
            )

            channels = [
                message.channel
                for message in delivered_c
            ]

            assert channels == [
                "objective",
                "objective",
                "subjective",
            ]

            assert all(
                message.topic
                == "estacion-central"
                for message in delivered_c
            )

            subjective = delivered_c[-1]

            assert (
                subjective.payload["domain"]
                == "crime"
            )

            assert (
                "perception"
                in subjective.payload
            )

        finally:

            await peer_c.stop()
            await peer_b.stop()
            await peer_a.stop()

    asyncio.run(scenario())

import asyncio
import socket

from civicmesh.domains import (
    CrimeGenerator,
    CrimePerceptionModel,
    CrimePublisher,
    RumorBuffer,
    load_domain_config,
)

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
        f"La condición no se cumplió "
        f"antes de {timeout} segundos"
    )


def test_crime_publisher_uses_real_pubsub_network():

    async def scenario():

        ports = set()

        while len(ports) < 3:
            ports.add(get_free_port())

        port_a, port_b, port_c = list(ports)

        delivered_c = []

        rumors_a = RumorBuffer()

        def deliver_a(message):
            rumors_a.record_message(
                message,
                own_peer_id="publisher-A",
            )

        peer_a = PubSubPeer(
            peer_id="publisher-A",
            host="127.0.0.1",
            port=port_a,
            delivery_function=deliver_a,
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
            delivery_function=lambda message: None,
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

            # Levantar los 3 peers
            await peer_a.start()
            await peer_b.start()
            await peer_c.start()

            # Crear topología:
            #
            # publisher-A <-> peer-B <-> peer-C

            await peer_b.join(
                PeerInfo(
                    peer_id="publisher-A",
                    host="127.0.0.1",
                    port=port_a,
                )
            )

            await peer_c.join(
                PeerInfo(
                    peer_id="peer-B",
                    host="127.0.0.1",
                    port=port_b,
                )
            )

            await wait_until(
                lambda: (
                    peer_a.membership.get_peer(
                        "peer-B"
                    )
                    is not None
                    and
                    peer_b.membership.get_peer(
                        "peer-C"
                    )
                    is not None
                )
            )

            # El publisher escucha rumores
            peer_a.pubsub.subscribe(
                "estacion-central"
            )

            # C será el receptor final
            peer_c.pubsub.subscribe(
                "estacion-central"
            )

            config = load_domain_config()

            generator = CrimeGenerator(
                config.crime_rates,
                config.seed,
                config.delta_t,
            )

            perception = CrimePerceptionModel(
                commune="estacion-central",
                config=config.crime_perception,
                seed=config.seed,
            )

            publisher = CrimePublisher(
                commune="estacion-central",
                generator=generator,
                perception=perception,

                # Pub/Sub REAL del Rol 2
                publish=peer_a.pubsub.publish,

                rumor_provider=rumors_a.consume,
            )

            # Ejecutar un paso real
            publisher.tick("t1")

            # Esperar 2 objetivos + 1 subjetivo
            await wait_until(
                lambda: len(delivered_c) == 3
            )

            channels = [
                message.channel
                for message in delivered_c
            ]

            assert channels == [
                "objective",
                "objective",
                "subjective",
            ]

            assert all(
                message.topic
                == "estacion-central"
                for message in delivered_c
            )

            subjective = delivered_c[-1]

            assert (
                subjective.payload["domain"]
                == "crime"
            )

            assert (
                "perception"
                in subjective.payload
            )

        finally:

            await peer_c.stop()
            await peer_b.stop()
            await peer_a.stop()

    asyncio.run(scenario())
