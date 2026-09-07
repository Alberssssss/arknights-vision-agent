# Metadata Preparation Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce deterministic, honestly scoped eligibility and whole-group partition reports from validated demonstration metadata.

**Architecture:** One pure reporting module uses the reviewed manifest validator, stable SHA-256 assignments, and canonical declaration hashing. It exposes no media reader, training export, model call, device connection, or file-writing interface. CLI integration is a separate task after review.

**Tech Stack:** Python 3.11+ standard library, `unittest`, existing `src/` package.

---

## Task 1: Eligibility, stable group assignment, and summary

**Files:** Create `src/arknights_vision_agent/preparation.py` and `tests/test_preparation.py`. No other implementation files change. The coordinator supplies the full contract from `docs/superpowers/specs/2026-09-07-preparation-report-design.md` directly to the implementer.

### 1. Establish the fixture and failing public API test

- [ ] Add the following fixture and test before the production module exists:

```python
import copy
import itertools
import unittest

from arknights_vision_agent.preparation import (
    PreparationValidationError, build_preparation_report,
)


def make_manifest():
    return {"schema_version": 1, "max_action_age_ms": 5000, "records": [{
        "record_id": "record-1", "recording_id": "recording-demo",
        "leakage_group_id": "group-demo",
        "observation": {
            "run_id": "run-demo", "observation_id": "frame-1",
            "screen": "recruitment", "available_options": ["option-a"],
            "captured_at_ms": 1000, "source": "synthetic",
        },
        "action": {"run_id": "run-demo", "observation_id": "frame-1",
                   "kind": "select", "option_id": "option-a"},
        "decision_at_ms": 1100,
        "media": {"kind": "video", "path": "demo/source.mp4",
                  "start_ms": 0, "end_ms": 1000, "media_to_run_offset_ms": 0},
        "label": {"origin": "human", "status": "pending",
                  "evidence_id": "evidence-demo", "review_id": None},
        "usage_permitted": False,
    }]}


def add_independent_record(manifest, suffix, group):
    row = copy.deepcopy(manifest["records"][0])
    row["record_id"] = "record-" + suffix
    row["recording_id"] = "recording-" + suffix
    row["leakage_group_id"] = group
    row["observation"]["run_id"] = "run-" + suffix
    row["action"]["run_id"] = "run-" + suffix
    row["media"]["path"] = "demo/" + suffix + ".mp4"
    manifest["records"].append(row)
    return row


class PreparationTests(unittest.TestCase):
    def test_synthetic_report_does_not_claim_eligible_data(self):
        report = build_preparation_report(make_manifest())
        self.assertEqual(report["scope"], "metadata_only")
        self.assertEqual(report["records"], [{
            "record_id": "record-1", "leakage_group_id": "group-demo",
            "partition": "train", "metadata_eligible": False,
            "exclusion_reasons": ["synthetic_source", "label_pending",
                                  "usage_not_permitted"],
        }])
        self.assertEqual(report["summary"]["eligible_record_count"], 0)
        self.assertEqual(report["summary"]["empty_partitions"], ["validation", "test"])
        self.assertEqual(report["summary"]["eligible_empty_partitions"],
                         ["train", "validation", "test"])
        self.assertTrue(all(value is False for value in report["verification"].values()))
```

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -p test_preparation.py -v`. Expect missing-module failure. Add the minimal passing report path, then develop the general implementation under the following red/green cases. Keep the final implementation below as contract guidance, not permission to skip tests.

### 2. Add exact eligibility and configuration tests before enforcement

- [ ] Use the following exhaustive eligibility test:

```python
    def test_every_source_status_permission_origin_combination(self):
        for source, status, permission, origin in itertools.product(
            ("synthetic", "recorded"), ("pending", "accepted", "rejected"),
            (False, True), ("input_log", "human", "inferred"),
        ):
            with self.subTest(source=source, status=status,
                              permission=permission, origin=origin):
                manifest = make_manifest()
                row = manifest["records"][0]
                row["observation"]["source"] = source
                row["label"].update(origin=origin, status=status,
                                    review_id=None if status == "pending" else "review-1")
                row["usage_permitted"] = permission
                report = build_preparation_report(manifest)
                expected = []
                if source == "synthetic": expected.append("synthetic_source")
                if status == "pending": expected.append("label_pending")
                if status == "rejected": expected.append("label_rejected")
                if not permission: expected.append("usage_not_permitted")
                actual = report["records"][0]
                self.assertEqual(actual["exclusion_reasons"], expected)
                self.assertIs(actual["metadata_eligible"], not expected)
                self.assertEqual(row["label"]["origin"], origin)

    def test_invalid_configuration_uses_public_error(self):
        for seed in (True, False, -1, 2**63, 0.0, "0", None, [], {}):
            with self.subTest(seed=seed), self.assertRaises(PreparationValidationError):
                build_preparation_report(make_manifest(), seed=seed)
        for weights in (
            {}, [], {"train": 10000, "validation": 0},
            {"train": 8000, "validation": 1000, "test": 1000, "extra": 0},
            {"train": 8000, "validation": 1000, "test": 999},
            {"train": -1, "validation": 1, "test": 10000},
            {"train": 10001, "validation": 0, "test": 0},
            {"train": 9999, "validation": True, "test": 0},
            {"train": 8000.0, "validation": 1000, "test": 1000},
        ):
            with self.subTest(weights=weights), self.assertRaises(PreparationValidationError):
                build_preparation_report(make_manifest(), weights=weights)
```

- [ ] Extend exact-type tests with local `int` and `dict` subclasses; test both valid seed endpoints and all-train/all-validation/all-test weights. Verify malformed manifests, including invalid actions in rejected/permission-denied rows, are wrapped as the public error. Do not sanitize or filter them first.

### 3. Add stable assignment and counts tests before implementing aggregation

- [ ] Golden assignment test, using the literal strings and values in the spec:

```python
    def test_actual_hash_golden_assignments(self):
        for seed, group, expected in (
            (0, "group-demo", "train"), (0, "group-5", "validation"),
            (0, "group-4", "test"), (7, "group-demo", "train"),
            (2**63 - 1, "组🦊", "train"),
        ):
            with self.subTest(seed=seed, group=group):
                manifest = make_manifest()
                manifest["records"][0]["leakage_group_id"] = group
                self.assertEqual(build_preparation_report(manifest, seed=seed)
                                 ["groups"][0]["partition"], expected)

    def test_actual_hash_half_open_boundaries(self):
        for train, validation, test, expected in (
            (7382, 1, 2617, "validation"), (7382, 0, 2618, "test"),
            (7383, 0, 2617, "train"),
        ):
            report = build_preparation_report(make_manifest(), weights={
                "train": train, "validation": validation, "test": test,
            })
            self.assertEqual(report["groups"][0]["partition"], expected)
```

- [ ] Strengthen all golden vectors with their bucket-specific one-unit validation weights from the spec, so the test pins the bucket rather than just a broad partition. Verify a seed change across a custom threshold changes assignment using the known 7382/5545 buckets.
- [ ] With `add_independent_record`, create records in all three golden groups; make only the validation record recorded/accepted/permitted. Assert exact root keys, nested keys, group/record counts, all four exclusion counts, fixed partition ordering, eligible-empty train/test but no assigned-empty partition. Then give the same group a second row with different eligibility and assert eligible-group count remains one, not eligible-row count. Put multiple runs and recordings in that group and assert no split divergence.
- [ ] Reverse input records and dictionary insertion order: reports must be equal. Add an unrelated group: existing record/group assignments must remain equal while counts/digest change. Alter a valid label or permission: assignment remains equal while eligibility/digest changes.
- [ ] Launch fresh Python subprocesses with `PYTHONHASHSEED=1` and `2`, importing this public function and receiving the same fixture on stdin; compare JSON reports. This uses no model/network/device and verifies that Python hash randomization cannot affect results.

### 4. Add digest, isolation, and honest-evidence tests

- [ ] Independently construct canonical JSON from the fixture sorted by record ID and dictionary keys with the exact prefix/settings in the spec. Assert the reported algorithm and lowercase SHA-256 equal that reference. Verify key/record ordering invariance, option-list ordering sensitivity, metadata sensitivity, and seed/weights independence of the declaration digest.
- [ ] Make a deep copy before accepted and rejected calls and assert no mutation. Mutate nested report weights, reasons, groups, partition counts, and verification: the original arguments and a new report must be unchanged. Ensure defaults cannot be corrupted by a previous returned report.
- [ ] Assert exact false verification fields. Reports must omit media paths, observations, actions, and evidence/reviewer IDs, and never claim media inspection, training readiness, training, or game completion. Existing-media absence is normal for all fixture tests.

### 5. Complete production implementation under these tests

The following is the complete bounded implementation. Equivalent focused helpers are allowed. Do not introduce filesystem, network, random, model, controller, or training imports.

```python
"""Pure eligibility and group-partition reports over declared metadata."""

import hashlib
import json

from arknights_vision_agent.demonstrations import ManifestValidationError, validate_manifest

_PARTITIONS = ("train", "validation", "test")
_REASONS = ("synthetic_source", "label_pending", "label_rejected", "usage_not_permitted")
_SPLIT_ALGORITHM = "sha256-json-mod10000-v1"
_DIGEST_ALGORITHM = "sha256-canonical-manifest-v1"


class PreparationValidationError(ValueError):
    """Invalid preparation configuration or demonstration declarations."""


def _configuration(seed, weights):
    if type(seed) is not int or not 0 <= seed <= 2**63 - 1:
        raise PreparationValidationError("seed must be an integer in 0..2**63-1")
    if weights is None:
        weights = {"train": 8000, "validation": 1000, "test": 1000}
    if type(weights) is not dict or set(weights) != set(_PARTITIONS):
        raise PreparationValidationError("weights must declare train, validation, and test")
    if (any(type(value) is not int or not 0 <= value <= 10000 for value in weights.values())
            or sum(weights.values()) != 10000):
        raise PreparationValidationError("integer weights must be in 0..10000 and sum to 10000")
    return {partition: weights[partition] for partition in _PARTITIONS}


def _canonical_bytes(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _partition(group, seed, weights):
    digest = hashlib.sha256(b"arknights-vision-agent/split/v1\n"
                            + _canonical_bytes([seed, group])).digest()
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


def build_preparation_report(manifest: dict, *, seed: int = 0, weights: dict | None = None) -> dict:
    """Validate declarations and report metadata eligibility, without inspecting media."""
    weights = _configuration(seed, weights)
    try:
        validated = validate_manifest(manifest)
    except ManifestValidationError as error:
        raise PreparationValidationError(f"invalid demonstration manifest: {error}") from error
    validated["records"].sort(key=lambda row: row["record_id"])
    digest = hashlib.sha256(b"arknights-vision-agent/manifest/v1\n"
                            + _canonical_bytes(validated)).hexdigest()
    records, groups = [], {}
    reason_counts = {reason: 0 for reason in _REASONS}
    counts = {partition: {"record_count": 0, "eligible_record_count": 0,
                          "group_count": 0, "eligible_group_count": 0}
              for partition in _PARTITIONS}
    for row in validated["records"]:
        group_id = row["leakage_group_id"]
        if group_id not in groups:
            groups[group_id] = {"leakage_group_id": group_id,
                                "partition": _partition(group_id, seed, weights),
                                "record_count": 0, "eligible_record_count": 0}
        group = groups[group_id]
        reasons = _exclusions(row)
        eligible = not reasons
        records.append({"record_id": row["record_id"], "leakage_group_id": group_id,
                        "partition": group["partition"], "metadata_eligible": eligible,
                        "exclusion_reasons": reasons})
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
    eligible_count = sum(count["eligible_record_count"] for count in counts.values())
    return {
        "schema_version": 1, "scope": "metadata_only",
        "manifest_digest": {"algorithm": _DIGEST_ALGORITHM, "sha256": digest},
        "split": {"algorithm": _SPLIT_ALGORITHM, "seed": seed, "weights": weights},
        "records": records, "groups": group_rows,
        "summary": {
            "record_count": len(records), "eligible_record_count": eligible_count,
            "excluded_record_count": len(records) - eligible_count,
            "group_count": len(group_rows),
            "eligible_group_count": sum(c["eligible_group_count"] for c in counts.values()),
            "exclusion_reason_counts": reason_counts, "partitions": counts,
            "empty_partitions": [p for p in _PARTITIONS if counts[p]["record_count"] == 0],
            "eligible_empty_partitions": [p for p in _PARTITIONS
                                          if counts[p]["eligible_record_count"] == 0],
        },
        "verification": {
            "media_inspected": False, "label_evidence_verified": False,
            "permission_verified": False, "training_started": False,
            "game_clear_verified": False,
        },
    }
```

### 6. Verify and review

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `python3 -m compileall -q src tests`, and `git diff --check`, inspecting full results.
- [ ] Self-review all contract rules and the actual diff. Commit only the two task files as `feat: report metadata eligibility and stable group splits`. Do not push or edit status.
- [ ] Coordinator runs fresh verification and obtains specification review, then independent quality review. Return findings to the implementer for regression-tested fixes; re-review before publication.

## Follow-on boundary

After this report function is reviewed, add a separate non-overwriting preparation CLI and clearly synthetic example. Real media inspection, timestamp alignment, label review, model-specific export, hardware preflight, and device integration remain separate work. This report never launches training.
