# Demonstration Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate declared demonstration metadata and its cross-record relationships without opening media or training a model.

**Architecture:** A pure manifest module reuses the reviewed action guard and a shared identifier predicate. It enforces portable timestamps, causal source windows, review declarations, and whole-manifest consistency, then returns a detached copy. Partitioning/reporting and command-line integration follow in separate plans.

**Tech Stack:** Python 3.11+ standard library, `unittest`, existing `src/` package.

---

## Task 1: Strict manifest boundary

**Files:** Create `src/arknights_vision_agent/identifiers.py`, `src/arknights_vision_agent/demonstrations.py`, and `tests/test_demonstrations.py`. Modify `actions.py` only to reuse the shared identifier predicate. The full required schema is fixed in `docs/superpowers/specs/2026-09-07-demonstration-manifest-design.md`; the coordinator must provide that contract directly to the implementer.

### 1. Establish a real failing test

- [ ] Add this complete fixture and happy-path test before implementing the module:

```python
import copy
import unittest

from arknights_vision_agent.demonstrations import validate_manifest


def make_manifest():
    return {
        "schema_version": 1, "max_action_age_ms": 5000,
        "records": [{
            "record_id": "record-1", "recording_id": "recording-demo",
            "leakage_group_id": "group-demo",
            "observation": {
                "run_id": "run-demo", "observation_id": "frame-1",
                "screen": "recruitment", "available_options": ["option-a"],
                "captured_at_ms": 1000, "source": "synthetic",
            },
            "action": {
                "run_id": "run-demo", "observation_id": "frame-1",
                "kind": "select", "option_id": "option-a",
            },
            "decision_at_ms": 1100,
            "media": {
                "kind": "video", "path": "demo/source.mp4",
                "start_ms": 0, "end_ms": 1000, "media_to_run_offset_ms": 0,
            },
            "label": {
                "origin": "human", "status": "pending",
                "evidence_id": "evidence-demo", "review_id": None,
            },
            "usage_permitted": False,
        }],
    }


class ManifestTests(unittest.TestCase):
    def test_returns_detached_validated_copy_without_media(self):
        original = make_manifest()
        before = copy.deepcopy(original)
        result = validate_manifest(original)
        self.assertEqual(result, original)
        self.assertIsNot(result, original)
        result["records"][0]["observation"]["available_options"].append("changed")
        result["records"][0]["media"]["path"] = "changed.mp4"
        self.assertEqual(original, before)
```

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -p test_demonstrations.py -v` and retain the initial missing-module failure.

### 2. Extract the identifier rule without changing it

- [ ] Put this complete predicate in `identifiers.py` and replace the existing private function in `actions.py` with an import alias. All existing callers remain unchanged:

```python
"""Shared opaque-identifier validation."""


def is_valid_identifier(value: object) -> bool:
    if type(value) is not str or not value.strip() or len(value) > 128:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True
```

```python
from arknights_vision_agent.identifiers import is_valid_identifier as _is_valid_id
```

- [ ] Run the existing action tests before and after extraction; Unicode, exact types, and public error behavior must remain unchanged.

### 3. Implement schema checks in red/green increments

- [ ] Add `ManifestValidationError(ValueError)` and the minimal valid-copy path; observe the first test pass. The eventual return is `copy.deepcopy(manifest)` only after all checks pass.
- [ ] Before each corresponding implementation, add failing tests for these exact schema boundaries: all missing/unknown fields at each object level; non-plain dictionaries/lists/strings; version other than exact integer 1; empty and more-than-10,000 records; ID whitespace/overlength/surrogates/non-string types; every invalid enum; Boolean/non-integer/out-of-range clocks; permission other than exact bool; and review-ID/status mismatch.
- [ ] Apply shared action validation, wrapping its failure with the one-based record index. Do not duplicate its screen, options, action, or freshness logic. Add unavailable option, mismatched run/observation, future select, stale select, exact age boundary, invalid observation, and live-source rejection cases before adding their enforcement.
- [ ] Add media boundary tests before implementing them: valid Unicode relative path; exactly 1024 characters; 1025 characters; absolute/home/URL/Windows/backslash/colon paths; empty/dot/dotdot segments; control characters; invalid Unicode; wrong path types. Literal `$` and `%` remain literal. Add image-point windows, reversed windows, negative mapped start, unequal mapped end/capture, nonzero positive/negative offsets, and future capture even on stop. The module must not import filesystem/controller/model/network functionality.

Useful complete primitive implementations, to use under those tests:

```python
import unicodedata

_MAX_MS = 2**63 - 1
_MIN_OFFSET = -(2**63)


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


def _require_media_path(value, where):
    if type(value) is not str or not 1 <= len(value) <= 1024:
        raise ManifestValidationError(f"{where} is invalid")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ManifestValidationError(f"{where} is invalid Unicode") from error
    if (value.startswith(("/", "~")) or "\\" in value or ":" in value
            or any(unicodedata.category(char) == "Cc" for char in value)
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ManifestValidationError(f"{where} is not a literal relative media reference")
```

The validation logic must enforce every exact field/enum and rule in the provided schema. The primitive helpers do not replace the action guard. The timing additions are specifically:

```python
mapped_start = media["start_ms"] + media["media_to_run_offset_ms"]
mapped_end = media["end_ms"] + media["media_to_run_offset_ms"]
if mapped_start < 0 or mapped_end != observation["captured_at_ms"]:
    raise ManifestValidationError(f"record {index} media clock mapping is invalid")
if observation["captured_at_ms"] > record["decision_at_ms"]:
    raise ManifestValidationError(f"record {index} observation is after action onset")
```

### 4. Enforce whole-manifest consistency

- [ ] Write failing paired-record tests for every consistency rule, including conflicts in pending/rejected/synthetic/permission-denied records. Mutate a deep copy of the first record, giving it distinct `record_id` and `observation_id` (update the action ID too) before introducing one conflict at a time.
- [ ] Track unique record IDs and `(run_id, observation_id)` pairs. Track run-to-`(group, source)`, recording-to-`(group, source, path, kind)`, path-to-recording, and run/recording-to-offset mappings. Reject conflicting mappings with an indexed error, never overwrite them silently. A reusable complete helper is:

```python
def _remember(mapping, key, value, where):
    if key in mapping and mapping[key] != value:
        raise ManifestValidationError(f"{where} conflicts with another record")
    mapping[key] = value
```

- [ ] Verify positive cases for multiple runs per recording, multiple recordings per run, repeated evidence/review IDs, mixed sources in distinct runs/assets, reversed row order, exact signed timestamp/offset limits where the mapping is valid, and a fully populated 10,000-record boundary. These are metadata tests only; the source files need not exist.
- [ ] Check non-mutation on both acceptance and rejection and that invalid values are not echoed in errors.

### 5. Verify, review, and commit

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `python3 -m compileall -q src tests`, and `git diff --check`.
- [ ] Inspect the actual diff for unrelated changes and forbidden side effects. Commit only the task files as `feat: validate demonstration metadata and provenance`.
- [ ] The coordinator obtains specification review then independent quality review, returning findings to the same implementer for tested fixes. Do not push or update status from the implementation agent.

## Follow-on work

After this boundary is reviewed, create a separate complete plan for metadata eligibility and deterministic group partition reports, then command-line integration. Neither a successful validation nor a partition report is authorization for training or evidence that a model can play the game.

## Complete validator control flow

The following completes the implementation using the primitive helpers above. The implementer may separate helpers for readability while preserving this contract and the test-first sequence. It is not permission to skip the negative tests.

```python
import copy

from arknights_vision_agent.actions import ActionValidationError, validate_action
from arknights_vision_agent.identifiers import is_valid_identifier


class ManifestValidationError(ValueError):
    """A demonstration manifest has inconsistent or malformed declarations."""


def _require_enum(value, allowed, where):
    if type(value) is not str or value not in allowed:
        raise ManifestValidationError(f"{where} is invalid")


def validate_manifest(manifest: dict) -> dict:
    _require_fields(manifest, {"schema_version", "max_action_age_ms", "records"}, "manifest")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ManifestValidationError("manifest schema_version must be integer 1")
    _require_ms(manifest["max_action_age_ms"], "manifest max_action_age_ms")
    records = manifest["records"]
    if type(records) is not list or not 1 <= len(records) <= 10000:
        raise ManifestValidationError("manifest records must be a plain list of 1..10000 entries")

    record_ids, observation_ids = set(), set()
    runs, recordings, paths, alignments = {}, {}, {}, {}
    for index, record in enumerate(records, start=1):
        where = f"record {index}"
        _require_fields(record, {
            "record_id", "recording_id", "leakage_group_id", "observation", "action",
            "decision_at_ms", "media", "label", "usage_permitted",
        }, where)
        for field in ("record_id", "recording_id", "leakage_group_id"):
            _require_id(record[field], f"{where} {field}")
        _require_ms(record["decision_at_ms"], f"{where} decision_at_ms")
        if type(record["usage_permitted"]) is not bool:
            raise ManifestValidationError(f"{where} usage_permitted must be Boolean")

        observation = record["observation"]
        try:
            validate_action(record["action"], observation,
                            now_ms=record["decision_at_ms"],
                            max_age_ms=manifest["max_action_age_ms"])
        except ActionValidationError as error:
            raise ManifestValidationError(f"{where} action/observation: {error}") from error
        _require_enum(observation["source"], {"synthetic", "recorded"}, f"{where} source")
        _require_ms(observation["captured_at_ms"], f"{where} captured_at_ms")
        if observation["captured_at_ms"] > record["decision_at_ms"]:
            raise ManifestValidationError(f"{where} observation is after action onset")

        media = record["media"]
        _require_fields(media, {"kind", "path", "start_ms", "end_ms", "media_to_run_offset_ms"},
                        f"{where} media")
        _require_enum(media["kind"], {"image", "video"}, f"{where} media kind")
        _require_media_path(media["path"], f"{where} media path")
        _require_ms(media["start_ms"], f"{where} media start_ms")
        _require_ms(media["end_ms"], f"{where} media end_ms")
        _require_ms(media["media_to_run_offset_ms"], f"{where} media offset", signed=True)
        if media["start_ms"] > media["end_ms"]:
            raise ManifestValidationError(f"{where} media window is reversed")
        if media["kind"] == "image" and media["start_ms"] != media["end_ms"]:
            raise ManifestValidationError(f"{where} image must have a point timestamp")
        mapped_start = media["start_ms"] + media["media_to_run_offset_ms"]
        mapped_end = media["end_ms"] + media["media_to_run_offset_ms"]
        if mapped_start < 0 or mapped_end != observation["captured_at_ms"]:
            raise ManifestValidationError(f"{where} media clock mapping is invalid")

        label = record["label"]
        _require_fields(label, {"origin", "status", "evidence_id", "review_id"}, f"{where} label")
        _require_enum(label["origin"], {"input_log", "human", "inferred"}, f"{where} label origin")
        _require_enum(label["status"], {"pending", "accepted", "rejected"}, f"{where} label status")
        _require_id(label["evidence_id"], f"{where} evidence_id")
        if label["status"] == "pending":
            if label["review_id"] is not None:
                raise ManifestValidationError(f"{where} pending label must not have review_id")
        else:
            _require_id(label["review_id"], f"{where} review_id")

        run_id = observation["run_id"]
        recording_id = record["recording_id"]
        group = record["leakage_group_id"]
        source = observation["source"]
        observation_key = (run_id, observation["observation_id"])
        if record["record_id"] in record_ids:
            raise ManifestValidationError(f"{where} record_id is duplicated")
        if observation_key in observation_ids:
            raise ManifestValidationError(f"{where} run/observation pair is duplicated")
        record_ids.add(record["record_id"])
        observation_ids.add(observation_key)
        _remember(runs, run_id, (group, source), f"{where} run provenance")
        _remember(recordings, recording_id, (group, source, media["path"], media["kind"]),
                  f"{where} recording provenance")
        _remember(paths, media["path"], recording_id, f"{where} media path identity")
        _remember(alignments, (run_id, recording_id), media["media_to_run_offset_ms"],
                  f"{where} clock alignment")
    return copy.deepcopy(manifest)
```
