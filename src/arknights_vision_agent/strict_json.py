"""Bounded strict-JSON object parsing for untrusted offline inputs."""

import json
import math

_MAX_JSON_NESTING = 100


class StrictJSONError(ValueError):
    """Raised when text is not an accepted bounded JSON object."""


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError("JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_nonfinite_number(_: str) -> None:
    raise StrictJSONError("JSON contains a non-finite number")


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise StrictJSONError("JSON number exceeds the finite range")
    return parsed


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


def load_json_object(payload: str, *, max_bytes: int) -> dict:
    """Parse a plain-text JSON object under an exact UTF-8 byte limit."""
    if type(max_bytes) is not int or max_bytes <= 0:
        raise StrictJSONError("max_bytes must be a positive integer")
    if type(payload) is not str:
        raise StrictJSONError("JSON payload must be plain text")
    try:
        payload_size = len(payload.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise StrictJSONError("JSON payload is not valid Unicode") from error
    if payload_size > max_bytes:
        raise StrictJSONError("JSON payload exceeds the size limit")
    try:
        parsed = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_number,
            parse_float=_parse_finite_float,
        )
    except StrictJSONError:
        raise
    except (ValueError, RecursionError, TypeError, UnicodeError) as error:
        raise StrictJSONError("JSON payload is not valid JSON") from error
    if type(parsed) is not dict:
        raise StrictJSONError("JSON payload must contain a JSON object")
    if _is_nested_too_deep(parsed):
        raise StrictJSONError("JSON payload is nested too deeply")
    if _contains_invalid_unicode(parsed):
        raise StrictJSONError("JSON payload contains invalid Unicode")
    return parsed
