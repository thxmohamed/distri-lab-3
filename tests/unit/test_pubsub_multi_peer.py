from civicmesh.pubsub.router import PubSubRouter


def test_message_reaches_subscriber_through_intermediate_peer():
    routers = {}

    topology = {
        "peer-1": ["peer-2"],
        "peer-2": ["peer-1", "peer-3"],
        "peer-3": ["peer-2"],
    }

    delivered = {
        "peer-1": [],
        "peer-2": [],
        "peer-3": [],
    }

    def make_send_function(sender_id):
        def send(target_id, message):
            routers[target_id].receive(
                message,
                sender=sender_id,
            )

        return send

    for node_id in topology:
        routers[node_id] = PubSubRouter(
            node_id=node_id,
            local_view_provider=lambda node_id=node_id: topology[node_id],
            send_function=make_send_function(node_id),
            delivery_function=delivered[node_id].append,
        )

    routers["peer-3"].subscribe("estacion-central")

    original_message = routers["peer-1"].publish(
        topic="estacion-central",
        channel="objective",
        payload={"crime_count": 5},
    )

    assert delivered["peer-1"] == []
    assert delivered["peer-2"] == []

    assert len(delivered["peer-3"]) == 1

    received_message = delivered["peer-3"][0]

    assert received_message.message_id == original_message.message_id
    assert received_message.topic == "estacion-central"
    assert received_message.channel == "objective"
    assert received_message.payload == {
        "crime_count": 5
    }

    assert received_message.ttl == 2
    assert received_message.hop_count == 2

def test_ttl_stops_message_before_distant_subscriber():
    routers = {}

    topology = {
        "peer-1": ["peer-2"],
        "peer-2": ["peer-1", "peer-3"],
        "peer-3": ["peer-2", "peer-4"],
        "peer-4": ["peer-3"],
    }

    delivered = {
        "peer-1": [],
        "peer-2": [],
        "peer-3": [],
        "peer-4": [],
    }

    def make_send_function(sender_id):
        def send(target_id, message):
            routers[target_id].receive(
                message,
                sender=sender_id,
            )

        return send

    for node_id in topology:
        routers[node_id] = PubSubRouter(
            node_id=node_id,
            local_view_provider=lambda node_id=node_id: topology[node_id],
            send_function=make_send_function(node_id),
            delivery_function=delivered[node_id].append,
        )

    routers["peer-4"].subscribe("estacion-central")

    routers["peer-1"].publish(
        topic="estacion-central",
        channel="subjective",
        payload={"perception": 0.75},
    )

    assert delivered["peer-1"] == []
    assert delivered["peer-2"] == []
    assert delivered["peer-3"] == []
    assert delivered["peer-4"] == []