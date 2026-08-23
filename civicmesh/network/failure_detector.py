from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from .membership import Membership
from .peer_info import PeerInfo


logger = logging.getLogger(__name__)


class FailureDetector:
    """
    Detecta peers que dejaron de responder.

    Un peer confirmado como 'alive' se considera caído cuando:

        tiempo_actual - last_seen > timeout_seconds

    El peer se conserva en Membership con status='dead'.
    """

    def __init__(
        self,
        membership: Membership,
        timeout_seconds: float = 10.0,
        check_interval_seconds: float = 2.0,
        clock: Callable[[], float] = time.time,
    ) -> None:

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds debe ser mayor que 0"
            )

        if check_interval_seconds <= 0:
            raise ValueError(
                "check_interval_seconds debe ser mayor que 0"
            )

        self.membership = membership
        self.timeout_seconds = timeout_seconds
        self.check_interval_seconds = check_interval_seconds
        self._clock = clock

    def check_failures(self) -> list[PeerInfo]:
        """
        Marca como dead los peers alive cuyo last_seen
        supera el timeout.

        Retorna los peers que fueron marcados como dead
        durante esta comprobación.
        """

        now = self._clock()

        newly_dead: list[PeerInfo] = []

        for peer in self.membership.get_all_peers():

            if not peer.is_alive():
                continue

            if peer.last_seen is None:
                continue

            elapsed = now - peer.last_seen

            if elapsed < 0:
                continue

            if elapsed > self.timeout_seconds:

                peer.mark_dead()
                newly_dead.append(peer)

                logger.warning(
                    "[%s] Peer %s marcado como DEAD "
                    "por timeout (%.2fs sin contacto)",
                    self.membership.self_id,
                    peer.peer_id,
                    elapsed,
                )

        return newly_dead

    async def failure_detection_loop(self) -> None:
        """
        Ejecuta periódicamente la detección de fallos.
        """

        while True:

            self.check_failures()

            await asyncio.sleep(
                self.check_interval_seconds
            )