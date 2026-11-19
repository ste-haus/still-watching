import json
import logging

from flask import Flask, jsonify, request

from still_watching.config import load_settings
from still_watching.events import NOTIFICATION_PLAYBACK_START, NOTIFICATION_PLAYBACK_STOP, parse_event
from still_watching.jellyfin import JellyfinClient
from still_watching.tracker import RunTracker


HTTP_OK = 200
HTTP_BAD_REQUEST = 400
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

logger = logging.getLogger(__name__)


def create_app(tracker=None):
    if tracker is None:
        settings = load_settings()
        client = JellyfinClient(settings)
        tracker = RunTracker(settings, ask=client.ask_still_watching)

    app = Flask(__name__)

    handlers = {
        NOTIFICATION_PLAYBACK_START: tracker.handle_start,
        NOTIFICATION_PLAYBACK_STOP: tracker.handle_stop,
    }

    @app.post("/webhook")
    def webhook():
        # The Webhook plugin does not always label its body as JSON, so parse the raw data.
        try:
            payload = json.loads(request.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return jsonify({"message": "Body is not JSON"}), HTTP_BAD_REQUEST

        if not isinstance(payload, dict):
            return jsonify({"message": "Body is not a JSON object"}), HTTP_BAD_REQUEST

        event = parse_event(payload)
        handler = handlers.get(event.notification_type)

        if handler is None:
            return jsonify({"message": f"Ignored {event.notification_type or 'unknown'} event"}), HTTP_OK

        handler(event)
        return jsonify({"message": "Event processed"}), HTTP_OK

    return app


def build():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    return create_app()
