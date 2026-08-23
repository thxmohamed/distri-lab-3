import pytest

from civicmesh.pubsub.subscriptions import SubscriptionManager


def test_subscribe_to_topic():
    manager = SubscriptionManager()

    manager.subscribe("estacion-central")

    assert manager.is_subscribed("estacion-central") is True


def test_unsubscribed_topic_returns_false():
    manager = SubscriptionManager()

    assert manager.is_subscribed("estacion-central") is False


def test_unsubscribe_from_topic():
    manager = SubscriptionManager()

    manager.subscribe("estacion-central")
    manager.unsubscribe("estacion-central")

    assert manager.is_subscribed("estacion-central") is False


def test_subscribe_with_neighbors():
    geography = {
        "estacion-central": [
            "santiago",
            "quinta-normal",
        ],
        "santiago": [
            "estacion-central",
        ],
    }

    manager = SubscriptionManager(geography)

    manager.subscribe(
        "estacion-central",
        include_neighbors=True,
    )

    assert manager.get_subscriptions() == {
        "estacion-central",
        "santiago",
        "quinta-normal",
    }


def test_subscribe_without_neighbors():
    geography = {
        "estacion-central": [
            "santiago",
            "quinta-normal",
        ]
    }

    manager = SubscriptionManager(geography)

    manager.subscribe(
        "estacion-central",
        include_neighbors=False,
    )

    assert manager.get_subscriptions() == {
        "estacion-central",
    }


def test_duplicate_subscription_is_not_duplicated():
    manager = SubscriptionManager()

    manager.subscribe("estacion-central")
    manager.subscribe("estacion-central")

    assert manager.get_subscriptions() == {
        "estacion-central",
    }


def test_empty_topic_is_rejected():
    manager = SubscriptionManager()

    with pytest.raises(ValueError):
        manager.subscribe("")