from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable

from .membership import Membership
from .peer_info import PeerInfo


# Función que posteriormente implementará Peer para enviar
# realmente un mensaje por red.
SendMessageFunction = Callable[
    [PeerInfo, dict],
    Awaitable[None]
]


class GossipManager:
    """
    Gestiona el protocolo de gossip de membresía de CivicMesh.

    Responsabilidades:
    - Seleccionar peers destino según el fanout.
    - Construir mensajes GOSSIP.
    - Procesar mensajes GOSSIP recibidos.
    - Registrar contacto directo con el emisor.
    - Fusionar los peers conocidos por otros nodos.
    - Ejecutar rondas periódicas de gossip.

    Esta clase NO implementa directamente TCP/UDP.
    El transporte será responsabilidad de Peer.
    """

    def __init__(
        self,
        membership: Membership,
        own_info: PeerInfo,
        fanout: int = 2,
        interval_seconds: float = 3.0,
        seed: int | None = None,
    ) -> None:

        if fanout <= 0:
            raise ValueError(
                "fanout debe ser mayor que 0"
            )

        if interval_seconds <= 0:
            raise ValueError(
                "interval_seconds debe ser mayor que 0"
            )

        if own_info.peer_id != membership.self_id:
            raise ValueError(
                "own_info.peer_id debe coincidir "
                "con membership.self_id"
            )

        self.membership = membership
        self.own_info = own_info

        self.fanout = fanout
        self.interval_seconds = interval_seconds

        # Random propio para no depender del estado global
        # de random.
        self._rng = random.Random(seed)

    # ---------------------------------------------------------
    # Selección de peers
    # ---------------------------------------------------------

    def select_targets(self) -> list[PeerInfo]:
        """
        Selecciona aleatoriamente los peers con los que
        se realizará gossip en una ronda.

        Se utilizan peers conectables:
        - alive
        - unknown

        Los peers dead quedan excluidos.

        Si existen menos peers que el fanout,
        retorna todos los disponibles.
        """

        candidates = (
            self.membership.get_connectable_peers()
        )

        if not candidates:
            return []

        if len(candidates) <= self.fanout:
            return list(candidates)

        return self._rng.sample(
            candidates,
            self.fanout,
        )

    # ---------------------------------------------------------
    # Construcción de mensajes
    # ---------------------------------------------------------

    def build_gossip_message(self) -> dict:
        """
        Construye un mensaje de membresía GOSSIP.

        Ejemplo:

        {
            "type": "GOSSIP",
            "sender": {
                "peer_id": "peer-A",
                "host": "127.0.0.1",
                "port": 5000
            },
            "members": [...]
        }
        """

        return {
            "type": "GOSSIP",
            "sender": self.own_info.to_dict(),
            "members": (
                self.membership.to_gossip_payload()
            ),
        }

    # ---------------------------------------------------------
    # Procesamiento de mensajes
    # ---------------------------------------------------------

    def process_gossip_message(
        self,
        message: dict,
    ) -> int:
        """
        Procesa un mensaje GOSSIP recibido.

        El sender corresponde a comunicación DIRECTA,
        porque acabamos de recibir el mensaje desde ese peer.

        Los elementos de 'members', en cambio, corresponden
        a conocimiento INDIRECTO.

        Retorna:
            Cantidad de peers nuevos descubiertos mediante
            la lista de membresía recibida.

        Lanza ValueError si el mensaje no tiene una
        estructura válida.
        """

        if not isinstance(message, dict):
            raise ValueError(
                "El mensaje GOSSIP debe ser un diccionario"
            )

        if message.get("type") != "GOSSIP":
            raise ValueError(
                "El mensaje recibido no es de tipo GOSSIP"
            )

        sender = message.get("sender")

        if not isinstance(sender, dict):
            raise ValueError(
                "El mensaje GOSSIP no contiene "
                "un sender válido"
            )

        sender_peer_id = sender.get("peer_id")
        sender_host = sender.get("host")
        sender_port = sender.get("port")

        if (
            sender_peer_id is None
            or sender_host is None
            or sender_port is None
        ):
            raise ValueError(
                "El sender del mensaje GOSSIP está incompleto"
            )

        # -----------------------------------------------------
        # 1. Registrar contacto DIRECTO con quien envió Gossip.
        # -----------------------------------------------------

        self.membership.register_direct_contact(
            peer_id=sender_peer_id,
            host=sender_host,
            port=sender_port,
        )

        # -----------------------------------------------------
        # 2. Procesar peers mencionados por el sender.
        #
        # Estos son descubrimientos INDIRECTOS.
        # -----------------------------------------------------

        members = message.get(
            "members",
            [],
        )

        if not isinstance(members, list):
            raise ValueError(
                "'members' debe ser una lista"
            )

        discovered_count = (
            self.membership.merge_gossip_members(
                members
            )
        )

        return discovered_count

    # ---------------------------------------------------------
    # Una ronda de Gossip
    # ---------------------------------------------------------

    async def gossip_round(
        self,
        send_message: SendMessageFunction,
    ) -> int:
        """
        Ejecuta una única ronda de gossip.

        1. Selecciona destinos.
        2. Construye el mensaje.
        3. Envía el mensaje a cada destino.

        El envío real se delega a send_message(), que
        posteriormente será implementado por Peer.

        Retorna:
            Cantidad de peers a los que se intentó enviar
            el mensaje.
        """

        targets = self.select_targets()

        if not targets:
            return 0

        message = self.build_gossip_message()

        for target in targets:
            try:
                await send_message(
                    target,
                    message,
                )

            except (
                ConnectionError,
                OSError,
                asyncio.TimeoutError,
            ):
                # No marcamos inmediatamente como dead.
                #
                # Un fallo de conexión puntual no significa
                # necesariamente que el peer esté caído.
                #
                # FailureDetector se encargará posteriormente
                # de decidirlo mediante timeout.
                continue

        return len(targets)

    # ---------------------------------------------------------
    # Loop periódico
    # ---------------------------------------------------------

    async def gossip_loop(
        self,
        send_message: SendMessageFunction,
    ) -> None:
        """
        Ejecuta rondas de Gossip periódicamente.

        Ejemplo:
            interval_seconds = 3

            t=0  -> ronda
            t=3  -> ronda
            t=6  -> ronda
            ...
        """

        while True:

            await self.gossip_round(
                send_message
            )

            await asyncio.sleep(
                self.interval_seconds
            )