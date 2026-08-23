from __future__ import annotations

import logging
from typing import Iterable

from .peer_info import PeerInfo


logger = logging.getLogger(__name__)


class Membership:
    """
    Mantiene la vista local de peers conocidos por un peer.
    """

    def __init__(
        self,
        self_id: str,
        max_view_size: int | None = None,
    ) -> None:

        if not self_id:
            raise ValueError(
                "self_id no puede estar vacío"
            )

        if (
            max_view_size is not None
            and max_view_size <= 0
        ):
            raise ValueError(
                "max_view_size debe ser mayor que 0"
            )

        self.self_id = self_id
        self.max_view_size = max_view_size

        self._peers: dict[str, PeerInfo] = {}

    # =========================================================
    # MÉTODOS BÁSICOS
    # =========================================================

    def __len__(self) -> int:
        return len(self._peers)

    def __contains__(
        self,
        peer_id: str,
    ) -> bool:

        return peer_id in self._peers

    def get_peer(
        self,
        peer_id: str,
    ) -> PeerInfo | None:

        return self._peers.get(peer_id)

    # =========================================================
    # DESCUBRIMIENTO INDIRECTO
    # =========================================================

    def discover_peer(
        self,
        peer_id: str,
        host: str,
        port: int,
    ) -> PeerInfo | None:
        """
        Registra un peer descubierto indirectamente
        mediante Gossip.

        No actualiza last_seen.
        """

        self._validate_peer_data(
            peer_id,
            host,
            port,
        )

        if peer_id == self.self_id:
            return None

        existing_peer = self._peers.get(
            peer_id
        )

        # -----------------------------------------------------
        # Peer completamente nuevo
        # -----------------------------------------------------

        if existing_peer is None:

            peer = PeerInfo(
                peer_id=peer_id,
                host=host,
                port=port,
                last_seen=None,
                status="unknown",
            )

            self._peers[peer_id] = peer

            logger.info(
                "[%s] Peer descubierto indirectamente: "
                "%s (%s:%s)",
                self.self_id,
                peer_id,
                host,
                port,
            )

            self._enforce_view_limit(
                protected_peer_id=peer_id
            )

            return peer

        # -----------------------------------------------------
        # Información indirecta
        # -----------------------------------------------------

        if existing_peer.status != "alive":

            existing_peer.host = host
            existing_peer.port = port

        return existing_peer

    # =========================================================
    # CONTACTO DIRECTO
    # =========================================================

    def register_direct_contact(
        self,
        peer_id: str,
        host: str,
        port: int,
    ) -> PeerInfo | None:
        """
        Registra evidencia de comunicación directa.
        """

        self._validate_peer_data(
            peer_id,
            host,
            port,
        )

        if peer_id == self.self_id:
            return None

        peer = self._peers.get(
            peer_id
        )

        # Guardamos estado anterior para detectar
        # nuevos peers o recuperaciones.
        previous_status: str | None = None

        if peer is None:

            peer = PeerInfo(
                peer_id=peer_id,
                host=host,
                port=port,
            )

            self._peers[peer_id] = peer

            logger.info(
                "[%s] Nuevo contacto directo: "
                "%s (%s:%s)",
                self.self_id,
                peer_id,
                host,
                port,
            )

        else:

            previous_status = peer.status

            peer.host = host
            peer.port = port

        peer.touch()

        # -----------------------------------------------------
        # Peer que estaba DEAD volvió
        # -----------------------------------------------------

        if previous_status == "dead":

            logger.info(
                "[%s] Peer %s volvió a estar ALIVE",
                self.self_id,
                peer_id,
            )

        # -----------------------------------------------------
        # Peer UNKNOWN fue confirmado
        # -----------------------------------------------------

        elif previous_status == "unknown":

            logger.info(
                "[%s] Peer %s confirmado como ALIVE",
                self.self_id,
                peer_id,
            )

        self._enforce_view_limit(
            protected_peer_id=peer_id
        )

        return peer

    # =========================================================
    # GOSSIP
    # =========================================================

    def merge_gossip_members(
        self,
        members: Iterable[dict],
    ) -> int:

        discovered_count = 0

        for member in members:

            if not isinstance(
                member,
                dict,
            ):
                continue

            peer_id = member.get(
                "peer_id"
            )

            host = member.get(
                "host"
            )

            port = member.get(
                "port"
            )

            if (
                peer_id is None
                or host is None
                or port is None
            ):
                continue

            was_known = (
                peer_id in self._peers
            )

            try:

                peer = self.discover_peer(
                    peer_id=peer_id,
                    host=host,
                    port=port,
                )

            except (
                ValueError,
                TypeError,
            ):
                continue

            if (
                peer is not None
                and not was_known
            ):
                discovered_count += 1

        return discovered_count

    # =========================================================
    # ESTADO
    # =========================================================

    def mark_dead(
        self,
        peer_id: str,
    ) -> bool:

        peer = self._peers.get(
            peer_id
        )

        if peer is None:
            return False

        peer.mark_dead()

        return True

    def get_alive_peers(
        self,
    ) -> list[PeerInfo]:

        return [
            peer
            for peer in self._peers.values()
            if peer.is_alive()
        ]

    def get_connectable_peers(
        self,
    ) -> list[PeerInfo]:

        return [
            peer
            for peer in self._peers.values()
            if peer.is_connectable()
        ]

    def get_all_peers(
        self,
    ) -> list[PeerInfo]:

        return list(
            self._peers.values()
        )

    # =========================================================
    # ELIMINACIÓN
    # =========================================================

    def remove_peer(
        self,
        peer_id: str,
    ) -> bool:

        if peer_id not in self._peers:
            return False

        del self._peers[
            peer_id
        ]

        logger.info(
            "[%s] Peer eliminado de la vista: %s",
            self.self_id,
            peer_id,
        )

        return True

    # =========================================================
    # SERIALIZACIÓN GOSSIP
    # =========================================================

    def to_gossip_payload(
        self,
    ) -> list[dict]:

        return [
            peer.to_dict()
            for peer in self._peers.values()
            if peer.is_connectable()
        ]

    # =========================================================
    # VISTA PARCIAL
    # =========================================================

    def _enforce_view_limit(
        self,
        protected_peer_id: str | None = None,
    ) -> None:

        if self.max_view_size is None:
            return

        while (
            len(self._peers)
            > self.max_view_size
        ):

            candidates = [
                peer
                for peer in self._peers.values()
                if (
                    peer.peer_id
                    != protected_peer_id
                )
            ]

            if not candidates:
                return

            peer_to_remove = min(
                candidates,
                key=self._eviction_priority,
            )

            del self._peers[
                peer_to_remove.peer_id
            ]

            logger.info(
                "[%s] Peer removido por límite "
                "de vista parcial: %s",
                self.self_id,
                peer_to_remove.peer_id,
            )

    @staticmethod
    def _eviction_priority(
        peer: PeerInfo,
    ) -> tuple[int, float]:

        if peer.status == "dead":
            status_priority = 0

        elif peer.status == "unknown":
            status_priority = 1

        else:
            status_priority = 2

        last_seen = (
            peer.last_seen
            if peer.last_seen is not None
            else 0.0
        )

        return (
            status_priority,
            last_seen,
        )

    # =========================================================
    # VALIDACIONES
    # =========================================================

    @staticmethod
    def _validate_peer_data(
        peer_id: str,
        host: str,
        port: int,
    ) -> None:

        if not isinstance(
            peer_id,
            str,
        ):
            raise TypeError(
                "peer_id debe ser str"
            )

        if not peer_id.strip():
            raise ValueError(
                "peer_id no puede estar vacío"
            )

        if not isinstance(
            host,
            str,
        ):
            raise TypeError(
                "host debe ser str"
            )

        if not host.strip():
            raise ValueError(
                "host no puede estar vacío"
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