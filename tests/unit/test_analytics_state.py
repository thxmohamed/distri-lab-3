from civicmesh.analytics import AnalyticsState


def test_record_tracks_last_value_and_timestamp():

    state = AnalyticsState()

    state.record(
        "estacion-central",
        "objective",
        3,
        "t1",
    )

    state.record(
        "estacion-central",
        "objective",
        5,
        "t2",
    )

    topic_state = state.get(
        "estacion-central",
        "objective",
    )

    assert topic_state.last_value == 5
    assert topic_state.last_timestamp == "t2"
    assert len(topic_state.history) == 2


def test_topic_and_channel_are_independent():

    state = AnalyticsState()

    state.record(
        "estacion-central",
        "objective",
        3,
        "t1",
    )

    state.record(
        "estacion-central",
        "subjective",
        0.8,
        "t1",
    )

    objective = state.get(
        "estacion-central", "objective"
    )
    subjective = state.get(
        "estacion-central", "subjective"
    )

    assert objective.last_value == 3
    assert subjective.last_value == 0.8


def test_snapshot_lists_every_topic_channel():

    state = AnalyticsState()

    state.record(
        "estacion-central",
        "objective",
        3,
        "t1",
    )

    state.record(
        "maipu",
        "subjective",
        0.4,
        "t1",
    )

    snapshot = state.snapshot()

    assert set(snapshot.keys()) == {
        "estacion-central:objective",
        "maipu:subjective",
    }

    assert (
        snapshot["estacion-central:objective"][
            "last_value"
        ]
        == 3
    )
