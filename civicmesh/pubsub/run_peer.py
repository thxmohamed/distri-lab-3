from __future__ import annotations

import argparse
import asyncio
import json
import logging

from civicmesh.network.peer_info import PeerInfo
from civicmesh.pubsub.message import PubSubMessage
from civicmesh.pubsub.network_adapter import PubSubPeer


logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta un peer CivicMesh con soporte "
            "de Gossip y Publish/Subscribe."
        )
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
    # Suscripciones Pub/Sub
    # ---------------------------------------------------------

    parser.add_argument(
        "--subscribe",
        action="append",
        default=[],
        metavar="TOPIC",
        help=(
            "Tópico geográfico al que se suscribe el peer. "
            "Puede indicarse varias veces."
        ),
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

    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def validate_seed_args(
    args: argparse.Namespace,
) -> None:
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


def build_delivery_function(
    peer_id: str,
):
    """
    Entrega local por defecto.

    Por ahora registra el mensaje recibido.
    Los dominios y la capa analítica pueden utilizar
    posteriormente su propio callback.
    """

    def deliver(message: PubSubMessage) -> None:
        event = {
            "peer_id": peer_id,
            "message_id": message.message_id,
            "topic": message.topic,
            "channel": message.channel,
            "payload": message.payload,
            "origin": message.origin,
            "ttl": message.ttl,
            "hop_count": message.hop_count,
        }

        print(
            json.dumps(
                event,
                ensure_ascii=False,
            ),
            flush=True,
        )

    return deliver


def build_peer(
    args: argparse.Namespace,
) -> PubSubPeer:
    return PubSubPeer(
        peer_id=args.peer_id,
        host=args.host,
        port=args.port,
        delivery_function=build_delivery_function(
            args.peer_id
        ),

        # Vista parcial
        max_view_size=args.max_view_size,

        # Gossip
        fanout=args.fanout,
        gossip_interval=args.gossip_interval,
        random_seed=args.random_seed,

        # Red
        connection_timeout=args.connection_timeout,

        # Failure detector
        failure_timeout=args.failure_timeout,
        failure_check_interval=(
            args.failure_check_interval
        ),
    )


async def run_peer(
    args: argparse.Namespace,
) -> None:
    validate_seed_args(args)

    peer = build_peer(args)

    try:
        # -----------------------------------------------------
        # 1. Levantar TCP + Gossip + Failure Detector
        # -----------------------------------------------------

        await peer.start()

        # -----------------------------------------------------
        # 2. Registrar suscripciones Pub/Sub
        # -----------------------------------------------------

        for topic in args.subscribe:
            peer.pubsub.subscribe(topic)

        # -----------------------------------------------------
        # 3. Bootstrap contra seed, si corresponde
        # -----------------------------------------------------

        if args.seed_id is not None:
            seed = PeerInfo(
                peer_id=args.seed_id,
                host=args.seed_host,
                port=args.seed_port,
            )

            await peer.join(seed)

        # -----------------------------------------------------
        # 4. Mostrar configuración
        # -----------------------------------------------------

        subscriptions = (
            peer.pubsub.subscriptions.get_subscriptions()
        )

        print(
            f"[{args.peer_id}] "
            f"PubSubPeer iniciado en "
            f"{args.host}:{args.port}"
        )

        print(
            f"[{args.peer_id}] "
            f"suscripciones="
            f"{sorted(subscriptions)}"
        )

        print(
            f"[{args.peer_id}] "
            f"max_view_size={args.max_view_size}, "
            f"gossip_fanout={args.fanout}, "
            f"gossip_interval="
            f"{args.gossip_interval}s"
        )

        print(
            f"[{args.peer_id}] "
            "Presiona Ctrl+C para detener."
        )

        # -----------------------------------------------------
        # 5. Mantener el peer vivo
        # -----------------------------------------------------

        await asyncio.Event().wait()

    finally:
        await peer.stop()


def main() -> None:
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
            "\nPubSubPeer detenido por el usuario."
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