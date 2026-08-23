from civicmesh.pubsub.message import PubSubMessage
from civicmesh.pubsub.metrics import PubSubMetrics
from civicmesh.pubsub.router import PubSubRouter


def test_metrics_start_at_zero():
    metrics = PubSubMetrics()

    assert metrics.snapshot() == {
        "published": 0,
        "received": 0,
        "delivered": 0,
        "forwarded": 0,
        "dropped_duplicate": 0,
    }


def test_publish_updates_metrics():
    sent_messages = []

    router = PubSubRouter(
        node_id="peer-1",
        local_view_provider=lambda: [
            "peer-2",
            "peer-3",
        ],
        send_function=lambda peer, message: sent_messages.append(
            (peer, message)
        ),
        delivery_function=lambda message: None,
    )

    router.publish(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 5},
    )

    assert router.metrics.published == 1
    assert router.metrics.forwarded == 2
    assert router.metrics.received == 0
    assert router.metrics.delivered == 0
    assert router.metrics.dropped_duplicate == 0


def test_delivery_updates_metrics():
    router = PubSubRouter(
        node_id="peer-2",
        local_view_provider=lambda: [],
        send_function=lambda peer, message: None,
        delivery_function=lambda message: None,
    )

    router.subscribe("estacion-central")

    message = PubSubMessage(
        message_id="message-1",
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 7},
        origin="peer-1",
        ttl=3,
        priority=100,
    )

    router.receive(
        message,
        sender="peer-1",
    )

    assert router.metrics.received == 1
    assert router.metrics.delivered == 1
    assert router.metrics.dropped_duplicate == 0


def test_duplicate_updates_metrics():
    router = PubSubRouter(
        node_id="peer-2",
        local_view_provider=lambda: [],
        send_function=lambda peer, message: None,
        delivery_function=lambda message: None,
    )

    message = PubSubMessage(
        message_id="message-1",
        topic="estacion-central",
        channel="objective",
        payload={},
        origin="peer-1",
        ttl=3,
        priority=100,
    )

    router.receive(
        message,
        sender="peer-1",
    )

    router.receive(
        message,
        sender="peer-1",
    )

    assert router.metrics.received == 2
    assert router.metrics.dropped_duplicate == 1