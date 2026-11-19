"""Episode-run tracking.

A run is a sequence of episodes of one series watched on one device by one user, where each
episode starts within the run gap of the previous one ending. An episode only joins the run once
it has played for the start delay, so skipping past an episode does not count it. When an episode
would make the run longer than the run length, the viewer is asked whether they are still watching
and that episode becomes the first of a new run.
"""

import logging
import threading
import time
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class TimerScheduler:
    def schedule(self, delay_seconds, callback):
        timer = threading.Timer(delay_seconds, callback)
        timer.daemon = True
        timer.start()
        return timer


@dataclass
class Episode:
    item_id: str
    series_id: str | None
    started_at: float
    runtime_seconds: float
    session_id: str | None
    label: str
    counted: bool = False
    ended_at: float | None = None
    pending: object = None

    def end_time(self, now):
        if self.ended_at is not None:
            return self.ended_at

        # No stop arrived (the client vanished, or it moved on without one). Assume the episode ran
        # its full length, but never past now, since a new start means this one is over.
        if self.runtime_seconds > 0:
            return min(now, self.started_at + self.runtime_seconds)

        return self.started_at


@dataclass
class Viewer:
    username: str
    device_name: str
    run_series_id: str | None = None
    run_count: int = 0
    current: Episode | None = None

    def reset(self):
        self.run_series_id = None
        self.run_count = 0
        self.current = None


class RunTracker:
    def __init__(self, settings, ask, clock=time.monotonic, scheduler=None):
        self._settings = settings
        self._ask = ask
        self._clock = clock
        self._scheduler = scheduler or TimerScheduler()
        self._viewers = {}
        self._lock = threading.Lock()

    def viewer(self, key):
        return self._viewers.get(key)

    def _viewer_for(self, event):
        viewer = self._viewers.get(event.viewer_key)

        if viewer is None:
            viewer = Viewer(username=event.username, device_name=event.device_name)
            self._viewers[event.viewer_key] = viewer

        return viewer

    @staticmethod
    def _cancel_pending(episode):
        if episode is not None and episode.pending is not None:
            episode.pending.cancel()
            episode.pending = None

    def _schedule_confirmation(self, key, episode):
        episode.pending = self._scheduler.schedule(
            self._settings.start_delay_seconds,
            lambda: self.confirm(key, episode),
        )

    def _continues_run(self, viewer, event, now):
        previous = viewer.current

        if previous is None or viewer.run_series_id is None:
            return False

        if event.series_id != viewer.run_series_id:
            return False

        return now - previous.end_time(now) <= self._settings.run_gap_seconds

    # Event handlers

    def handle_start(self, event):
        now = self._clock()

        with self._lock:
            viewer = self._viewer_for(event)
            current = viewer.current

            if event.is_movie:
                self._cancel_pending(current)
                viewer.reset()
                logger.info("%s on %s started a movie; run reset", viewer.username, viewer.device_name)
                return

            if not event.is_episode:
                return

            if current is not None and current.item_id == event.item_id:
                current.ended_at = None
                current.session_id = event.session_id or current.session_id

                if current.counted:
                    logger.info("%s resumed %s; run stays at %d", viewer.username, current.label, viewer.run_count)
                    return

                self._cancel_pending(current)
                self._schedule_confirmation(event.viewer_key, current)
                return

            if current is not None and not current.counted:
                self._cancel_pending(current)
                logger.info("%s skipped past %s before it counted", viewer.username, current.label)

            if not self._continues_run(viewer, event, now):
                viewer.run_series_id = event.series_id
                viewer.run_count = 0

            episode = Episode(
                item_id=event.item_id,
                series_id=event.series_id,
                started_at=now,
                runtime_seconds=event.runtime_seconds,
                session_id=event.session_id,
                label=event.label,
            )
            viewer.current = episode
            self._schedule_confirmation(event.viewer_key, episode)

    def handle_stop(self, event):
        now = self._clock()

        with self._lock:
            viewer = self._viewers.get(event.viewer_key)

            if viewer is None or not event.is_episode:
                return

            current = viewer.current

            if current is None or current.item_id != event.item_id:
                return

            current.ended_at = now

            if not current.counted:
                self._cancel_pending(current)
                logger.info("%s stopped %s before it counted", viewer.username, current.label)

    def confirm(self, key, episode):
        """Count an episode that has played for the start delay, asking if it makes the run too long."""
        with self._lock:
            viewer = self._viewers.get(key)

            if viewer is None or viewer.current is not episode:
                return

            episode.pending = None

            if episode.counted or episode.ended_at is not None:
                return

            episode.counted = True
            viewer.run_count += 1

            if viewer.run_count <= self._settings.run_length:
                logger.info(
                    "%s on %s: %s is episode %d of %d in a row",
                    viewer.username, viewer.device_name, episode.label, viewer.run_count, self._settings.run_length,
                )
                return

            viewer.run_count = 1
            session_id = episode.session_id
            username = viewer.username
            device_name = viewer.device_name

        logger.info(
            "%s on %s passed %d episodes in a row; asking if they are still watching",
            username, device_name, self._settings.run_length,
        )

        if session_id is None:
            logger.warning("No session id for %s on %s; cannot ask", username, device_name)
            return

        self._ask(session_id)
