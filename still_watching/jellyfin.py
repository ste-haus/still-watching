import logging
import time

import requests

from still_watching.config import STOP_ACTION_STOP


logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10
MESSAGE_HEADER = "Still Watching"
MILLISECONDS_PER_SECOND = 1000
GO_HOME_DELAY_SECONDS = 2

# Some clients (Jellyfin for Android TV) ignore TimeoutMs and show a message for a short fixed
# time, so the message is resent to keep it on screen. Each copy still carries a timeout matching
# the resend interval, so clients that honor it show one continuous message instead of stacking
# copies or holding one indefinitely.
MESSAGE_REPEAT_COUNT = 5
MESSAGE_REPEAT_INTERVAL_SECONDS = 3
MESSAGE_TIMEOUT_MS = MESSAGE_REPEAT_INTERVAL_SECONDS * MILLISECONDS_PER_SECOND


class JellyfinClient:
    def __init__(self, settings, session=None, sleep=time.sleep):
        self._settings = settings
        self._http = session or requests.Session()
        self._sleep = sleep
        self._headers = {"Authorization": f'MediaBrowser Token="{settings.api_token}"'}

    def _post(self, path, payload=None):
        response = self._http.post(
            f"{self._settings.api_url}{path}",
            json=payload,
            headers=self._headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

    def display_message(self, session_id):
        self._post(
            f"/Sessions/{session_id}/Command",
            {
                "Name": "DisplayMessage",
                "Arguments": {
                    "Header": MESSAGE_HEADER,
                    "Text": self._settings.message,
                    "TimeoutMs": str(MESSAGE_TIMEOUT_MS),
                },
            },
        )

    def _stop_playback(self, session_id):
        if self._settings.stop_action == STOP_ACTION_STOP:
            self._post(f"/Sessions/{session_id}/Playing/Stop")
            self._sleep(GO_HOME_DELAY_SECONDS)
            self._post(f"/Sessions/{session_id}/Command/GoHome")
        else:
            self._post(f"/Sessions/{session_id}/Playing/Pause")

    def _repeat_message(self, session_id):
        for attempt in range(MESSAGE_REPEAT_COUNT):
            if attempt:
                self._sleep(MESSAGE_REPEAT_INTERVAL_SECONDS)

            try:
                self.display_message(session_id)
            except requests.RequestException as error:
                logger.warning("Could not show the message on session %s: %s", session_id, error)
                return

    def ask_still_watching(self, session_id):
        """Pause or stop the session, then keep the still-watching message on screen."""
        stopped = True

        try:
            self._stop_playback(session_id)
        except requests.RequestException as error:
            logger.error("Could not %s session %s: %s", self._settings.stop_action.lower(), session_id, error)
            stopped = False
        else:
            logger.info("Sent %s to session %s", self._settings.stop_action, session_id)

        self._repeat_message(session_id)
        return stopped
