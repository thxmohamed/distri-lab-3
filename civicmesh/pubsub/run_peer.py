from __future__ import annotations

import argparse
import asyncio
import logging

from civicmesh.network.peer_info import PeerInfo
from civicmesh.pubsub.network_adapter import PubSubPeer

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Lee los parámetros entregados por consola.

    A diferencia de civicmesh.network.run_peer (que solo entiende
    JOIN/GOSSIP), este script levanta un PubSubPeer: un peer "puro"
    -- sin publicar nada propio -- capaz de suscribirse a tópicos y
    reenviar mensajes de pub/sub de otros peers/publicadores según
    should_forward (TTL, prioridad, interés). Es el proceso pensado
    para ocupar los hosts CPU del Slurm (Sección 5.1 del enunciado) y
    los servicios "peer" del docker-compose.
    """

    parser = argparse.ArgumentParser(
        description="Ejecuta un peer de CivicMesh con pub/sub (sin publicar datos propios)."
    )

    parser.add_argument("--id", dest="peer_id", required=True, help="Identificador único del peer. Ej: peer-A")
    parser.add_argument("--host", default="127.0.0.1", help="Host donde escuchará el peer.")
    parser.add_argument("--port", type=int, required=True, help="Puerto TCP donde escuchará el peer.")

    parser.add_argument(
        "--subscribe",
        default="",
        help="Comunas a las que suscribirse, separadas por coma. Ej: santiago,maipu",
    )
    parser.add_argument(
        "--include-neighbors",
        action="store_true",
        help="Además de las comunas indicadas, suscribirse a sus vecinas geográficas.",
    )

    parser.add_argument("--max-view-size", type=int, default=10, help="Tamaño máximo de la vista parcial de membresía.")
    parser.add_argument("--fanout", type=int, default=2, help="Cantidad de peers seleccionados por ronda Gossip.")
    parser.add_argument("--gossip-interval", type=float, default=3.0, help="Intervalo entre rondas Gossip en segundos.")
    parser.add_argument("--random-seed", type=int, default=None, help="Seed para selección reproducible de peers.")
    parser.add_argument("--failure-timeout", type=float, default=10.0, help="Segundos sin contacto antes de marcar un peer como dead.")
    parser.add_argument("--failure-check-interval", type=float, default=2.0, help="Cada cuántos segundos se revisan los timeouts.")
    parser.add_argument("--connection-timeout", type=float, default=5.0, help="Timeout de conexiones TCP.")

    parser.add_argument("--seed-id", default=None, help="ID del peer seed.")
    parser.add_argument("--seed-host", default=None, help="Host del peer seed.")
    parser.add_argument("--seed-port", type=int, default=None, help="Puerto del peer seed.")

    return parser.parse_args()


def validate_seed_args(args: argparse.Namespace) -> None:
    seed_values = [args.seed_id, args.seed_host, args.seed_port]
    supplied = [value is not None for value in seed_values]

    if any(supplied) and not all(supplied):
        raise ValueError("Para utilizar un seed debes indicar --seed-id, --seed-host y --seed-port.")


def on_message(message) -> None:
    """
    Estado agregado local minimo: por ahora solo deja constancia en el
    log de cada mensaje entregado (topic/canal/origen/hop_count). El
    Rol 4 (Analitica) puede reemplazar esto por la agregacion real que
    alimenta metrics/ (Seccion 3.4/5.4 del enunciado).
    """

    logger.info(
        "PUBSUB entregado: topic=%s canal=%s origen=%s hop_count=%s payload=%s",
        message.topic,
        message.channel,
        message.origin,
        message.hop_count,
        message.payload,
    )


async def run_peer(args: argparse.Namespace) -> None:
    validate_seed_args(args)

    peer = PubSubPeer(
        peer_id=args.peer_id,
        host=args.host,
        port=args.port,
        delivery_function=on_message,
        max_view_size=args.max_view_size,
        fanout=args.fanout,
        gossip_interval=args.gossip_interval,
        random_seed=args.random_seed,
        connection_timeout=args.connection_timeout,
        failure_timeout=args.failure_timeout,
        failure_check_interval=args.failure_check_interval,
    )

    try:
        await peer.start()

        if args.seed_id is not None:
            seed = PeerInfo(peer_id=args.seed_id, host=args.seed_host, port=args.seed_port)
            await peer.join(seed)

        topics = [topic.strip() for topic in args.subscribe.split(",") if topic.strip()]
        for topic in topics:
            peer.pubsub.subscribe(topic, include_neighbors=args.include_neighbors)

        print(
            f"[{args.peer_id}] fanout={args.fanout}, gossip_interval={args.gossip_interval}s, "
            f"failure_timeout={args.failure_timeout}s, suscrito_a={topics or '(nada)'}"
        )
        print(f"[{args.peer_id}] Presiona Ctrl+C para detener.")

        await asyncio.Event().wait()

    finally:
        await peer.stop()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    args = parse_args()

    try:
        asyncio.run(run_peer(args))
    except KeyboardInterrupt:
        print("\nPeer detenido por el usuario.")
    except ValueError as error:
        print(f"Error de configuración: {error}")
    except ConnectionError as error:
        print(f"Error de conexión: {error}")


if __name__ == "__main__":
    main()
