from dataclasses import dataclass


TICKS_PER_SECOND = 10_000_000

NOTIFICATION_PLAYBACK_START = "PlaybackStart"
NOTIFICATION_PLAYBACK_STOP = "PlaybackStop"

ITEM_TYPE_EPISODE = "Episode"
ITEM_TYPE_MOVIE = "Movie"

UNKNOWN = "unknown"


@dataclass(frozen=True)
class PlaybackEvent:
    notification_type: str
    user_id: str
    device_id: str
    item_id: str
    item_type: str
    series_id: str | None
    runtime_seconds: float
    session_id: str | None
    username: str
    device_name: str
    name: str
    series_name: str | None

    @property
    def viewer_key(self):
        return f"{self.user_id}-{self.device_id}"

    @property
    def is_episode(self):
        return self.item_type == ITEM_TYPE_EPISODE

    @property
    def is_movie(self):
        return self.item_type == ITEM_TYPE_MOVIE

    @property
    def label(self):
        if self.series_name:
            return f"{self.series_name} - {self.name}"

        return self.name


def _text(payload, key, default=None):
    value = payload.get(key)

    if value is None or value == "":
        return default

    return str(value)


def parse_event(payload):
    """Build a PlaybackEvent from a Jellyfin Webhook plugin payload sent with "Send All Properties"."""
    try:
        ticks = float(payload.get("RunTimeTicks") or 0)
    except (TypeError, ValueError):
        ticks = 0

    return PlaybackEvent(
        notification_type=_text(payload, "NotificationType", ""),
        user_id=_text(payload, "UserId", UNKNOWN),
        device_id=_text(payload, "DeviceId", UNKNOWN),
        item_id=_text(payload, "ItemId", ""),
        item_type=_text(payload, "ItemType", ""),
        series_id=_text(payload, "SeriesId"),
        runtime_seconds=ticks / TICKS_PER_SECOND,
        session_id=_text(payload, "Id"),
        username=_text(payload, "NotificationUsername", UNKNOWN),
        device_name=_text(payload, "DeviceName", UNKNOWN),
        name=_text(payload, "Name", UNKNOWN),
        series_name=_text(payload, "SeriesName"),
    )
