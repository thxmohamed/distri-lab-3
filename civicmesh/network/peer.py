from __future__ import annotations

import asyncio
import json
import logging

from .failure_detector import FailureDetector
from .gossip import GossipManager
from .membership import Membership
from .peer_info import PeerInfo


logger = logging.getLogger(__name__)


class Peer:

    def __init__(
        self,
        peer_id: str,
        host: str,
        port: int,
        *,
        max_view_size: int = 10,
        fanout: int = 2,
        gossip_interval: float = 3.0,
        random_seed: int | None = None,
        connection_timeout: float = 5.0,
        failure_timeout: float = 10.0,
        failure_check_interval: float = 2.0,
    ) -> None:
    

        self._validate_configuration(
            peer_id=peer_id,
            host=host,
            port=port,
            max_view_size=max_view_size,
            connection_timeout=connection_timeout,
            failure_timeout=failure_timeout,
            failure_check_interval=failure_check_interval,
        )

        self.own_info = PeerInfo(
            peer_id=peer_id,
            host=host,
            port=port,
        )

        self.own_info.touch()

        self.membership = Membership(
            self_id=peer_id,
            max_view_size=max_view_size,
        )

        self.gossip = GossipManager(
            membership=self.membership,
            own_info=self.own_info,
            fanout=fanout,
            interval_seconds=gossip_interval,
            seed=random_seed,
        )

        self.failure_detector = FailureDetector(
            membership=self.membership,
            timeout_seconds=failure_timeout,
            check_interval_seconds=failure_check_interval,
        )

        self.connection_timeout = (
            connection_timeout
        )

        self._server: asyncio.Server | None = None
        self._gossip_task: asyncio.Task | None = None
        self._failure_detector_task: asyncio.Task | None = None

        self._running = False

    # =========================================================
    # INICIO
    # =========================================================

    async def start(self) -> None:

        if self._running:
            return

        self._server = await asyncio.start_server(
            self._handle_connection,
            self.own_info.host,
            self.own_info.port,
        )

        self._running = True

        self._gossip_task = asyncio.create_task(
            self.gossip.gossip_loop(
                self.send_message
            )
        )

        self._failure_detector_task = asyncio.create_task(
            self.failure_detector
            .failure_detection_loop()
        )

        logger.info(
            "[%s] Peer iniciado en %s:%s",
            self.own_info.peer_id,
            self.own_info.host,
            self.own_info.port,
        )

    async def serve_forever(
        self,
    ) -> None:

        if not self._running:
            await self.start()

        if self._server is None:
            raise RuntimeError(
                "El servidor no pudo iniciarse"
            )

        async with self._server:
            await self._server.serve_forever()

    # =========================================================
    # DETENCIÓN
    # =========================================================

    async def stop(self) -> None:

        if not self._running:
            return

        self._running = False

        if self._gossip_task is not None:

            self._gossip_task.cancel()

            try:
                await self._gossip_task

            except asyncio.CancelledError:
                pass

            self._gossip_task = None

        if (
            self._failure_detector_task
            is not None
        ):

            self._failure_detector_task.cancel()

            try:
                await self._failure_detector_task

            except asyncio.CancelledError:
                pass

            self._failure_detector_task = None

        if self._server is not None:

            self._server.close()
            await self._server.wait_closed()

            self._server = None

        logger.info(
            "[%s] Peer detenido",
            self.own_info.peer_id,
        )

    # =========================================================
    # RECIBIR
    # =========================================================

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:

        try:

            data = await asyncio.wait_for(
                reader.readline(),
                timeout=self.connection_timeout,
            )

            if not data:
                return

            try:

                message = json.loads(
                    data.decode("utf-8")
                )

            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
            ):

                logger.warning(
                    "[%s] Mensaje JSON inválido",
                    self.own_info.peer_id,
                )

                return

            await self.handle_message(
                message
            )

        except asyncio.TimeoutError:

            logger.warning(
                "[%s] Timeout recibiendo mensaje",
                self.own_info.peer_id,
            )

        except ConnectionError as error:

            logger.warning(
                "[%s] Error de conexión: %s",
                self.own_info.peer_id,
                error,
            )

        finally:

            writer.close()

            try:
                await writer.wait_closed()

            except (
                ConnectionError,
                OSError,
            ):
                pass

    # =========================================================
    # ENVÍO
    # =========================================================

    async def send_message(
        self,
        peer: PeerInfo,
        message: dict,
    ) -> None:

        if (
            peer.peer_id
            == self.own_info.peer_id
        ):
            return

        try:

            _, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    peer.host,
                    peer.port,
                ),
                timeout=self.connection_timeout,
            )

            serialized_message = (
                json.dumps(message) + "\n"
            ).encode("utf-8")

            writer.write(
                serialized_message
            )

            await asyncio.wait_for(
                writer.drain(),
                timeout=self.connection_timeout,
            )

            writer.close()

            try:
                await writer.wait_closed()

            except (
                ConnectionError,
                OSError,
            ):
                pass

        except asyncio.TimeoutError as error:

            raise ConnectionError(
                f"Timeout conectando con "
                f"{peer.peer_id}"
            ) from error

        except OSError as error:

            raise ConnectionError(
                f"No fue posible conectar con "
                f"{peer.peer_id} "
                f"({peer.host}:{peer.port})"
            ) from error

    # =========================================================
    # PROCESAMIENTO
    # =========================================================

    async def handle_message(
        self,
        message: dict,
    ) -> None:

        if not isinstance(
            message,
            dict,
        ):
            return

        message_type = message.get(
            "type"
        )

        if message_type == "JOIN":

            self._handle_join(
                message
            )

        elif message_type == "GOSSIP":

            self._handle_gossip(
                message
            )

        else:

            logger.warning(
                "[%s] Tipo de mensaje desconocido: %s",
                self.own_info.peer_id,
                message_type,
            )

    # =========================================================
    # JOIN
    # =========================================================

    def build_join_message(
        self,
    ) -> dict:

        return {
            "type": "JOIN",
            "sender": self.own_info.to_dict(),
        }

    async def join(
        self,
        seed_peer: PeerInfo,
    ) -> None:

        if (
            seed_peer.peer_id
            == self.own_info.peer_id
        ):
            return

        message = (
            self.build_join_message()
        )

        await self.send_message(
            seed_peer,
            message,
        )

        self.membership.register_direct_contact(
            peer_id=seed_peer.peer_id,
            host=seed_peer.host,
            port=seed_peer.port,
        )

        logger.info(
            "[%s] JOIN enviado a %s",
            self.own_info.peer_id,
            seed_peer.peer_id,
        )

    def _handle_join(
        self,
        message: dict,
    ) -> None:

        sender = message.get(
            "sender"
        )

        if not isinstance(
            sender,
            dict,
        ):
            return

        peer_id = sender.get(
            "peer_id"
        )

        host = sender.get(
            "host"
        )

        port = sender.get(
            "port"
        )

        if (
            peer_id is None
            or host is None
            or port is None
        ):
            return

        try:

            peer = (
                self.membership
                .register_direct_contact(
                    peer_id=peer_id,
                    host=host,
                    port=port,
                )
            )

        except (
            ValueError,
            TypeError,
        ):
            return

        if peer is not None:

            logger.info(
                "[%s] JOIN recibido desde %s",
                self.own_info.peer_id,
                peer.peer_id,
            )

    # =========================================================
    # GOSSIP
    # =========================================================

    def _handle_gossip(
        self,
        message: dict,
    ) -> None:

        try:

            discovered = (
                self.gossip
                .process_gossip_message(
                    message
                )
            )

        except (
            ValueError,
            TypeError,
        ) as error:

            logger.warning(
                "[%s] GOSSIP inválido: %s",
                self.own_info.peer_id,
                error,
            )

            return

        sender = message.get(
            "sender",
            {},
        )

        sender_id = sender.get(
            "peer_id",
            "desconocido",
        )

        logger.debug(
            "[%s] GOSSIP recibido desde %s. "
            "Nuevos peers: %s",
            self.own_info.peer_id,
            sender_id,
            discovered,
        )

    # =========================================================
    # ESTADO
    # =========================================================

    def print_membership(
        self,
    ) -> None:

        peers = (
            self.membership
            .get_all_peers()
        )

        print(
            f"\n[{self.own_info.peer_id}] "
            "Vista de membresía:"
        )

        if not peers:

            print(
                "  Sin peers conocidos"
            )
            return

        for peer in peers:

            print(
                f"  {peer.peer_id} "
                f"{peer.host}:{peer.port} "
                f"status={peer.status} "
                f"last_seen={peer.last_seen}"
            )

    # =========================================================
    # VALIDACIONES
    # =========================================================

    @staticmethod
    def _validate_configuration(
        peer_id: str,
        host: str,
        port: int,
        max_view_size: int,
        connection_timeout: float,
        failure_timeout: float,
        failure_check_interval: float,
    ) -> None:


        if (
            not isinstance(peer_id, str)
            or not peer_id.strip()
        ):
            raise ValueError(
                "peer_id debe ser un string no vacío"
            )

        if (
            not isinstance(host, str)
            or not host.strip()
        ):
            raise ValueError(
                "host debe ser un string no vacío"
            )

        if not isinstance(
            port,
            int,
        ):
            raise TypeError(
                "port debe ser int"
            )

        if not 1 <= port <= 65535:
            raise ValueError(
                "port debe estar entre 1 y 65535"
            )
        if not isinstance(max_view_size,int):
            raise TypeError(
                "max_view_size debe ser int"
            )
        if max_view_size <= 0:
            raise ValueError(
                "max_view_size debe ser mayor que 0"
            )


        if connection_timeout <= 0:
            raise ValueError(
                "connection_timeout debe ser mayor que 0"
            )

        if failure_timeout <= 0:
            raise ValueError(
                "failure_timeout debe ser mayor que 0"
            )

        if failure_check_interval <= 0:
            raise ValueError(
                "failure_check_interval debe ser mayor que 0"
            )