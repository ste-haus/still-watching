import logging
import time

import requests

from still_watching.config import STOP_ACTION_STOP


logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10
MESSAGE_HEADER = "Still Watching"
MESSAGE_TIMEOUT_MS = 7000
MESSAGE_LEAD_SECONDS = 5
GO_HOME_DELAY_SECONDS = 2


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

    def ask_still_watching(self, session_id):
        """Show the still-watching message, then pause or stop the session."""
        try:
            self.display_message(session_id)
        except requests.RequestException as error:
            logger.warning("Could not show the message on session %s: %s", session_id, error)

        self._sleep(MESSAGE_LEAD_SECONDS)

        try:
            if self._settings.stop_action == STOP_ACTION_STOP:
                self._post(f"/Sessions/{session_id}/Playing/Stop")
                self._sleep(GO_HOME_DELAY_SECONDS)
                self._post(f"/Sessions/{session_id}/Command/GoHome")
            else:
                self._post(f"/Sessions/{session_id}/Playing/Pause")
        except requests.RequestException as error:
            logger.error("Could not %s session %s: %s", self._settings.stop_action.lower(), session_id, error)
            return False

        logger.info("Sent %s to session %s", self._settings.stop_action, session_id)
        return True
