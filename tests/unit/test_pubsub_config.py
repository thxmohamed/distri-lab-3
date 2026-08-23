import pytest

from civicmesh.pubsub.config import (
    ChannelPolicy,
    get_channel_policy,
    load_channel_policies,
)


def test_objective_channel_policy():
    policy = get_channel_policy("objective")

    assert policy.ttl == 4
    assert policy.priority == 100
    assert policy.fanout == 3


def test_subjective_channel_policy():
    policy = get_channel_policy("subjective")

    assert policy.ttl == 2
    assert policy.priority == 50
    assert policy.fanout == 2


def test_channels_have_independent_policies():
    objective = get_channel_policy("objective")
    subjective = get_channel_policy("subjective")

    assert objective.ttl != subjective.ttl
    assert objective.priority != subjective.priority
    assert objective.fanout != subjective.fanout


def test_invalid_channel_is_rejected():
    with pytest.raises(ValueError):
        get_channel_policy("invalid")


def test_zero_ttl_is_rejected():
    with pytest.raises(ValueError):
        ChannelPolicy(
            ttl=0,
            priority=100,
            fanout=3,
        )


def test_negative_priority_is_rejected():
    with pytest.raises(ValueError):
        ChannelPolicy(
            ttl=3,
            priority=-1,
            fanout=3,
        )


def test_zero_fanout_is_rejected():
    with pytest.raises(ValueError):
        ChannelPolicy(
            ttl=3,
            priority=100,
            fanout=0,
        )

def test_load_channel_policies_from_yaml(tmp_path):
    config_file = tmp_path / "pubsub.yaml"

    config_file.write_text(
        """
pubsub:
  channels:
    objective:
      ttl: 8
      priority: 200
      fanout: 5

    subjective:
      ttl: 3
      priority: 40
      fanout: 1
""",
        encoding="utf-8",
    )

    policies = load_channel_policies(config_file)

    assert policies["objective"].ttl == 8
    assert policies["objective"].priority == 200
    assert policies["objective"].fanout == 5

    assert policies["subjective"].ttl == 3
    assert policies["subjective"].priority == 40
    assert policies["subjective"].fanout == 1


def test_missing_required_channel_is_rejected(tmp_path):
    config_file = tmp_path / "pubsub.yaml"

    config_file.write_text(
        """
pubsub:
  channels:
    objective:
      ttl: 4
      priority: 100
      fanout: 3
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_channel_policies(config_file)


def test_invalid_policy_from_yaml_is_rejected(tmp_path):
    config_file = tmp_path / "pubsub.yaml"

    config_file.write_text(
        """
pubsub:
  channels:
    objective:
      ttl: 0
      priority: 100
      fanout: 3

    subjective:
      ttl: 2
      priority: 50
      fanout: 2
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_channel_policies(config_file)