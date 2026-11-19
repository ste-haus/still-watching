import json

import pytest

from still_watching.app import create_app
from still_watching.config import ConfigError, STOP_ACTION_STOP, load_settings
from still_watching.events import TICKS_PER_SECOND, parse_event
from still_watching.jellyfin import JellyfinClient


HTTP_OK = 200
HTTP_BAD_REQUEST = 400
EPISODE_SECONDS = 1320


class RecordingTracker:
    def __init__(self):
        self.starts = []
        self.stops = []

    def handle_start(self, event):
        self.starts.append(event)

    def handle_stop(self, event):
        self.stops.append(event)


@pytest.fixture
def tracker():
    return RecordingTracker()


@pytest.fixture
def client(tracker):
    return create_app(tracker=tracker).test_client()


def test_webhook_routes_start_and_stop(client, tracker):
    start = {"NotificationType": "PlaybackStart", "ItemType": "Episode", "ItemId": "e1"}
    stop = {"NotificationType": "PlaybackStop", "ItemType": "Episode", "ItemId": "e1"}

    assert client.post("/webhook", json=start).status_code == HTTP_OK
    assert client.post("/webhook", data=json.dumps(stop), content_type="text/plain").status_code == HTTP_OK

    assert [e.item_id for e in tracker.starts] == ["e1"]
    assert [e.item_id for e in tracker.stops] == ["e1"]


def test_webhook_ignores_other_notifications(client, tracker):
    response = client.post("/webhook", json={"NotificationType": "ItemAdded"})

    assert response.status_code == HTTP_OK
    assert tracker.starts == [] and tracker.stops == []


def test_webhook_rejects_non_json(client):
    assert client.post("/webhook", data="nope", content_type="text/plain").status_code == HTTP_BAD_REQUEST


def test_parse_event_reads_webhook_fields():
    event = parse_event({
        "NotificationType": "PlaybackStart",
        "UserId": "u",
        "DeviceId": "d",
        "ItemId": "i",
        "ItemType": "Episode",
        "SeriesId": "s",
        "SeriesName": "Show",
        "Name": "Pilot",
        "RunTimeTicks": EPISODE_SECONDS * TICKS_PER_SECOND,
        "Id": "session",
    })

    assert event.viewer_key == "u-d"
    assert event.series_id == "s"
    assert event.runtime_seconds == EPISODE_SECONDS
    assert event.session_id == "session"
    assert event.label == "Show - Pilot"


def test_settings_defaults_and_validation():
    settings = load_settings({"JELLYFIN_API_URL": "http://jf/", "JELLYFIN_API_TOKEN": "t"})

    assert settings.api_url == "http://jf"
    assert settings.run_length == 4
    assert settings.run_gap_seconds == 600
    assert settings.start_delay_seconds == 60
    assert settings.stop_action == "PAUSE"

    with pytest.raises(ConfigError):
        load_settings({"JELLYFIN_API_URL": "http://jf"})

    with pytest.raises(ConfigError):
        load_settings({"JELLYFIN_API_URL": "http://jf", "JELLYFIN_API_TOKEN": "t", "RUN_LENGTH": "0"})

    with pytest.raises(ConfigError):
        load_settings({"JELLYFIN_API_URL": "http://jf", "JELLYFIN_API_TOKEN": "t", "JELLYFIN_STOP_ACTION": "EJECT"})


class RecordingHttp:
    def __init__(self):
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append((url, json, headers))
        return self

    def raise_for_status(self):
        pass


def _client(stop_action=None):
    env = {"JELLYFIN_API_URL": "http://jf", "JELLYFIN_API_TOKEN": "t"}

    if stop_action:
        env["JELLYFIN_STOP_ACTION"] = stop_action

    http = RecordingHttp()
    return JellyfinClient(load_settings(env), session=http, sleep=lambda _: None), http


def test_ask_shows_message_then_pauses():
    jellyfin, http = _client()

    assert jellyfin.ask_still_watching("s1")

    urls = [call[0] for call in http.calls]
    assert urls == ["http://jf/Sessions/s1/Command", "http://jf/Sessions/s1/Playing/Pause"]
    assert http.calls[0][1]["Name"] == "DisplayMessage"
    assert all(call[2]["Authorization"] == 'MediaBrowser Token="t"' for call in http.calls)


def test_ask_can_stop_and_go_home():
    jellyfin, http = _client(STOP_ACTION_STOP)

    jellyfin.ask_still_watching("s1")

    urls = [call[0] for call in http.calls]
    assert urls[1:] == ["http://jf/Sessions/s1/Playing/Stop", "http://jf/Sessions/s1/Command/GoHome"]
