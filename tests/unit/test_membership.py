from civicmesh.network.membership import Membership


def test_register_direct_peer():

    membership = Membership(
        self_id="peer-A"
    )

    peer = membership.register_direct_contact(
        peer_id="peer-B",
        host="127.0.0.1",
        port=5001,
    )

    assert peer is not None
    assert peer.peer_id == "peer-B"
    assert peer.status == "alive"
    assert peer.last_seen is not None


def test_discover_indirect_peer():

    membership = Membership(
        self_id="peer-A"
    )

    peer = membership.discover_peer(
        peer_id="peer-C",
        host="127.0.0.1",
        port=5002,
    )

    assert peer is not None
    assert peer.status == "unknown"
    assert peer.last_seen is None


def test_does_not_add_itself():

    membership = Membership(
        self_id="peer-A"
    )

    peer = membership.register_direct_contact(
        peer_id="peer-A",
        host="127.0.0.1",
        port=5000,
    )

    assert peer is None
    assert len(membership) == 0


def test_alive_peers():

    membership = Membership(
        self_id="peer-A"
    )

    membership.register_direct_contact(
        "peer-B",
        "127.0.0.1",
        5001,
    )

    membership.discover_peer(
        "peer-C",
        "127.0.0.1",
        5002,
    )

    alive = membership.get_alive_peers()

    assert len(alive) == 1
    assert alive[0].peer_id == "peer-B"


def test_mark_dead():

    membership = Membership(
        self_id="peer-A"
    )

    membership.register_direct_contact(
        "peer-B",
        "127.0.0.1",
        5001,
    )

    result = membership.mark_dead(
        "peer-B"
    )

    peer = membership.get_peer(
        "peer-B"
    )

    assert result is True
    assert peer is not None
    assert peer.status == "dead"
    assert peer.is_alive() is False


def test_merge_gossip():

    membership = Membership(
        self_id="peer-A"
    )

    count = membership.merge_gossip_members(
        [
            {
                "peer_id": "peer-B",
                "host": "127.0.0.1",
                "port": 5001,
            },
            {
                "peer_id": "peer-C",
                "host": "127.0.0.1",
                "port": 5002,
            },
        ]
    )

    assert count == 2
    assert "peer-B" in membership
    assert "peer-C" in membership

    assert (
        membership.get_peer("peer-B").status
        == "unknown"
    )


def test_dead_peer_not_connectable():

    membership = Membership(
        self_id="peer-A"
    )

    membership.register_direct_contact(
        "peer-B",
        "127.0.0.1",
        5001,
    )

    membership.mark_dead(
        "peer-B"
    )

    candidates = (
        membership.get_connectable_peers()
    )

    assert len(candidates) == 0


def test_view_limit():

    membership = Membership(
        self_id="peer-A",
        max_view_size=2,
    )

    membership.discover_peer(
        "peer-B",
        "127.0.0.1",
        5001,
    )

    membership.discover_peer(
        "peer-C",
        "127.0.0.1",
        5002,
    )

    membership.discover_peer(
        "peer-D",
        "127.0.0.1",
        5003,
    )

    assert len(membership) == 2