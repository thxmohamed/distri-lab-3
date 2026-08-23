from civicmesh.pubsub.message import PubSubMessage
from civicmesh.pubsub.router import PubSubRouter


def test_publish_sends_message_to_peers():
    sent_messages = []
    delivered_messages = []

    def get_local_view():
        return [
            "peer-2",
            "peer-3",
            "peer-4",
            "peer-5",
        ]

    def send(peer, message):
        sent_messages.append((peer, message))

    def deliver(message):
        delivered_messages.append(message)

    router = PubSubRouter(
        node_id="peer-1",
        local_view_provider=get_local_view,
        send_function=send,
        delivery_function=deliver,
    )

    message = router.publish(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 5},
    )

    assert len(sent_messages) == 3

    assert [
        peer
        for peer, _ in sent_messages
    ] == [
        "peer-2",
        "peer-3",
        "peer-4",
    ]

    assert sent_messages[0][1].message_id == message.message_id
    assert sent_messages[0][1].ttl == 3
    assert sent_messages[0][1].hop_count == 1


def test_publish_respects_subjective_fanout():
    sent_messages = []

    def get_local_view():
        return [
            "peer-2",
            "peer-3",
            "peer-4",
        ]

    def send(peer, message):
        sent_messages.append((peer, message))

    router = PubSubRouter(
        node_id="peer-1",
        local_view_provider=get_local_view,
        send_function=send,
        delivery_function=lambda message: None,
    )

    router.publish(
        topic="estacion-central",
        channel="subjective",
        payload={"perception": 0.8},
    )

    assert len(sent_messages) == 2

    assert [
        peer
        for peer, _ in sent_messages
    ] == [
        "peer-2",
        "peer-3",
    ]


def test_received_message_is_delivered_to_subscriber():
    delivered_messages = []

    router = PubSubRouter(
        node_id="peer-2",
        local_view_provider=lambda: [],
        send_function=lambda peer, message: None,
        delivery_function=delivered_messages.append,
    )

    router.subscribe("estacion-central")

    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 7},
        origin="peer-1",
        ttl=3,
        priority=100,
        hop_count=1,
        message_id="message-123",
    )

    result = router.receive(
        message,
        sender="peer-1",
    )

    assert result is True
    assert len(delivered_messages) == 1
    assert delivered_messages[0].payload == {
        "crime_count": 7
    }


def test_duplicate_message_is_ignored():
    delivered_messages = []

    router = PubSubRouter(
        node_id="peer-2",
        local_view_provider=lambda: [],
        send_function=lambda peer, message: None,
        delivery_function=delivered_messages.append,
    )

    router.subscribe("estacion-central")

    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 7},
        origin="peer-1",
        ttl=3,
        priority=100,
        message_id="message-123",
    )

    first_result = router.receive(
        message,
        sender="peer-1",
    )

    second_result = router.receive(
        message,
        sender="peer-1",
    )

    assert first_result is True
    assert second_result is False
    assert len(delivered_messages) == 1


def test_received_message_can_be_forwarded():
    sent_messages = []

    def send(peer, message):
        sent_messages.append((peer, message))

    router = PubSubRouter(
        node_id="peer-2",
        local_view_provider=lambda: [
            "peer-1",
            "peer-3",
            "peer-4",
        ],
        send_function=send,
        delivery_function=lambda message: None,
    )

    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 4},
        origin="peer-1",
        ttl=3,
        priority=100,
        hop_count=1,
        message_id="message-123",
    )

    router.receive(
        message,
        sender="peer-1",
    )

    assert [
        peer
        for peer, _ in sent_messages
    ] == [
        "peer-3",
        "peer-4",
    ]

    assert sent_messages[0][1].ttl == 2
    assert sent_messages[0][1].hop_count == 2


def test_sender_is_not_immediately_selected_again():
    sent_messages = []

    def send(peer, message):
        sent_messages.append((peer, message))

    router = PubSubRouter(
        node_id="peer-2",
        local_view_provider=lambda: [
            "peer-1",
            "peer-3",
        ],
        send_function=send,
        delivery_function=lambda message: None,
    )

    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={},
        origin="peer-4",
        ttl=3,
        priority=100,
        message_id="message-123",
    )

    router.receive(
        message,
        sender="peer-1",
    )

    assert [
        peer
        for peer, _ in sent_messages
    ] == [
        "peer-3",
    ]


def test_unsubscribed_peer_does_not_deliver_locally():
    delivered_messages = []

    router = PubSubRouter(
        node_id="peer-2",
        local_view_provider=lambda: [],
        send_function=lambda peer, message: None,
        delivery_function=delivered_messages.append,
    )

    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 4},
        origin="peer-1",
        ttl=3,
        priority=100,
        message_id="message-123",
    )

    router.receive(
        message,
        sender="peer-1",
    )

    assert delivered_messages == []


def test_expired_message_is_delivered_but_not_forwarded():
    sent_messages = []
    delivered_messages = []

    router = PubSubRouter(
        node_id="peer-2",
        local_view_provider=lambda: [
            "peer-3",
        ],
        send_function=lambda peer, message: sent_messages.append(
            (peer, message)
        ),
        delivery_function=delivered_messages.append,
    )

    router.subscribe("estacion-central")

    message = PubSubMessage(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 4},
        origin="peer-1",
        ttl=0,
        priority=100,
        hop_count=4,
        message_id="message-123",
    )

    router.receive(
        message,
        sender="peer-1",
    )

    assert len(delivered_messages) == 1
    assert sent_messages == []


def test_router_can_subscribe_with_neighbors():
    geography = {
        "estacion-central": [
            "santiago",
            "quinta-normal",
        ]
    }

    router = PubSubRouter(
        node_id="peer-1",
        local_view_provider=lambda: [],
        send_function=lambda peer, message: None,
        delivery_function=lambda message: None,
        geography=geography,
    )

    router.subscribe(
        "estacion-central",
        include_neighbors=True,
    )

    assert router.subscriptions.get_subscriptions() == {
        "estacion-central",
        "santiago",
        "quinta-normal",
    }