# Demonstration-manifest v1 design

## Scope and approval basis

This implements the reversible metadata portion of the owner's approved autonomous setup/data-preparation work. Actual training is explicitly deferred. The broader collection and grouping decisions were reviewed in `docs/demonstration-data-design.md`; this document fixes the exact v1 representation before implementation.

The validator does not open media, inspect a device, infer actions, verify reviewers, establish data-use rights, generate training examples, or update model weights. A validated manifest means its declarations are structurally consistent, not that the demonstrations are correct or trainable.

## Public API

- `ManifestValidationError(ValueError)` is the public failure type.
- `validate_manifest(manifest: dict) -> dict` returns a detached deep copy of a validated manifest. It does not modify input or return mutable references into it.
- `is_valid_identifier(value: object) -> bool` is extracted into a small shared `identifiers.py` module. The existing action module uses the same implementation without changing its public API or identifier rules.

The implementation is standard-library-only Python 3.11+. Errors identify the record index and field/constraint without echoing arbitrary submitted values.

## Exact representation

All objects and lists are plain built-in dictionaries/lists. Unknown and missing keys are errors. Enums and identifiers are plain strings. Booleans never pass integer checks.

The top-level object contains exactly:

| Field | Contract |
| --- | --- |
| `schema_version` | Exact integer `1` |
| `max_action_age_ms` | Exact integer in `0..2**63-1`, explicitly recorded for the shared action guard |
| `records` | Plain list of 1..10,000 records |

Each record contains exactly:

| Field | Contract |
| --- | --- |
| `record_id` | Globally unique identifier |
| `recording_id` | Identifier for the original source-media asset |
| `leakage_group_id` | Identifier grouping related runs/recordings |
| `observation` | Existing exact observation schema; source must be `synthetic` or `recorded`, never `live` |
| `action` | Existing exact action schema accepted against that observation |
| `decision_at_ms` | Run-relative action-onset timestamp, exact integer `0..2**63-1` |
| `media` | Exact media object below |
| `label` | Exact label object below |
| `usage_permitted` | Exact Boolean owner attestation; false also represents permission not established |

The run ID is `observation.run_id`; no redundant record-level run ID is introduced. The shared guard binds the action to the same run and observation. Identifiers retain the existing rule: valid Unicode, nonblank, at most 128 characters. They are neither stripped nor normalized.

Media fields are exactly `kind`, `path`, `start_ms`, `end_ms`, and `media_to_run_offset_ms`:

- `kind` is `image` or `video`, a declaration rather than a detected media type.
- `path` is a literal relative POSIX reference to the original asset, not an extracted frame. It has 1..1024 valid Unicode characters. Reject leading `/` or `~`, any backslash or colon, control characters in Unicode category `Cc`, empty path segments, and segments equal to `.` or `..`. Do not expand variables, decode URLs, normalize the path, resolve symlinks, or inspect files. Literal percent signs and dollar signs have no special interpretation.
- `start_ms` and `end_ms` are media-relative inclusive endpoint timestamps in `0..2**63-1`, with start no later than end. An image requires equal endpoints.
- `media_to_run_offset_ms` is an exact signed 64-bit integer, defining `run_ms = media_ms + offset_ms`.
- The mapped start is nonnegative; the mapped end equals `observation.captured_at_ms`. Capture must be no later than `decision_at_ms`, for every label including stop. Capture is also bounded by `2**63-1`. These constraints prevent future observation windows from being declared as causal inputs.

The label object has exactly `origin`, `status`, `evidence_id`, and `review_id`:

- `origin`: `input_log`, `human`, or `inferred`.
- `status`: `pending`, `accepted`, or `rejected`.
- `evidence_id`: a valid opaque identifier for the supporting log/annotation evidence.
- `review_id`: `None` if pending; a valid opaque identifier if accepted or rejected.

An accepted inferred label remains inferred. IDs are not dereferenced or authenticated by the validator. Rejected/pending labels remain structurally valid records; they are not silently discarded.

## Shared action validation and causal timing

Call `validate_action(record['action'], record['observation'], now_ms=record['decision_at_ms'], max_age_ms=manifest['max_action_age_ms'])`. Wrap its expected validation failure as an indexed `ManifestValidationError`. Do not copy its screen, option, action-kind, freshness, or run/observation matching rules.

The action guard deliberately permits stopping with a stale/future observation. The data validator adds its own causal requirement (`captured_at_ms <= decision_at_ms`) even for stop, because training metadata must not contain a future input frame. Stale stop remains permitted; it is explicitly represented under the declared maximum age rather than falsely described as a freshness check applied to stop.

## Whole-manifest consistency

Validate every record, including synthetic, rejected, pending, or permission-denied records:

1. Record IDs are globally unique.
2. `(run_id, observation_id)` pairs are unique.
3. Each run belongs to exactly one leakage group and one source type.
4. Each recording ID has exactly one leakage group, source type, literal media path, and declared media kind.
5. One literal path may not be assigned multiple recording IDs.
6. The offset is constant for each `(run_id, recording_id)` pair.

Multiple runs per recording and recordings per run are allowed when these constraints hold. Row order is irrelevant; there is no requirement to sort records chronologically. Distinct paths with identical underlying content cannot be detected here; later media hashes/alignment review must address undeclared duplicates. Edited/nonlinear alignment is outside this v1 contract.

## Representative synthetic record

```json
{
  "schema_version": 1,
  "max_action_age_ms": 5000,
  "records": [{
    "record_id": "record-1",
    "recording_id": "recording-demo",
    "leakage_group_id": "group-demo",
    "observation": {
      "run_id": "run-demo", "observation_id": "frame-1",
      "screen": "recruitment", "available_options": ["option-a", "option-b"],
      "captured_at_ms": 1000, "source": "synthetic"
    },
    "action": {
      "run_id": "run-demo", "observation_id": "frame-1",
      "kind": "select", "option_id": "option-a"
    },
    "decision_at_ms": 1100,
    "media": {
      "kind": "video", "path": "demo/source.mp4",
      "start_ms": 0, "end_ms": 1000, "media_to_run_offset_ms": 0
    },
    "label": {
      "origin": "human", "status": "pending",
      "evidence_id": "evidence-demo", "review_id": null
    },
    "usage_permitted": false
  }]
}
```

No media file accompanies this example. Accepting its metadata must not cause a file read or make it eligible as recorded training material.

## Follow-on split/report boundary

A separate plan implements deterministic group partitioning and eligibility reports over this validated representation. Metadata eligibility will require recorded source, accepted review, and literal permission true, with all exclusion reasons reported. It will not prove content correctness, model performance, or game completion. A model-specific training export and actual media reader are separate later components.

## Acceptance evidence required

- Test-first valid and invalid examples, including exact boundaries, type subclasses, Unicode, causal stop timing, and all-record consistency.
- Existing action/replay/CLI tests remain green after extracting identifier validation.
- Input/output isolation and absence of media/device/model side effects are checked.
- Specification review followed by independent quality review has no unresolved important findings.
- Status reports distinguish metadata validation from inspected or training-ready data.
