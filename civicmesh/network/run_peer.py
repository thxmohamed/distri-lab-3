from __future__ import annotations

import argparse
import asyncio
import logging

from .peer import Peer
from .peer_info import PeerInfo


def parse_args() -> argparse.Namespace:
    """
    Lee los parámetros entregados por consola.
    """

    parser = argparse.ArgumentParser(
        description="Ejecuta un Peer de CivicMesh."
    )

    # ---------------------------------------------------------
    # Identidad del peer
    # ---------------------------------------------------------

    parser.add_argument(
        "--id",
        dest="peer_id",
        required=True,
        help="Identificador único del peer. Ej: peer-A",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host donde escuchará el peer.",
    )

    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Puerto TCP donde escuchará el peer.",
    )

    # ---------------------------------------------------------
    # Membresía
    # ---------------------------------------------------------

    parser.add_argument(
        "--max-view-size",
        type=int,
        default=10,
        help=(
            "Cantidad máxima de peers almacenados "
            "en la vista parcial de membresía."
        ),
    )

    # ---------------------------------------------------------
    # Gossip
    # ---------------------------------------------------------

    parser.add_argument(
        "--fanout",
        type=int,
        default=2,
        help="Cantidad de peers seleccionados por ronda Gossip.",
    )

    parser.add_argument(
        "--gossip-interval",
        type=float,
        default=3.0,
        help="Intervalo entre rondas Gossip en segundos.",
    )

    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Seed para selección reproducible de peers.",
    )

    # ---------------------------------------------------------
    # Failure detector
    # ---------------------------------------------------------

    parser.add_argument(
        "--failure-timeout",
        type=float,
        default=10.0,
        help=(
            "Segundos sin contacto antes de marcar "
            "un peer como dead."
        ),
    )

    parser.add_argument(
        "--failure-check-interval",
        type=float,
        default=2.0,
        help=(
            "Cada cuántos segundos se revisan "
            "los timeouts."
        ),
    )

    # ---------------------------------------------------------
    # Red
    # ---------------------------------------------------------

    parser.add_argument(
        "--connection-timeout",
        type=float,
        default=5.0,
        help="Timeout de conexiones TCP.",
    )

    # ---------------------------------------------------------
    # Seed / Bootstrap
    # ---------------------------------------------------------

    parser.add_argument(
        "--seed-id",
        default=None,
        help="ID del peer seed.",
    )

    parser.add_argument(
        "--seed-host",
        default=None,
        help="Host del peer seed.",
    )

    parser.add_argument(
        "--seed-port",
        type=int,
        default=None,
        help="Puerto del peer seed.",
    )

    return parser.parse_args()


def validate_seed_args(
    args: argparse.Namespace,
) -> None:
    """
    Comprueba que los parámetros del seed estén todos
    presentes o todos ausentes.
    """

    seed_values = [
        args.seed_id,
        args.seed_host,
        args.seed_port,
    ]

    supplied = [
        value is not None
        for value in seed_values
    ]

    if any(supplied) and not all(supplied):
        raise ValueError(
            "Para utilizar un seed debes indicar "
            "--seed-id, --seed-host y --seed-port."
        )


async def run_peer(
    args: argparse.Namespace,
) -> None:
    """
    Crea y mantiene ejecutándose un Peer.
    """

    validate_seed_args(args)

    peer = Peer(
        peer_id=args.peer_id,
        host=args.host,
        port=args.port,

        # Vista parcial
        max_view_size=args.max_view_size,

        # Gossip
        fanout=args.fanout,
        gossip_interval=args.gossip_interval,
        random_seed=args.random_seed,

        # Red
        connection_timeout=args.connection_timeout,

        # Detección de fallos
        failure_timeout=args.failure_timeout,
        failure_check_interval=args.failure_check_interval,
    )

    try:

        # -----------------------------------------------------
        # 1. Levantar servidor + tareas internas
        # -----------------------------------------------------

        await peer.start()

        # -----------------------------------------------------
        # 2. Hacer JOIN si se indicó un seed
        # -----------------------------------------------------

        if args.seed_id is not None:

            seed = PeerInfo(
                peer_id=args.seed_id,
                host=args.seed_host,
                port=args.seed_port,
            )

            await peer.join(seed)

        # -----------------------------------------------------
        # 3. Mostrar configuración básica
        # -----------------------------------------------------

        print(
            f"[{args.peer_id}] "
            f"max_view_size={args.max_view_size}, "
            f"fanout={args.fanout}, "
            f"gossip_interval={args.gossip_interval}s, "
            f"failure_timeout={args.failure_timeout}s"
        )

        print(
            f"[{args.peer_id}] "
            "Presiona Ctrl+C para detener."
        )

        # -----------------------------------------------------
        # 4. Mantener el proceso vivo
        # -----------------------------------------------------

        await asyncio.Event().wait()

    finally:

        await peer.stop()


def main() -> None:
    """
    Punto de entrada desde consola.
    """

    # Permite visualizar los logger.info/logger.warning
    # utilizados por Peer, Membership y FailureDetector.
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        ),
    )

    args = parse_args()

    try:

        asyncio.run(
            run_peer(args)
        )

    except KeyboardInterrupt:

        print(
            "\nPeer detenido por el usuario."
        )

    except ValueError as error:

        print(
            f"Error de configuración: {error}"
        )

    except ConnectionError as error:

        print(
            f"Error de conexión: {error}"
        )


if __name__ == "__main__":
    main()