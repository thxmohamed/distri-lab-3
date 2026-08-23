import asyncio
import socket

from civicmesh.network.peer import Peer
from civicmesh.network.peer_info import PeerInfo


def get_free_port() -> int:
    """Obtiene un puerto TCP disponible."""

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
    timeout: float = 3.0,
    interval: float = 0.05,
) -> None:
    """
    Espera hasta que una condición se cumpla.
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


def test_peer_detects_failure_after_timeout():
    """
    Comprueba el flujo real:

        A <---- B

        B realiza JOIN.

        A conoce a B como alive.

        B se detiene.

        A deja de recibir mensajes.

        FailureDetector alcanza el timeout.

        A marca B como dead.
    """

    async def scenario():

        port_a = get_free_port()
        port_b = get_free_port()

        while port_b == port_a:
            port_b = get_free_port()

        # ---------------------------------------------
        # Peer A
        # ---------------------------------------------

        peer_a = Peer(
            peer_id="peer-A",
            host="127.0.0.1",
            port=port_a,

            fanout=2,

            # Gossip frecuente durante el test.
            gossip_interval=0.1,

            # Timeout pequeño para no esperar 10 s.
            failure_timeout=0.5,

            # Revisar frecuentemente.
            failure_check_interval=0.05,

            connection_timeout=0.2,

            random_seed=123,
        )

        # ---------------------------------------------
        # Peer B
        # ---------------------------------------------

        peer_b = Peer(
            peer_id="peer-B",
            host="127.0.0.1",
            port=port_b,

            fanout=2,
            gossip_interval=0.1,
            failure_timeout=0.5,
            failure_check_interval=0.05,
            connection_timeout=0.2,

            random_seed=456,
        )

        try:

            # -----------------------------------------
            # 1. Iniciar ambos peers
            # -----------------------------------------

            await peer_a.start()
            await peer_b.start()

            # -----------------------------------------
            # 2. A será seed para B
            # -----------------------------------------

            seed_a = PeerInfo(
                peer_id="peer-A",
                host="127.0.0.1",
                port=port_a,
            )

            # -----------------------------------------
            # 3. B entra a la malla
            # -----------------------------------------

            await peer_b.join(seed_a)

            # -----------------------------------------
            # 4. Esperar hasta que A conozca a B
            # -----------------------------------------

            await wait_until(
                lambda: (
                    peer_a.membership
                    .get_peer("peer-B")
                    is not None
                )
            )

            peer_b_seen_by_a = (
                peer_a.membership
                .get_peer("peer-B")
            )

            assert peer_b_seen_by_a is not None

            # -----------------------------------------
            # 5. B debe estar vivo inicialmente
            # -----------------------------------------

            assert (
                peer_b_seen_by_a.status
                == "alive"
            )

            # Dejamos que ocurra al menos alguna ronda
            # de Gossip.
            await asyncio.sleep(0.2)

            assert (
                peer_a.membership
                .get_peer("peer-B")
                .status
                == "alive"
            )

            # -----------------------------------------
            # 6. Simular caída de B
            # -----------------------------------------

            await peer_b.stop()

            # -----------------------------------------
            # 7. Esperar detección del timeout
            # -----------------------------------------

            await wait_until(
                lambda: (
                    peer_a.membership
                    .get_peer("peer-B")
                    .status
                    == "dead"
                ),
                timeout=2.0,
            )

            # -----------------------------------------
            # 8. Verificación final
            # -----------------------------------------

            peer_b_after_failure = (
                peer_a.membership
                .get_peer("peer-B")
            )

            assert peer_b_after_failure is not None

            assert (
                peer_b_after_failure.status
                == "dead"
            )

        finally:

            # B puede haberse detenido anteriormente.
            await peer_b.stop()

            await peer_a.stop()

    asyncio.run(
        scenario()
    )