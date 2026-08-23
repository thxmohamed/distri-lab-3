import asyncio

from civicmesh.network.gossip import GossipManager
from civicmesh.network.membership import Membership
from civicmesh.network.peer_info import PeerInfo


def create_gossip_manager(
    fanout: int = 2,
) -> GossipManager:

    own_info = PeerInfo(
        peer_id="peer-A",
        host="127.0.0.1",
        port=5000,
    )

    membership = Membership(
        self_id="peer-A"
    )

    return GossipManager(
        membership=membership,
        own_info=own_info,
        fanout=fanout,
        interval_seconds=3,
        seed=123,
    )


def test_build_gossip_message():

    gossip = create_gossip_manager()

    gossip.membership.register_direct_contact(
        "peer-B",
        "127.0.0.1",
        5001,
    )

    message = gossip.build_gossip_message()

    assert message["type"] == "GOSSIP"

    assert (
        message["sender"]["peer_id"]
        == "peer-A"
    )

    assert len(message["members"]) == 1

    assert (
        message["members"][0]["peer_id"]
        == "peer-B"
    )


def test_select_targets_respects_fanout():

    gossip = create_gossip_manager(
        fanout=2
    )

    gossip.membership.register_direct_contact(
        "peer-B",
        "127.0.0.1",
        5001,
    )

    gossip.membership.register_direct_contact(
        "peer-C",
        "127.0.0.1",
        5002,
    )

    gossip.membership.register_direct_contact(
        "peer-D",
        "127.0.0.1",
        5003,
    )

    targets = gossip.select_targets()

    assert len(targets) == 2


def test_dead_peer_is_not_selected():

    gossip = create_gossip_manager()

    gossip.membership.register_direct_contact(
        "peer-B",
        "127.0.0.1",
        5001,
    )

    gossip.membership.mark_dead(
        "peer-B"
    )

    targets = gossip.select_targets()

    assert len(targets) == 0


def test_process_gossip_sender_is_direct():

    gossip = create_gossip_manager()

    message = {
        "type": "GOSSIP",

        "sender": {
            "peer_id": "peer-B",
            "host": "127.0.0.1",
            "port": 5001,
        },

        "members": [],
    }

    gossip.process_gossip_message(
        message
    )

    peer_b = gossip.membership.get_peer(
        "peer-B"
    )

    assert peer_b is not None
    assert peer_b.status == "alive"
    assert peer_b.last_seen is not None


def test_gossip_members_are_indirect():

    gossip = create_gossip_manager()

    message = {
        "type": "GOSSIP",

        "sender": {
            "peer_id": "peer-B",
            "host": "127.0.0.1",
            "port": 5001,
        },

        "members": [
            {
                "peer_id": "peer-C",
                "host": "127.0.0.1",
                "port": 5002,
            }
        ],
    }

    discovered = (
        gossip.process_gossip_message(
            message
        )
    )

    peer_c = gossip.membership.get_peer(
        "peer-C"
    )

    assert discovered == 1

    assert peer_c is not None
    assert peer_c.status == "unknown"
    assert peer_c.last_seen is None


def test_gossip_round_sends_to_targets():

    async def scenario():

        gossip = create_gossip_manager(
            fanout=2
        )

        gossip.membership.register_direct_contact(
            "peer-B",
            "127.0.0.1",
            5001,
        )

        gossip.membership.register_direct_contact(
            "peer-C",
            "127.0.0.1",
            5002,
        )

        sent_to = []

        async def fake_send(
            peer,
            message,
        ):
            sent_to.append(
                peer.peer_id
            )

            assert (
                message["type"]
                == "GOSSIP"
            )

        count = await gossip.gossip_round(
            fake_send
        )

        assert count == 2
        assert len(sent_to) == 2

    asyncio.run(
        scenario()
    )