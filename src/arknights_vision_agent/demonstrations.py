"""Strict validation for offline demonstration metadata."""

import copy

from arknights_vision_agent.actions import ActionValidationError, validate_action
from arknights_vision_agent.identifiers import is_valid_identifier
from arknights_vision_agent.media_paths import is_valid_media_path

_MAX_MS = 2**63 - 1
_MIN_OFFSET = -(2**63)
_MANIFEST_FIELDS = {"schema_version", "max_action_age_ms", "records"}
_RECORD_FIELDS = {
    "record_id",
    "recording_id",
    "leakage_group_id",
    "observation",
    "action",
    "decision_at_ms",
    "media",
    "label",
    "usage_permitted",
}
_MEDIA_FIELDS = {"kind", "path", "start_ms", "end_ms", "media_to_run_offset_ms"}
_LABEL_FIELDS = {"origin", "status", "evidence_id", "review_id"}


class ManifestValidationError(ValueError):
    """A demonstration manifest has inconsistent or malformed declarations."""


def _require_fields(value, fields, where):
    if type(value) is not dict or set(value) != fields:
        raise ManifestValidationError(f"{where} fields do not match the schema")


def _require_id(value, where):
    if not is_valid_identifier(value):
        raise ManifestValidationError(f"{where} is invalid")


def _require_ms(value, where, *, signed=False):
    minimum = _MIN_OFFSET if signed else 0
    if type(value) is not int or not minimum <= value <= _MAX_MS:
        raise ManifestValidationError(f"{where} is outside the timestamp range")


def _require_enum(value, allowed, where):
    if type(value) is not str or value not in allowed:
        raise ManifestValidationError(f"{where} is invalid")


def _require_media_path(value, where):
    if not is_valid_media_path(value):
        raise ManifestValidationError(
            f"{where} is not a literal relative media reference"
        )


def _validate_media(media, observation, where):
    _require_fields(media, _MEDIA_FIELDS, f"{where} media")
    _require_enum(media["kind"], {"image", "video"}, f"{where} media kind")
    _require_media_path(media["path"], f"{where} media path")
    _require_ms(media["start_ms"], f"{where} media start_ms")
    _require_ms(media["end_ms"], f"{where} media end_ms")
    _require_ms(
        media["media_to_run_offset_ms"],
        f"{where} media offset",
        signed=True,
    )
    if media["start_ms"] > media["end_ms"]:
        raise ManifestValidationError(f"{where} media window is reversed")
    if media["kind"] == "image" and media["start_ms"] != media["end_ms"]:
        raise ManifestValidationError(f"{where} image must have a point timestamp")

    mapped_start = media["start_ms"] + media["media_to_run_offset_ms"]
    mapped_end = media["end_ms"] + media["media_to_run_offset_ms"]
    if mapped_start < 0 or mapped_end != observation["captured_at_ms"]:
        raise ManifestValidationError(f"{where} media clock mapping is invalid")


def _validate_label(label, where):
    _require_fields(label, _LABEL_FIELDS, f"{where} label")
    _require_enum(
        label["origin"],
        {"input_log", "human", "inferred"},
        f"{where} label origin",
    )
    _require_enum(
        label["status"],
        {"pending", "accepted", "rejected"},
        f"{where} label status",
    )
    _require_id(label["evidence_id"], f"{where} evidence_id")
    if label["status"] == "pending":
        if label["review_id"] is not None:
            raise ManifestValidationError(
                f"{where} pending label must not have review_id"
            )
    else:
        _require_id(label["review_id"], f"{where} review_id")


def _remember(mapping, key, value, where):
    if key in mapping and mapping[key] != value:
        raise ManifestValidationError(f"{where} conflicts with another record")
    mapping[key] = value


def validate_manifest(manifest: dict) -> dict:
    """Validate declarations and return a detached manifest copy."""
    _require_fields(manifest, _MANIFEST_FIELDS, "manifest")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ManifestValidationError("manifest schema_version must be integer 1")
    _require_ms(manifest["max_action_age_ms"], "manifest max_action_age_ms")
    records = manifest["records"]
    if type(records) is not list or not 1 <= len(records) <= 10000:
        raise ManifestValidationError(
            "manifest records must be a plain list of 1..10000 entries"
        )

    record_ids = set()
    observation_ids = set()
    runs = {}
    recordings = {}
    paths = {}
    alignments = {}
    for index, record in enumerate(records, start=1):
        where = f"record {index}"
        _require_fields(record, _RECORD_FIELDS, where)
        for field in ("record_id", "recording_id", "leakage_group_id"):
            _require_id(record[field], f"{where} {field}")
        _require_ms(record["decision_at_ms"], f"{where} decision_at_ms")
        if type(record["usage_permitted"]) is not bool:
            raise ManifestValidationError(
                f"{where} usage_permitted must be Boolean"
            )

        observation = record["observation"]
        try:
            validate_action(
                record["action"],
                observation,
                now_ms=record["decision_at_ms"],
                max_age_ms=manifest["max_action_age_ms"],
            )
        except ActionValidationError as error:
            raise ManifestValidationError(
                f"{where} action/observation: {error}"
            ) from error
        _require_enum(
            observation["source"],
            {"synthetic", "recorded"},
            f"{where} source",
        )
        _require_ms(observation["captured_at_ms"], f"{where} captured_at_ms")
        if observation["captured_at_ms"] > record["decision_at_ms"]:
            raise ManifestValidationError(f"{where} observation is after action onset")

        _validate_media(record["media"], observation, where)
        _validate_label(record["label"], where)

        media = record["media"]
        run_id = observation["run_id"]
        recording_id = record["recording_id"]
        group = record["leakage_group_id"]
        source = observation["source"]
        observation_key = (run_id, observation["observation_id"])
        if record["record_id"] in record_ids:
            raise ManifestValidationError(f"{where} record_id is duplicated")
        if observation_key in observation_ids:
            raise ManifestValidationError(
                f"{where} run/observation pair is duplicated"
            )
        record_ids.add(record["record_id"])
        observation_ids.add(observation_key)
        _remember(runs, run_id, (group, source), f"{where} run provenance")
        _remember(
            recordings,
            recording_id,
            (group, source, media["path"], media["kind"]),
            f"{where} recording provenance",
        )
        _remember(
            paths,
            media["path"],
            recording_id,
            f"{where} media path identity",
        )
        _remember(
            alignments,
            (run_id, recording_id),
            media["media_to_run_offset_ms"],
            f"{where} clock alignment",
        )

    return copy.deepcopy(manifest)
