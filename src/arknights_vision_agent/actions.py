"""Strict, offline validation for proposed actions."""

from arknights_vision_agent.identifiers import is_valid_identifier as _is_valid_id
from arknights_vision_agent.strict_json import StrictJSONError, load_json_object

_OBSERVATION_KEYS = {
    "run_id",
    "observation_id",
    "screen",
    "available_options",
    "captured_at_ms",
    "source",
}
_SCREENS = {"recruitment", "route", "event", "unknown", "terminal"}
_SOURCES = {"synthetic", "recorded", "live"}
_ACTION_KEYS = {
    "select": {"run_id", "observation_id", "kind", "option_id"},
    "wait": {"run_id", "observation_id", "kind", "wait_ms"},
    "stop": {"run_id", "observation_id", "kind"},
}
_SELECT_SCREENS = {"recruitment", "route", "event"}


class ActionValidationError(ValueError):
    """Raised when an action proposal or observation is unsafe to use."""


def parse_action(payload: str) -> dict:
    """Parse an action proposal from JSON text."""
    try:
        return load_json_object(payload, max_bytes=16384)
    except StrictJSONError as error:
        raise ActionValidationError(str(error)) from error


def _validate_observation(observation: dict) -> None:
    if set(observation) != _OBSERVATION_KEYS:
        raise ActionValidationError("observation fields do not match the schema")
    if not _is_valid_id(observation["run_id"]):
        raise ActionValidationError("observation run_id is invalid")
    if not _is_valid_id(observation["observation_id"]):
        raise ActionValidationError("observation_id is invalid")
    if type(observation["screen"]) is not str or observation["screen"] not in _SCREENS:
        raise ActionValidationError("observation screen is invalid")
    if type(observation["source"]) is not str or observation["source"] not in _SOURCES:
        raise ActionValidationError("observation source is invalid")
    options = observation["available_options"]
    if type(options) is not list:
        raise ActionValidationError("available_options must be a list")
    if any(not _is_valid_id(option) for option in options):
        raise ActionValidationError("available_options contains an invalid option")
    if len(set(options)) != len(options):
        raise ActionValidationError("available_options contains a duplicate")
    captured_at_ms = observation["captured_at_ms"]
    if type(captured_at_ms) is not int or captured_at_ms < 0:
        raise ActionValidationError("captured_at_ms is invalid")


def _validate_action_schema(action: dict) -> None:
    kind = action.get("kind")
    if type(kind) is not str or kind not in _ACTION_KEYS:
        raise ActionValidationError("action kind is invalid")
    if set(action) != _ACTION_KEYS[kind]:
        raise ActionValidationError("action fields do not match its kind")
    if not _is_valid_id(action["run_id"]):
        raise ActionValidationError("action run_id is invalid")
    if not _is_valid_id(action["observation_id"]):
        raise ActionValidationError("action observation_id is invalid")
    if kind == "select" and not _is_valid_id(action["option_id"]):
        raise ActionValidationError("action option_id is invalid")
    if kind == "wait":
        wait_ms = action["wait_ms"]
        if type(wait_ms) is not int or not 1 <= wait_ms <= 10000:
            raise ActionValidationError("action wait_ms is invalid")


def _validate_action_context(
    action: dict,
    observation: dict,
    now_ms: int,
    max_age_ms: int,
) -> None:
    if action["run_id"] != observation["run_id"]:
        raise ActionValidationError("action run_id does not match observation")
    if action["observation_id"] != observation["observation_id"]:
        raise ActionValidationError("action observation_id does not match observation")

    kind = action["kind"]
    screen = observation["screen"]
    if screen == "terminal" and kind != "stop":
        raise ActionValidationError("terminal observations permit only stop")
    if kind == "select":
        if screen not in _SELECT_SCREENS:
            raise ActionValidationError("select is not allowed on this screen")
        if action["option_id"] not in observation["available_options"]:
            raise ActionValidationError("selected option is not available")

    if kind != "stop":
        captured_at_ms = observation["captured_at_ms"]
        if captured_at_ms > now_ms:
            raise ActionValidationError("observation timestamp is in the future")
        if now_ms - captured_at_ms > max_age_ms:
            raise ActionValidationError("observation is stale")


def validate_action(
    action: dict,
    observation: dict,
    *,
    now_ms: int,
    max_age_ms: int = 5000,
) -> dict:
    """Return a validated copy of an action proposal."""
    if type(action) is not dict:
        raise ActionValidationError("action must be a dictionary")
    if type(observation) is not dict:
        raise ActionValidationError("observation must be a dictionary")
    if type(now_ms) is not int or now_ms < 0:
        raise ActionValidationError("now_ms is invalid")
    if type(max_age_ms) is not int or max_age_ms < 0:
        raise ActionValidationError("max_age_ms is invalid")
    _validate_observation(observation)
    _validate_action_schema(action)
    _validate_action_context(action, observation, now_ms, max_age_ms)
    return dict(action)
