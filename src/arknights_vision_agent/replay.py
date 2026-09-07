"""Deterministic, offline replay of proposed actions."""

from arknights_vision_agent.actions import (
    ActionValidationError,
    parse_action,
    validate_action,
)

_TRACE_KEYS = {"schema_version", "run_id", "source", "steps"}
_STEP_KEYS = {"observation", "action_json", "decision_at_ms"}
_REPLAY_SOURCES = {"synthetic", "recorded"}
_MAX_STEPS = 1000


class ReplayValidationError(ValueError):
    """Raised when a replay trace does not match its schema."""


def _matching_stop(observation: object) -> dict:
    if type(observation) is dict:
        run_id = observation.get("run_id")
        observation_id = observation.get("observation_id")
    else:
        run_id = "trace-validation"
        observation_id = "trace-validation"
    return {
        "run_id": run_id,
        "observation_id": observation_id,
        "kind": "stop",
    }


def _validate_trace_run_id(trace: dict) -> None:
    observation = {
        "run_id": trace["run_id"],
        "observation_id": "trace-validation",
        "screen": "unknown",
        "available_options": [],
        "captured_at_ms": 0,
        "source": trace["source"],
    }
    try:
        validate_action(
            _matching_stop(observation),
            observation,
            now_ms=0,
        )
    except ActionValidationError as error:
        raise ReplayValidationError(f"trace run_id is invalid: {error}") from error


def _validate_trace(trace: object) -> None:
    if type(trace) is not dict:
        raise ReplayValidationError("trace must be a plain dictionary")
    if set(trace) != _TRACE_KEYS:
        raise ReplayValidationError("trace fields do not match the schema")
    if type(trace["schema_version"]) is not int or trace["schema_version"] != 1:
        raise ReplayValidationError("trace schema_version must be the integer 1")
    if type(trace["source"]) is not str or trace["source"] not in _REPLAY_SOURCES:
        raise ReplayValidationError("trace source must be synthetic or recorded")

    steps = trace["steps"]
    if type(steps) is not list:
        raise ReplayValidationError("trace steps must be a plain list")
    if not steps:
        raise ReplayValidationError("trace steps must not be empty")
    if len(steps) > _MAX_STEPS:
        raise ReplayValidationError("trace steps must contain at most 1000 entries")

    _validate_trace_run_id(trace)

    seen_observation_ids = set()
    previous_capture_ms = None
    previous_decision_ms = None
    for step_index, step in enumerate(steps, start=1):
        if type(step) is not dict:
            raise ReplayValidationError(
                f"step {step_index} must be a plain dictionary"
            )
        if set(step) != _STEP_KEYS:
            raise ReplayValidationError(
                f"step {step_index} fields do not match the schema"
            )
        if type(step["action_json"]) is not str:
            raise ReplayValidationError(
                f"step {step_index} action_json must be plain text"
            )

        observation = step["observation"]
        decision_at_ms = step["decision_at_ms"]
        try:
            validate_action(
                _matching_stop(observation),
                observation,
                now_ms=decision_at_ms,
            )
        except ActionValidationError as error:
            raise ReplayValidationError(
                f"step {step_index} observation or decision_at_ms is invalid: {error}"
            ) from error

        if observation["run_id"] != trace["run_id"]:
            raise ReplayValidationError(
                f"step {step_index} observation run_id does not match trace"
            )
        if observation["source"] != trace["source"]:
            raise ReplayValidationError(
                f"step {step_index} observation source does not match trace"
            )

        observation_id = observation["observation_id"]
        if observation_id in seen_observation_ids:
            raise ReplayValidationError("observation_id is duplicated in trace")
        seen_observation_ids.add(observation_id)

        captured_at_ms = observation["captured_at_ms"]
        if previous_capture_ms is not None and captured_at_ms < previous_capture_ms:
            raise ReplayValidationError("captured_at_ms moves backward across steps")
        if previous_decision_ms is not None and decision_at_ms < previous_decision_ms:
            raise ReplayValidationError("decision_at_ms moves backward across steps")
        previous_capture_ms = captured_at_ms
        previous_decision_ms = decision_at_ms


def _blocked_parse_event(
    step_index: int,
    observation_id: str,
    error: ActionValidationError,
) -> dict:
    return {
        "step_index": step_index,
        "observation_id": observation_id,
        "parse_error": str(error),
        "status": "blocked",
        "executed": False,
    }


def _action_event(
    step_index: int,
    observation_id: str,
    proposed_action: dict,
    status: str,
    error: ActionValidationError | None = None,
) -> dict:
    event = {
        "step_index": step_index,
        "observation_id": observation_id,
        "proposed_action": proposed_action,
        "status": status,
        "executed": False,
    }
    if error is not None:
        event["error"] = str(error)
    return event


def replay_trace(trace: dict) -> dict:
    """Validate and replay a trace without executing any action."""
    _validate_trace(trace)

    events = []
    allowed_actions = 0
    blocked_actions = 0
    stopped = False

    for step_index, step in enumerate(trace["steps"], start=1):
        observation = step["observation"]
        try:
            proposed_action = parse_action(step["action_json"])
        except ActionValidationError as error:
            events.append(
                _blocked_parse_event(
                    step_index,
                    observation["observation_id"],
                    error,
                )
            )
            blocked_actions = 1
            break

        try:
            validated_action = validate_action(
                proposed_action,
                observation,
                now_ms=step["decision_at_ms"],
            )
        except ActionValidationError as error:
            events.append(
                _action_event(
                    step_index,
                    observation["observation_id"],
                    proposed_action,
                    "blocked",
                    error,
                )
            )
            blocked_actions = 1
            break

        if validated_action["kind"] == "stop":
            events.append(
                _action_event(
                    step_index,
                    observation["observation_id"],
                    validated_action,
                    "stopped",
                )
            )
            stopped = True
            break

        events.append(
            _action_event(
                step_index,
                observation["observation_id"],
                validated_action,
                "allowed_dry_run",
            )
        )
        allowed_actions += 1

    steps_available = len(trace["steps"])
    steps_processed = len(events)
    return {
        "schema_version": 1,
        "mode": "dry_run",
        "source": trace["source"],
        "run_id": trace["run_id"],
        "events": events,
        "summary": {
            "steps_available": steps_available,
            "steps_processed": steps_processed,
            "allowed_actions": allowed_actions,
            "blocked_actions": blocked_actions,
            "stopped": stopped,
            "trace_exhausted": steps_processed == steps_available,
            "game_clear_verified": False,
            "mode": "dry_run",
        },
    }
