from civicmesh.pubsub.forwarding import (
    select_forward_targets,
    should_forward,
)
from civicmesh.pubsub.message import PubSubMessage


def create_objective_message(
    ttl=4,
    hop_count=0,
    priority=100,
):
    return PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 5},
        origin="peer-1",
        ttl=ttl,
        priority=priority,
        hop_count=hop_count,
    )


def test_valid_message_should_be_forwarded():
    message = create_objective_message()

    local_view = [
        "peer-2",
        "peer-3",
    ]

    result = should_forward(
        message,
        "estacion-central",
        local_view,
    )

    assert result is True


def test_message_with_zero_ttl_is_not_forwarded():
    message = create_objective_message(ttl=0)

    local_view = [
        "peer-2",
        "peer-3",
    ]

    result = should_forward(
        message,
        "estacion-central",
        local_view,
    )

    assert result is False


def test_message_at_maximum_hop_count_is_not_forwarded():
    message = create_objective_message(
        ttl=1,
        hop_count=4,
    )

    local_view = [
        "peer-2",
    ]

    result = should_forward(
        message,
        "estacion-central",
        local_view,
    )

    assert result is False


def test_message_below_channel_priority_is_not_forwarded():
    message = create_objective_message(
        priority=99,
    )

    local_view = [
        "peer-2",
    ]

    result = should_forward(
        message,
        "estacion-central",
        local_view,
    )

    assert result is False


def test_message_with_channel_priority_is_forwarded():
    message = create_objective_message(
        priority=100,
    )

    local_view = [
        "peer-2",
    ]

    result = should_forward(
        message,
        "estacion-central",
        local_view,
    )

    assert result is True


def test_message_for_different_topic_is_not_forwarded():
    message = create_objective_message()

    local_view = [
        "peer-2",
    ]

    result = should_forward(
        message,
        "santiago",
        local_view,
    )

    assert result is False


def test_message_is_not_forwarded_without_peers():
    message = create_objective_message()

    result = should_forward(
        message,
        "estacion-central",
        [],
    )

    assert result is False


def test_fanout_limits_number_of_targets():
    local_view = [
        "peer-2",
        "peer-3",
        "peer-4",
        "peer-5",
    ]

    targets = select_forward_targets(
        local_view,
        fanout=2,
    )

    assert targets == [
        "peer-2",
        "peer-3",
    ]


def test_fanout_does_not_invent_peers():
    local_view = [
        "peer-2",
        "peer-3",
    ]

    targets = select_forward_targets(
        local_view,
        fanout=5,
    )

    assert targets == [
        "peer-2",
        "peer-3",
    ]


def test_duplicate_peers_are_not_selected_twice():
    local_view = [
        "peer-2",
        "peer-2",
        "peer-3",
    ]

    targets = select_forward_targets(
        local_view,
        fanout=3,
    )

    assert targets == [
        "peer-2",
        "peer-3",
    ]