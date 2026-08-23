from civicmesh.network.failure_detector import FailureDetector
from civicmesh.network.membership import Membership


def test_recent_peer_remains_alive():
    """
    Un peer cuyo último contacto todavía está dentro
    del timeout debe mantenerse alive.
    """

    current_time = 100.0

    membership = Membership(
        self_id="peer-A"
    )

    peer_b = membership.register_direct_contact(
        peer_id="peer-B",
        host="127.0.0.1",
        port=5001,
    )

    assert peer_b is not None

    # Simulamos que B fue visto hace 5 segundos.
    peer_b.last_seen = 95.0

    detector = FailureDetector(
        membership=membership,
        timeout_seconds=10.0,
        clock=lambda: current_time,
    )

    dead_peers = detector.check_failures()

    assert peer_b.status == "alive"
    assert dead_peers == []


def test_peer_is_marked_dead_after_timeout():
    """
    Si elapsed > timeout, el peer debe pasar de
    alive a dead.
    """

    current_time = 100.0

    membership = Membership(
        self_id="peer-A"
    )

    peer_b = membership.register_direct_contact(
        peer_id="peer-B",
        host="127.0.0.1",
        port=5001,
    )

    assert peer_b is not None

    # B fue visto hace 15 segundos.
    peer_b.last_seen = 85.0

    detector = FailureDetector(
        membership=membership,
        timeout_seconds=10.0,
        clock=lambda: current_time,
    )

    dead_peers = detector.check_failures()

    assert peer_b.status == "dead"

    assert len(dead_peers) == 1
    assert dead_peers[0].peer_id == "peer-B"


def test_peer_at_exact_timeout_remains_alive():
    """
    Nuestra política utiliza:

        elapsed > timeout

    Por lo tanto, exactamente en el límite todavía
    permanece alive.
    """

    current_time = 100.0

    membership = Membership(
        self_id="peer-A"
    )

    peer_b = membership.register_direct_contact(
        peer_id="peer-B",
        host="127.0.0.1",
        port=5001,
    )

    assert peer_b is not None

    peer_b.last_seen = 90.0

    detector = FailureDetector(
        membership=membership,
        timeout_seconds=10.0,
        clock=lambda: current_time,
    )

    detector.check_failures()

    assert peer_b.status == "alive"


def test_unknown_peer_is_not_marked_dead():
    """
    Un peer descubierto indirectamente no tiene
    last_seen y no debe procesarse como fallo.
    """

    membership = Membership(
        self_id="peer-A"
    )

    peer_c = membership.discover_peer(
        peer_id="peer-C",
        host="127.0.0.1",
        port=5002,
    )

    assert peer_c is not None
    assert peer_c.status == "unknown"
    assert peer_c.last_seen is None

    detector = FailureDetector(
        membership=membership,
        timeout_seconds=10.0,
        clock=lambda: 1000.0,
    )

    dead_peers = detector.check_failures()

    assert peer_c.status == "unknown"
    assert dead_peers == []


def test_already_dead_peer_remains_dead():
    """
    Un peer que ya estaba muerto no debe volver a
    aparecer como newly_dead.
    """

    membership = Membership(
        self_id="peer-A"
    )

    peer_b = membership.register_direct_contact(
        peer_id="peer-B",
        host="127.0.0.1",
        port=5001,
    )

    assert peer_b is not None

    peer_b.last_seen = 10.0

    membership.mark_dead(
        "peer-B"
    )

    detector = FailureDetector(
        membership=membership,
        timeout_seconds=10.0,
        clock=lambda: 100.0,
    )

    dead_peers = detector.check_failures()

    assert peer_b.status == "dead"

    # No murió en ESTA ejecución:
    # ya estaba muerto anteriormente.
    assert dead_peers == []


def test_multiple_peers_are_checked():
    """
    Comprueba que el detector revise toda la
    vista de membresía.
    """

    current_time = 100.0

    membership = Membership(
        self_id="peer-A"
    )

    peer_b = membership.register_direct_contact(
        "peer-B",
        "127.0.0.1",
        5001,
    )

    peer_c = membership.register_direct_contact(
        "peer-C",
        "127.0.0.1",
        5002,
    )

    peer_d = membership.register_direct_contact(
        "peer-D",
        "127.0.0.1",
        5003,
    )

    assert peer_b is not None
    assert peer_c is not None
    assert peer_d is not None

    # B fue visto recientemente.
    peer_b.last_seen = 97.0

    # C y D excedieron timeout.
    peer_c.last_seen = 80.0
    peer_d.last_seen = 70.0

    detector = FailureDetector(
        membership=membership,
        timeout_seconds=10.0,
        clock=lambda: current_time,
    )

    dead_peers = detector.check_failures()

    assert peer_b.status == "alive"
    assert peer_c.status == "dead"
    assert peer_d.status == "dead"

    dead_ids = {
        peer.peer_id
        for peer in dead_peers
    }

    assert dead_ids == {
        "peer-C",
        "peer-D",
    }