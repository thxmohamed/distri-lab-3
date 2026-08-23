from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from civicmesh.network.peer import Peer
from civicmesh.pubsub.message import PubSubMessage
from civicmesh.pubsub.router import PubSubRouter


logger = logging.getLogger(__name__)


DeliveryFunction = Callable[[PubSubMessage], None]


class PubSubPeer(Peer):
    """
    Integra la capa de red/gossip de Peer con PubSubRouter.

    Peer se encarga de:
    - TCP
    - JSON
    - membresía
    - gossip
    - detección de fallos

    PubSubRouter se encarga de:
    - tópicos
    - suscripciones
    - TTL
    - prioridad
    - hop count
    - fanout
    - deduplicación
    - should_forward
    """

    def __init__(
        self,
        peer_id: str,
        host: str,
        port: int,
        *,
        delivery_function: DeliveryFunction,
        geography: dict[str, list[str]] | None = None,
        tracker_size: int = 1000,
        **peer_kwargs: Any,
    ) -> None:
        super().__init__(
            peer_id=peer_id,
            host=host,
            port=port,
            **peer_kwargs,
        )

        self._pubsub_send_tasks: set[asyncio.Task] = set()

        self.pubsub = PubSubRouter(
            node_id=peer_id,
            local_view_provider=self._pubsub_local_view,
            send_function=self._schedule_pubsub_send,
            delivery_function=delivery_function,
            geography=geography,
            tracker_size=tracker_size,
        )

    def _pubsub_local_view(self) -> list[str]:
        """
        Convierte la vista de membresía del Rol 1
        a los peer_id que espera PubSubRouter.
        """

        return [
            peer.peer_id
            for peer in self.membership.get_connectable_peers()
        ]

    def _schedule_pubsub_send(
        self,
        target_id: str,
        message: PubSubMessage,
    ) -> None:
        """
        Adapta el envío síncrono esperado por PubSubRouter
        al send_message asíncrono de Peer.
        """

        target = self.membership.get_peer(target_id)

        if target is None:
            return

        if not target.is_connectable():
            return

        envelope = self.build_pubsub_message(message)

        task = asyncio.create_task(
            self.send_message(
                target,
                envelope,
            )
        )

        self._pubsub_send_tasks.add(task)

        task.add_done_callback(
            self._handle_pubsub_send_done
        )

    def _handle_pubsub_send_done(
        self,
        task: asyncio.Task,
    ) -> None:
        self._pubsub_send_tasks.discard(task)

        try:
            task.result()

        except asyncio.CancelledError:
            pass

        except (
            ConnectionError,
            OSError,
            asyncio.TimeoutError,
        ) as error:
            logger.warning(
                "[%s] Error enviando PUBSUB: %s",
                self.own_info.peer_id,
                error,
            )

    def build_pubsub_message(
        self,
        message: PubSubMessage,
    ) -> dict:
        """
        Construye el mensaje JSON que viajará por la red.
        """

        return {
            "type": "PUBSUB",
            "sender": self.own_info.to_dict(),
            "message": message.to_dict(),
        }

    async def handle_message(
        self,
        message: dict,
    ) -> None:
        """
        Intercepta mensajes PUBSUB.

        JOIN y GOSSIP siguen siendo procesados
        exactamente por Peer (Rol 1).
        """

        if (
            isinstance(message, dict)
            and message.get("type") == "PUBSUB"
        ):
            self._handle_pubsub_message(message)
            return

        await super().handle_message(message)

    def _handle_pubsub_message(
        self,
        envelope: dict,
    ) -> None:
        sender = envelope.get("sender")
        message_data = envelope.get("message")

        if not isinstance(sender, dict):
            return

        if not isinstance(message_data, dict):
            return

        sender_id = sender.get("peer_id")
        sender_host = sender.get("host")
        sender_port = sender.get("port")

        if (
            sender_id is None
            or sender_host is None
            or sender_port is None
        ):
            return

        try:
            self.membership.register_direct_contact(
                peer_id=sender_id,
                host=sender_host,
                port=sender_port,
            )

            pubsub_message = PubSubMessage.from_dict(
                message_data
            )

        except (
            ValueError,
            TypeError,
            KeyError,
        ) as error:
            logger.warning(
                "[%s] Mensaje PUBSUB inválido: %s",
                self.own_info.peer_id,
                error,
            )
            return

        self.pubsub.receive(
            pubsub_message,
            sender=sender_id,
        )

    async def stop(self) -> None:
        """
        Detiene también los envíos PUBSUB pendientes.
        """

        pending_tasks = list(
            self._pubsub_send_tasks
        )

        for task in pending_tasks:
            task.cancel()

        if pending_tasks:
            await asyncio.gather(
                *pending_tasks,
                return_exceptions=True,
            )

        self._pubsub_send_tasks.clear()

        await super().stop()