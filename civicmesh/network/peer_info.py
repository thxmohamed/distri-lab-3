from dataclasses import dataclass
import time


@dataclass
class PeerInfo:
    """
    Información local conocida sobre un peer de CivicMesh.
    """

    peer_id: str
    host: str
    port: int

    # Solo se actualiza cuando existe comunicación directa.
    last_seen: float | None = None

    # Estados:
    # unknown -> sabemos que existe, pero no hemos hablado directamente.
    # alive   -> hemos recibido comunicación directa.
    # dead    -> fue considerado caído por timeout.
    status: str = "unknown"

    def touch(self) -> None:
        """
        Registra comunicación directa con este peer.
        """
        self.last_seen = time.time()
        self.status = "alive"

    def mark_dead(self) -> None:
        """
        Marca el peer como caído.
        """
        self.status = "dead"

    def is_alive(self) -> bool:
        """
        Retorna True solamente si existe evidencia directa
        de que el peer está vivo.
        """
        return self.status == "alive"

    def is_connectable(self) -> bool:
        """
        Permite intentar conexión con peers vivos o recién descubiertos.
        """
        return self.status != "dead"

    def address(self) -> tuple[str, int]:
        """
        Retorna (host, port).
        """
        return self.host, self.port

    def to_dict(self) -> dict:
        """
        Representación serializable para mensajes JOIN/GOSSIP.
        No se envían last_seen ni status porque son estados locales.
        """
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
        }