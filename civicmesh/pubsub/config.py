from dataclasses import dataclass
from pathlib import Path

import yaml


REQUIRED_CHANNELS = {
    "objective",
    "subjective",
}

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "pubsub.yaml"
)


@dataclass(frozen=True)
class ChannelPolicy:
    ttl: int
    priority: int
    fanout: int

    def __post_init__(self) -> None:
        if self.ttl <= 0:
            raise ValueError("ttl must be greater than zero")

        if self.priority < 0:
            raise ValueError("priority cannot be negative")

        if self.fanout <= 0:
            raise ValueError("fanout must be greater than zero")


def load_channel_policies(
    path: str | Path = DEFAULT_CONFIG_PATH,
) -> dict[str, ChannelPolicy]:
    config_path = Path(path)

    with config_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError("configuration must be a mapping")

    pubsub_config = data.get("pubsub")

    if not isinstance(pubsub_config, dict):
        raise ValueError("missing pubsub configuration")

    channels = pubsub_config.get("channels")

    if not isinstance(channels, dict):
        raise ValueError("missing channels configuration")

    missing_channels = REQUIRED_CHANNELS - channels.keys()

    if missing_channels:
        missing = ", ".join(sorted(missing_channels))
        raise ValueError(
            f"missing required channels: {missing}"
        )

    policies: dict[str, ChannelPolicy] = {}

    for channel in REQUIRED_CHANNELS:
        values = channels[channel]

        if not isinstance(values, dict):
            raise ValueError(
                f"configuration for {channel} must be a mapping"
            )

        try:
            policy = ChannelPolicy(
                ttl=int(values["ttl"]),
                priority=int(values["priority"]),
                fanout=int(values["fanout"]),
            )
        except KeyError as exc:
            raise ValueError(
                f"missing parameter for channel {channel}: "
                f"{exc.args[0]}"
            ) from exc

        policies[channel] = policy

    return policies


CHANNEL_POLICIES = load_channel_policies()


def get_channel_policy(channel: str) -> ChannelPolicy:
    try:
        return CHANNEL_POLICIES[channel]
    except KeyError as exc:
        raise ValueError(
            f"unknown channel: {channel}"
        ) from exc