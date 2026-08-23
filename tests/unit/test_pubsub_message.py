import pytest

from civicmesh.pubsub.message import PubSubMessage


def test_create_pubsub_message():
    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 5},
        origin="peer-1",
        ttl=3,
        priority=100,
    )

    assert message.topic == "estacion-central"
    assert message.channel == "objective"
    assert message.payload == {"crime_count": 5}
    assert message.origin == "peer-1"
    assert message.ttl == 3
    assert message.hop_count == 0
    assert message.priority == 100
    assert message.message_id


def test_forward_message_updates_ttl_and_hop_count():
    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 5},
        origin="peer-1",
        ttl=3,
        priority=100,
    )

    forwarded = message.forwarded_copy()

    assert forwarded.message_id == message.message_id
    assert forwarded.ttl == 2
    assert forwarded.hop_count == 1


def test_invalid_channel_is_rejected():
    with pytest.raises(ValueError):
        PubSubMessage(
            topic="estacion-central",
            channel="invalid",
            payload={},
            origin="peer-1",
            ttl=3,
            priority=100,
        )


def test_message_with_exhausted_ttl_cannot_be_forwarded():
    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={},
        origin="peer-1",
        ttl=0,
        priority=100,
    )

    with pytest.raises(ValueError):
        message.forwarded_copy()

def test_message_to_dict():
    message = PubSubMessage(
        message_id="message-123",
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 5},
        origin="peer-1",
        ttl=3,
        priority=100,
        hop_count=1,
    )

    result = message.to_dict()

    assert result == {
        "message_id": "message-123",
        "topic": "estacion-central",
        "channel": "objective",
        "payload": {"crime_count": 5},
        "origin": "peer-1",
        "ttl": 3,
        "priority": 100,
        "hop_count": 1,
    }


def test_message_from_dict():
    data = {
        "message_id": "message-456",
        "topic": "santiago",
        "channel": "subjective",
        "payload": {"perception": 0.75},
        "origin": "peer-2",
        "ttl": 2,
        "priority": 50,
        "hop_count": 1,
    }

    message = PubSubMessage.from_dict(data)

    assert message.message_id == "message-456"
    assert message.topic == "santiago"
    assert message.channel == "subjective"
    assert message.payload == {"perception": 0.75}
    assert message.origin == "peer-2"
    assert message.ttl == 2
    assert message.priority == 50
    assert message.hop_count == 1


def test_message_serialization_round_trip():
    original = PubSubMessage(
        message_id="message-789",
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 8},
        origin="peer-1",
        ttl=4,
        priority=100,
        hop_count=0,
    )

    serialized = original.to_dict()
    restored = PubSubMessage.from_dict(serialized)

    assert restored == original