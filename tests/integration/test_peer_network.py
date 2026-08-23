import asyncio
import socket

from civicmesh.network.peer import Peer
from civicmesh.network.peer_info import PeerInfo


def get_free_port() -> int:
    """
    Busca un puerto TCP disponible en localhost.

    Esto evita usar puertos fijos como 5000/5001,
    que podrían estar ocupados durante los tests.
    """

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    ) as sock:

        sock.bind(
            ("127.0.0.1", 0)
        )

        return sock.getsockname()[1]


async def wait_until(
    condition,
    timeout: float = 2.0,
    interval: float = 0.05,
) -> None:
    """
    Espera hasta que una condición sea verdadera.

    Es mejor que usar un sleep fijo porque una operación
    de red puede tardar tiempos ligeramente diferentes
    según el computador.
    """

    loop = asyncio.get_running_loop()

    deadline = (
        loop.time() + timeout
    )

    while loop.time() < deadline:

        if condition():
            return

        await asyncio.sleep(
            interval
        )

    raise AssertionError(
        "La condición no se cumplió "
        f"antes de {timeout} segundos"
    )


def test_peer_join_over_tcp():
    """
    Comprueba integración entre:

    - Peer
    - TCP/asyncio
    - JOIN
    - Membership

    Flujo:

        Peer B
            |
            | JOIN
            v
        Peer A

    Al finalizar:

        A conoce a B como alive
        B conoce a A como alive
    """

    async def scenario():

        # -----------------------------------------------------
        # 1. Obtener dos puertos disponibles
        # -----------------------------------------------------

        port_a = get_free_port()
        port_b = get_free_port()

        # Evitar, por seguridad, que coincidan.
        while port_b == port_a:
            port_b = get_free_port()

        # -----------------------------------------------------
        # 2. Crear Peer A
        # -----------------------------------------------------

        peer_a = Peer(
            peer_id="peer-A",
            host="127.0.0.1",
            port=port_a,

            # Intervalo alto para que Gossip no interfiera
            # con este test específico de JOIN.
            gossip_interval=60,

            fanout=2,

            random_seed=123,
        )

        # -----------------------------------------------------
        # 3. Crear Peer B
        # -----------------------------------------------------

        peer_b = Peer(
            peer_id="peer-B",
            host="127.0.0.1",
            port=port_b,

            gossip_interval=60,

            fanout=2,

            random_seed=456,
        )

        try:

            # -------------------------------------------------
            # 4. Levantar ambos servidores TCP
            # -------------------------------------------------

            await peer_a.start()
            await peer_b.start()

            # -------------------------------------------------
            # 5. Representar a A como seed conocido por B
            # -------------------------------------------------

            seed_a = PeerInfo(
                peer_id="peer-A",
                host="127.0.0.1",
                port=port_a,
            )

            # -------------------------------------------------
            # 6. Peer B realiza JOIN hacia Peer A
            # -------------------------------------------------

            await peer_b.join(
                seed_a
            )

            # -------------------------------------------------
            # 7. Esperar a que A procese el JOIN
            # -------------------------------------------------

            await wait_until(
                lambda: (
                    peer_a.membership
                    .get_peer("peer-B")
                    is not None
                )
            )

            # -------------------------------------------------
            # 8. Obtener información de membresía
            # -------------------------------------------------

            peer_b_seen_by_a = (
                peer_a.membership
                .get_peer("peer-B")
            )

            peer_a_seen_by_b = (
                peer_b.membership
                .get_peer("peer-A")
            )

            # -------------------------------------------------
            # 9. Comprobar que A conoce a B
            # -------------------------------------------------

            assert peer_b_seen_by_a is not None

            assert (
                peer_b_seen_by_a.peer_id
                == "peer-B"
            )

            assert (
                peer_b_seen_by_a.host
                == "127.0.0.1"
            )

            assert (
                peer_b_seen_by_a.port
                == port_b
            )

            assert (
                peer_b_seen_by_a.status
                == "alive"
            )

            assert (
                peer_b_seen_by_a.last_seen
                is not None
            )

            # -------------------------------------------------
            # 10. Comprobar que B conoce a A
            # -------------------------------------------------

            assert peer_a_seen_by_b is not None

            assert (
                peer_a_seen_by_b.peer_id
                == "peer-A"
            )

            assert (
                peer_a_seen_by_b.host
                == "127.0.0.1"
            )

            assert (
                peer_a_seen_by_b.port
                == port_a
            )

            assert (
                peer_a_seen_by_b.status
                == "alive"
            )

            assert (
                peer_a_seen_by_b.last_seen
                is not None
            )

        finally:

            # -------------------------------------------------
            # 11. Detener los peers aunque falle un assert
            # -------------------------------------------------

            await peer_b.stop()
            await peer_a.stop()

    asyncio.run(
        scenario()
    )