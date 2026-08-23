import asyncio
import socket

from civicmesh.network.peer import Peer
from civicmesh.network.peer_info import PeerInfo


def get_free_port() -> int:
    """Obtiene un puerto TCP libre en localhost."""

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
    """
    Espera hasta que condition() sea True.
    """

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


def test_three_peers_discover_each_other_via_gossip():
    """
    Comprueba descubrimiento distribuido mediante Gossip.

    Estado inicial:

        B ---> A <--- C

    B y C solamente conocen inicialmente a A.

    Después del Gossip:

        A conoce B y C
        B descubre C
        C descubre B
    """

    async def scenario():

        # -----------------------------------------------------
        # 1. Obtener puertos libres
        # -----------------------------------------------------

        ports = set()

        while len(ports) < 3:
            ports.add(get_free_port())

        port_a, port_b, port_c = list(ports)

        # -----------------------------------------------------
        # 2. Crear los tres peers
        # -----------------------------------------------------

        peer_a = Peer(
            peer_id="peer-A",
            host="127.0.0.1",
            port=port_a,
            fanout=2,
            gossip_interval=0.05,
            failure_timeout=5.0,
            failure_check_interval=0.1,
            connection_timeout=0.3,
            random_seed=100,
        )

        peer_b = Peer(
            peer_id="peer-B",
            host="127.0.0.1",
            port=port_b,
            fanout=2,
            gossip_interval=0.05,
            failure_timeout=5.0,
            failure_check_interval=0.1,
            connection_timeout=0.3,
            random_seed=200,
        )

        peer_c = Peer(
            peer_id="peer-C",
            host="127.0.0.1",
            port=port_c,
            fanout=2,
            gossip_interval=0.05,
            failure_timeout=5.0,
            failure_check_interval=0.1,
            connection_timeout=0.3,
            random_seed=300,
        )

        try:

            # -------------------------------------------------
            # 3. Iniciar los servidores
            # -------------------------------------------------

            await peer_a.start()
            await peer_b.start()
            await peer_c.start()

            # -------------------------------------------------
            # 4. A será el seed
            # -------------------------------------------------

            seed_a = PeerInfo(
                peer_id="peer-A",
                host="127.0.0.1",
                port=port_a,
            )

            # -------------------------------------------------
            # 5. B y C entran mediante A
            # -------------------------------------------------

            await peer_b.join(seed_a)
            await peer_c.join(seed_a)

            # -------------------------------------------------
            # 6. Esperar hasta que A conozca B y C
            # -------------------------------------------------

            await wait_until(
                lambda: (
                    peer_a.membership.get_peer("peer-B")
                    is not None
                    and
                    peer_a.membership.get_peer("peer-C")
                    is not None
                )
            )

            # A debería conocer directamente a ambos.
            assert (
                peer_a.membership
                .get_peer("peer-B")
                .status
                == "alive"
            )

            assert (
                peer_a.membership
                .get_peer("peer-C")
                .status
                == "alive"
            )

            # -------------------------------------------------
            # 7. Esperar descubrimiento mediante Gossip
            # -------------------------------------------------

            await wait_until(
                lambda: (
                    peer_b.membership.get_peer("peer-C")
                    is not None
                    and
                    peer_c.membership.get_peer("peer-B")
                    is not None
                ),
                timeout=3.0,
            )

            # -------------------------------------------------
            # 8. Verificar descubrimiento
            # -------------------------------------------------

            peer_c_seen_by_b = (
                peer_b.membership
                .get_peer("peer-C")
            )

            peer_b_seen_by_c = (
                peer_c.membership
                .get_peer("peer-B")
            )

            assert peer_c_seen_by_b is not None
            assert peer_b_seen_by_c is not None

            # -------------------------------------------------
            # 9. Esperar contacto directo entre B y C
            # -------------------------------------------------

            await wait_until(
                lambda: (
                    peer_b.membership
                    .get_peer("peer-C")
                    .status
                    == "alive"
                    and
                    peer_c.membership
                    .get_peer("peer-B")
                    .status
                    == "alive"
                ),
                timeout=3.0,
            )

            # -------------------------------------------------
            # 10. Verificación final
            # -------------------------------------------------

            assert (
                peer_b.membership
                .get_peer("peer-C")
                .status
                == "alive"
            )

            assert (
                peer_c.membership
                .get_peer("peer-B")
                .status
                == "alive"
            )

        finally:

            # Siempre detener los peers.
            await peer_c.stop()
            await peer_b.stop()
            await peer_a.stop()

    asyncio.run(scenario())