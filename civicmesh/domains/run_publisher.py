from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from civicmesh.domains import (
    AirPerceptionModel,
    AirQualityPublisher,
    AirQualityReplay,
    CrimeGenerator,
    CrimePerceptionModel,
    CrimePublisher,
    RumorBuffer,
    load_air_quality_csv,
    load_domain_config,
)
from civicmesh.network.peer_info import PeerInfo
from civicmesh.pubsub.network_adapter import PubSubPeer


REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Ejecuta un publicador de CivicMesh."
    )

    parser.add_argument(
        "--domain",
        choices=("crime", "air"),
        required=True,
    )

    parser.add_argument(
        "--commune",
        required=True,
    )

    parser.add_argument(
        "--id",
        dest="peer_id",
        required=True,
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )

    parser.add_argument(
        "--port",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--seed-id",
        required=True,
    )

    parser.add_argument(
        "--seed-host",
        required=True,
    )

    parser.add_argument(
        "--seed-port",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--pollutant",
        choices=("pm2_5", "pm10"),
        default="pm2_5",
    )

    return parser.parse_args()


def validate_args(args):

    if args.interval <= 0:
        raise ValueError(
            "--interval debe ser mayor que cero"
        )


def build_publisher(
    args,
    peer,
    rumors,
    config,
):

    if args.domain == "crime":

        if args.commune not in config.crime_rates:
            raise ValueError(
                f"Comuna sin tasas de delitos: "
                f"{args.commune}"
            )

        generator = CrimeGenerator(
            config.crime_rates,
            seed=config.seed,
            delta_t=config.delta_t,
        )

        perception = CrimePerceptionModel(
            commune=args.commune,
            config=config.crime_perception,
            seed=config.seed,
        )

        return CrimePublisher(
            commune=args.commune,
            generator=generator,
            perception=perception,
            publish=peer.pubsub.publish,
            rumor_provider=rumors.consume,
        )

    dataset_path = (
        REPO_ROOT
        / config.air_dataset
    )

    samples = load_air_quality_csv(
        dataset_path
    )

    replay = AirQualityReplay(
        samples=samples,
        commune=args.commune,
    )

    perception = AirPerceptionModel(
        commune=args.commune,
        config=config.air_perception,
        seed=config.seed,
    )

    return AirQualityPublisher(
        commune=args.commune,
        replay=replay,
        perception=perception,
        publish=peer.pubsub.publish,
        rumor_provider=rumors.consume,
        pollutant=args.pollutant,
    )


async def run(args):

    validate_args(args)

    config = load_domain_config()

    rumors = RumorBuffer()

    def on_message(message):

        rumors.record_message(
            message,
            own_peer_id=args.peer_id,
        )

    peer = PubSubPeer(
        peer_id=args.peer_id,
        host=args.host,
        port=args.port,
        delivery_function=on_message,
        random_seed=config.seed,
    )

    try:

        # 1. Levantar publicador
        await peer.start()

        # 2. Conectarse a la malla
        seed = PeerInfo(
            peer_id=args.seed_id,
            host=args.seed_host,
            port=args.seed_port,
        )

        await peer.join(seed)

        # 3. Escuchar rumores subjetivos
        # del mismo tópico
        peer.pubsub.subscribe(
            args.commune
        )

        # 4. Crear publicador del dominio
        publisher = build_publisher(
            args,
            peer,
            rumors,
            config,
        )

        print(
            f"[{args.peer_id}] "
            f"domain={args.domain} "
            f"commune={args.commune} "
            f"interval={args.interval}s"
        )

        step = 0

        while True:

            try:

                if args.domain == "crime":

                    publisher.tick(
                        f"step-{step}"
                    )

                else:

                    publisher.tick()

            except StopIteration:

                print(
                    f"[{args.peer_id}] "
                    "Replay de aire finalizado."
                )

                break

            step += 1

            await asyncio.sleep(
                args.interval
            )

    finally:

        await peer.stop()


def main():

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
            run(args)
        )

    except KeyboardInterrupt:

        print(
            "\nPublicador detenido por el usuario."
        )

    except (
        ValueError,
        ConnectionError,
    ) as error:

        print(
            f"Error: {error}"
        )


if __name__ == "__main__":
    main()
