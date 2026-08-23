import pytest

from civicmesh.pubsub.deduplication import MessageTracker


def test_new_message_has_not_been_seen():
    tracker = MessageTracker()

    assert tracker.has_seen("message-1") is False


def test_marked_message_is_seen():
    tracker = MessageTracker()

    tracker.mark_seen("message-1")

    assert tracker.has_seen("message-1") is True


def test_check_and_mark_accepts_new_message():
    tracker = MessageTracker()

    result = tracker.check_and_mark("message-1")

    assert result is True
    assert tracker.has_seen("message-1") is True


def test_check_and_mark_rejects_duplicate_message():
    tracker = MessageTracker()

    first_result = tracker.check_and_mark("message-1")
    second_result = tracker.check_and_mark("message-1")

    assert first_result is True
    assert second_result is False


def test_marking_same_message_twice_does_not_duplicate_it():
    tracker = MessageTracker()

    tracker.mark_seen("message-1")
    tracker.mark_seen("message-1")

    assert tracker.size() == 1


def test_tracker_removes_oldest_message_when_full():
    tracker = MessageTracker(max_size=3)

    tracker.mark_seen("message-1")
    tracker.mark_seen("message-2")
    tracker.mark_seen("message-3")
    tracker.mark_seen("message-4")

    assert tracker.has_seen("message-1") is False
    assert tracker.has_seen("message-2") is True
    assert tracker.has_seen("message-3") is True
    assert tracker.has_seen("message-4") is True
    assert tracker.size() == 3


def test_empty_message_id_is_rejected():
    tracker = MessageTracker()

    with pytest.raises(ValueError):
        tracker.mark_seen("")


def test_invalid_max_size_is_rejected():
    with pytest.raises(ValueError):
        MessageTracker(max_size=0)