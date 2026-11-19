import pytest

from still_watching.config import Settings
from still_watching.events import ITEM_TYPE_EPISODE, ITEM_TYPE_MOVIE, TICKS_PER_SECOND, parse_event
from still_watching.tracker import RunTracker


SECONDS_PER_MINUTE = 60
EPISODE_MINUTES = 22
EPISODE_SECONDS = EPISODE_MINUTES * SECONDS_PER_MINUTE

RUN_LENGTH = 4
RUN_GAP_SECONDS = 10 * SECONDS_PER_MINUTE
START_DELAY_SECONDS = 60

USER = "user-1"
DEVICE = "tv-1"
SESSION = "session-1"
SERIES_A = "series-a"
SERIES_B = "series-b"


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FakeTimer:
    def __init__(self, due, callback):
        self.due = due
        self.callback = callback
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class FakeScheduler:
    def __init__(self, clock):
        self._clock = clock
        self.timers = []

    def schedule(self, delay_seconds, callback):
        timer = FakeTimer(self._clock.now + delay_seconds, callback)
        self.timers.append(timer)
        return timer

    def advance(self, seconds):
        """Move the clock forward, firing due timers in order at their due time."""
        target = self._clock.now + seconds

        while True:
            due = [t for t in self.timers if not t.cancelled and t.due <= target]
            if not due:
                break

            timer = min(due, key=lambda t: t.due)
            self.timers.remove(timer)
            self._clock.now = timer.due
            timer.callback()

        self._clock.now = target


class Harness:
    def __init__(self, settings):
        self.clock = FakeClock()
        self.scheduler = FakeScheduler(self.clock)
        self.asked = []
        self.tracker = RunTracker(settings, ask=self.asked.append, clock=self.clock, scheduler=self.scheduler)

    def event(self, notification, item_id, series_id=SERIES_A, item_type=ITEM_TYPE_EPISODE, device=DEVICE,
              runtime_seconds=EPISODE_SECONDS):
        return parse_event({
            "NotificationType": notification,
            "UserId": USER,
            "DeviceId": device,
            "ItemId": item_id,
            "ItemType": item_type,
            "SeriesId": series_id if item_type == ITEM_TYPE_EPISODE else None,
            "RunTimeTicks": runtime_seconds * TICKS_PER_SECOND,
            "Id": f"{SESSION}-{device}",
            "NotificationUsername": "viewer",
            "DeviceName": device,
            "Name": item_id,
        })

    def start(self, item_id, **kwargs):
        self.tracker.handle_start(self.event("PlaybackStart", item_id, **kwargs))

    def stop(self, item_id, **kwargs):
        self.tracker.handle_stop(self.event("PlaybackStop", item_id, **kwargs))

    def watch(self, item_id, minutes=EPISODE_MINUTES, **kwargs):
        """Start an episode, play it through, and stop it."""
        self.start(item_id, **kwargs)
        self.wait(minutes * SECONDS_PER_MINUTE)
        self.stop(item_id, **kwargs)

    def wait(self, seconds):
        self.scheduler.advance(seconds)

    def wait_minutes(self, minutes):
        self.wait(minutes * SECONDS_PER_MINUTE)

    def count(self, device=DEVICE):
        viewer = self.tracker.viewer(f"{USER}-{device}")
        return 0 if viewer is None else viewer.run_count


@pytest.fixture
def settings():
    return Settings(
        api_url="http://jellyfin.test",
        api_token="token",
        run_length=RUN_LENGTH,
        run_gap_seconds=RUN_GAP_SECONDS,
        start_delay_seconds=START_DELAY_SECONDS,
    )


@pytest.fixture
def harness(settings):
    return Harness(settings)


MOVIE = ITEM_TYPE_MOVIE
