"""Pure eligibility and group-partition reports over declared metadata."""

import hashlib
import json

from arknights_vision_agent.demonstrations import (
    ManifestValidationError,
    validate_manifest,
)

_PARTITIONS = ("train", "validation", "test")
_REASONS = (
    "synthetic_source",
    "label_pending",
    "label_rejected",
    "usage_not_permitted",
)
_SPLIT_ALGORITHM = "sha256-json-mod10000-v1"
_DIGEST_ALGORITHM = "sha256-canonical-manifest-v1"


class PreparationValidationError(ValueError):
    """Invalid preparation configuration or demonstration declarations."""


def _configuration(seed, weights):
    if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
        raise PreparationValidationError(
            "seed must be an integer in 0..2**63-1"
        )
    if weights is None:
        weights = {"train": 8000, "validation": 1000, "test": 1000}
    if type(weights) is not dict or set(weights) != set(_PARTITIONS):
        raise PreparationValidationError(
            "weights must declare train, validation, and test"
        )
    if (
        any(
            type(value) is not int or not 0 <= value <= 10000
            for value in weights.values()
        )
        or sum(weights.values()) != 10000
    ):
        raise PreparationValidationError(
            "integer weights must be in 0..10000 and sum to 10000"
        )
    return {partition: weights[partition] for partition in _PARTITIONS}


def _canonical_bytes(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _partition(group, seed, weights):
    digest = hashlib.sha256(
        b"arknights-vision-agent/split/v1\n"
        + _canonical_bytes([seed, group])
    ).digest()
    bucket = int.from_bytes(digest, "big") % 10000
    if bucket < weights["train"]:
        return "train"
    if bucket < weights["train"] + weights["validation"]:
        return "validation"
    return "test"


def _exclusions(row):
    reasons = []
    if row["observation"]["source"] == "synthetic":
        reasons.append("synthetic_source")
    if row["label"]["status"] == "pending":
        reasons.append("label_pending")
    if row["label"]["status"] == "rejected":
        reasons.append("label_rejected")
    if not row["usage_permitted"]:
        reasons.append("usage_not_permitted")
    return reasons


def build_preparation_report(
    manifest: dict, *, seed: int = 0, weights: dict | None = None
) -> dict:
    """Validate declarations and report metadata eligibility, without inspecting media."""
    weights = _configuration(seed, weights)
    try:
        validated = validate_manifest(manifest)
    except ManifestValidationError as error:
        raise PreparationValidationError(
            f"invalid demonstration manifest: {error}"
        ) from error

    validated["records"].sort(key=lambda row: row["record_id"])
    digest = hashlib.sha256(
        b"arknights-vision-agent/manifest/v1\n" + _canonical_bytes(validated)
    ).hexdigest()
    records = []
    groups = {}
    reason_counts = {reason: 0 for reason in _REASONS}
    counts = {
        partition: {
            "record_count": 0,
            "eligible_record_count": 0,
            "group_count": 0,
            "eligible_group_count": 0,
        }
        for partition in _PARTITIONS
    }
    for row in validated["records"]:
        group_id = row["leakage_group_id"]
        if group_id not in groups:
            groups[group_id] = {
                "leakage_group_id": group_id,
                "partition": _partition(group_id, seed, weights),
                "record_count": 0,
                "eligible_record_count": 0,
            }
        group = groups[group_id]
        reasons = _exclusions(row)
        eligible = not reasons
        records.append(
            {
                "record_id": row["record_id"],
                "leakage_group_id": group_id,
                "partition": group["partition"],
                "metadata_eligible": eligible,
                "exclusion_reasons": reasons,
            }
        )
        group["record_count"] += 1
        group["eligible_record_count"] += int(eligible)
        for reason in reasons:
            reason_counts[reason] += 1

    group_rows = [groups[group_id] for group_id in sorted(groups)]
    for group in group_rows:
        count = counts[group["partition"]]
        count["record_count"] += group["record_count"]
        count["eligible_record_count"] += group["eligible_record_count"]
        count["group_count"] += 1
        count["eligible_group_count"] += int(group["eligible_record_count"] > 0)
    eligible_count = sum(
        count["eligible_record_count"] for count in counts.values()
    )

    return {
        "schema_version": 1,
        "scope": "metadata_only",
        "manifest_digest": {
            "algorithm": _DIGEST_ALGORITHM,
            "sha256": digest,
        },
        "split": {
            "algorithm": _SPLIT_ALGORITHM,
            "seed": seed,
            "weights": weights,
        },
        "records": records,
        "groups": group_rows,
        "summary": {
            "record_count": len(records),
            "eligible_record_count": eligible_count,
            "excluded_record_count": len(records) - eligible_count,
            "group_count": len(group_rows),
            "eligible_group_count": sum(
                count["eligible_group_count"] for count in counts.values()
            ),
            "exclusion_reason_counts": reason_counts,
            "partitions": counts,
            "empty_partitions": [
                partition
                for partition in _PARTITIONS
                if counts[partition]["record_count"] == 0
            ],
            "eligible_empty_partitions": [
                partition
                for partition in _PARTITIONS
                if counts[partition]["eligible_record_count"] == 0
            ],
        },
        "verification": {
            "media_inspected": False,
            "label_evidence_verified": False,
            "permission_verified": False,
            "training_started": False,
            "game_clear_verified": False,
        },
    }
