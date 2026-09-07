"""Strict, offline validation for proposed actions."""

import json

_MAX_JSON_NESTING = 100
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


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ActionValidationError("JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_nonfinite_number(_: str) -> None:
    raise ActionValidationError("JSON contains a non-finite number")


def _is_nested_too_deep(value: object) -> bool:
    pending = [(value, 1)]
    while pending:
        current, depth = pending.pop()
        if depth > _MAX_JSON_NESTING:
            return True
        if type(current) is dict:
            pending.extend((item, depth + 1) for item in current.values())
        elif type(current) is list:
            pending.extend((item, depth + 1) for item in current)
    return False


def _contains_invalid_unicode(value: object) -> bool:
    pending = [value]
    while pending:
        current = pending.pop()
        if type(current) is str:
            try:
                current.encode("utf-8")
            except UnicodeEncodeError:
                return True
        elif type(current) is dict:
            pending.extend(current.keys())
            pending.extend(current.values())
        elif type(current) is list:
            pending.extend(current)
    return False


def parse_action(payload: str) -> dict:
    """Parse an action proposal from JSON text."""
    if type(payload) is not str:
        raise ActionValidationError("action payload must be text")
    try:
        payload_size = len(payload.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise ActionValidationError("action payload is not valid Unicode") from error
    if payload_size > 16384:
        raise ActionValidationError("action payload exceeds the size limit")
    try:
        parsed = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_number,
        )
    except ActionValidationError:
        raise
    except (ValueError, RecursionError, TypeError, UnicodeError) as error:
        raise ActionValidationError("action payload is not valid JSON") from error
    if type(parsed) is not dict:
        raise ActionValidationError("action payload must contain a JSON object")
    if _is_nested_too_deep(parsed):
        raise ActionValidationError("action payload is nested too deeply")
    if _contains_invalid_unicode(parsed):
        raise ActionValidationError("action payload contains invalid Unicode")
    return parsed


def _is_valid_id(value: object) -> bool:
    if type(value) is not str or not value.strip() or len(value) > 128:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


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
