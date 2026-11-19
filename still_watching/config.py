import os
from dataclasses import dataclass


SECONDS_PER_MINUTE = 60

DEFAULT_RUN_LENGTH = 4
DEFAULT_RUN_GAP_MINUTES = 10.0
DEFAULT_START_DELAY_SECONDS = 60.0
DEFAULT_MESSAGE = "Are you still watching?"

STOP_ACTION_PAUSE = "PAUSE"
STOP_ACTION_STOP = "STOP"
STOP_ACTIONS = (STOP_ACTION_PAUSE, STOP_ACTION_STOP)
DEFAULT_STOP_ACTION = STOP_ACTION_PAUSE

ENV_API_URL = "JELLYFIN_API_URL"
ENV_API_TOKEN = "JELLYFIN_API_TOKEN"
ENV_RUN_LENGTH = "STILL_WATCHING_RUN_LENGTH"
ENV_RUN_GAP_MINUTES = "STILL_WATCHING_RUN_GAP_MINUTES"
ENV_START_DELAY_SECONDS = "STILL_WATCHING_START_DELAY_SECONDS"
ENV_MESSAGE = "JELLYFIN_MESSAGE"
ENV_STOP_ACTION = "JELLYFIN_STOP_ACTION"


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    api_url: str
    api_token: str
    run_length: int = DEFAULT_RUN_LENGTH
    run_gap_seconds: float = DEFAULT_RUN_GAP_MINUTES * SECONDS_PER_MINUTE
    start_delay_seconds: float = DEFAULT_START_DELAY_SECONDS
    message: str = DEFAULT_MESSAGE
    stop_action: str = DEFAULT_STOP_ACTION


def _required(env, name):
    value = env.get(name, "").strip()

    if not value:
        raise ConfigError(f"{name} is required")

    return value


def _number(env, name, default, cast):
    raw = env.get(name, "").strip()

    if not raw:
        return default

    try:
        value = cast(raw)
    except ValueError as error:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from error

    if value < 0:
        raise ConfigError(f"{name} must not be negative, got {raw!r}")

    return value


def load_settings(env=None):
    env = os.environ if env is None else env

    run_length = _number(env, ENV_RUN_LENGTH, DEFAULT_RUN_LENGTH, int)
    if run_length < 1:
        raise ConfigError(f"{ENV_RUN_LENGTH} must be at least 1, got {run_length}")

    stop_action = env.get(ENV_STOP_ACTION, "").strip().upper() or DEFAULT_STOP_ACTION
    if stop_action not in STOP_ACTIONS:
        raise ConfigError(f"{ENV_STOP_ACTION} must be one of {', '.join(STOP_ACTIONS)}, got {stop_action!r}")

    run_gap_minutes = _number(env, ENV_RUN_GAP_MINUTES, DEFAULT_RUN_GAP_MINUTES, float)

    return Settings(
        api_url=_required(env, ENV_API_URL).rstrip("/"),
        api_token=_required(env, ENV_API_TOKEN),
        run_length=run_length,
        run_gap_seconds=run_gap_minutes * SECONDS_PER_MINUTE,
        start_delay_seconds=_number(env, ENV_START_DELAY_SECONDS, DEFAULT_START_DELAY_SECONDS, float),
        message=env.get(ENV_MESSAGE, "").strip() or DEFAULT_MESSAGE,
        stop_action=stop_action,
    )
