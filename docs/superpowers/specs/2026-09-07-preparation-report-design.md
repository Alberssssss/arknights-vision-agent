# Metadata eligibility and group-partition report v1

## Scope and design choice

This is the next reversible step in the owner's approved setup/data-preparation work. Actual training remains deferred. It follows the strict demonstration-manifest boundary, not a media decoder or model-specific training export.

Three approaches were considered: splitting individual frames (would separate related samples), balancing shuffled groups to exact quotas (would move existing assignments when groups are added), and independently hashing whole leakage groups (selected). The selected design preserves assignments when rows are reordered, unrelated groups are added, or label/permission status changes. It does not guarantee exact ratios, populated partitions, coverage, or statistically useful evaluation.

The function validates every input record, including excluded records. It reports eligibility of declared metadata, never training readiness or verified gameplay quality. It performs no file, network, device, model, or training operations.

## Public API and configuration

Create `preparation.py` with:

```python
class PreparationValidationError(ValueError): ...

def build_preparation_report(
    manifest: dict, *, seed: int = 0, weights: dict | None = None
) -> dict: ...
```

Call `validate_manifest` internally. Translate its expected `ManifestValidationError` to `PreparationValidationError`; do not duplicate or weaken manifest validation. Errors must not echo arbitrary input values. The report is detached from both the manifest and supplied weights.

`seed` is an exact built-in integer in `0..2**63-1`. `weights=None` means `{"train": 8000, "validation": 1000, "test": 1000}`. Otherwise weights are a plain dictionary with exactly those keys and exact integer values in `0..10000` whose sum is 10000. Booleans and subclasses do not satisfy exact-type checks. Zero-weight partitions are allowed and reported honestly.

## Stable assignment algorithm

Algorithm name: `sha256-json-mod10000-v1`.

1. Encode `[seed, leakage_group_id]` with Python `json.dumps`, `ensure_ascii=False`, `separators=(",", ":")`, `allow_nan=False`, then UTF-8. There is no whitespace, Unicode normalization, or stripping of identifiers.
2. Prepend the exact ASCII bytes `arknights-vision-agent/split/v1` followed by a single newline byte.
3. Compute SHA-256. Interpret all 32 digest bytes as one unsigned big-endian integer; take the remainder modulo 10000.
4. For bucket `b`, use train if `b < train_weight`; otherwise validation if `b < train_weight + validation_weight`; otherwise test. All boundaries are half-open. Partition order is always train, validation, test.

The group ID, seed, weights, and algorithm version determine the partition. Do not use process-randomized Python `hash`, a mutable random generator, input position, eligibility, group size, or a fallback rebalance. Modulo assignment is a deterministic approximation to configured proportions, not an exact quota.

Golden vectors (default weights unless stated):

| Seed | Group | SHA-256 | Bucket | Partition |
| --- | --- | --- | --- | --- |
| 0 | `group-demo` | `5bb5c0fb672c1ee08f49264458d957877177266649b0ce2bd57fcddaa59dd806` | 7382 | train |
| 0 | `group-5` | `214147f80233ca0cc2385e119bc8bf3a51dbefb531d8a31358f854721ee70b1c` | 8940 | validation |
| 0 | `group-4` | `870e08ef281d703e524f047f944b76842c06c1b6952bb3e2f0ff1708150c2d79` | 9241 | test |
| 7 | `group-demo` | `db4566e9689ed267263f5fe04178767fd62c4be47f533a49dacac1bc681decb9` | 5545 | train |
| 9223372036854775807 | `组🦊` | `8d92587705ce8e3ab2169b5f62e1933768836298a871db60b9c1c23ffc70f156` | 7622 | train |

For bucket 7382, weights `(7382, 1, 2617)` assign validation; `(7382, 0, 2618)` assign test; `(7383, 0, 2617)` assign train. This tests actual threshold boundaries without mocking the hash.

## Metadata eligibility

A record is metadata-eligible exactly when `record["observation"]["source"]` is `recorded`, label status is `accepted`, and `usage_permitted` is literal `True`. Report every applicable exclusion reason in this fixed order:

1. `synthetic_source` when source is synthetic.
2. `label_pending` when status is pending.
3. `label_rejected` when status is rejected.
4. `usage_not_permitted` when permission is false.

An accepted inferred label can be metadata-eligible; its origin in the manifest remains inferred. This is not independent confirmation of its label or rights. A group counts as eligible if it contains at least one eligible record. All rows, not just eligible ones, determine assigned group/record counts.

## Declaration digest

Algorithm name: `sha256-canonical-manifest-v1`.

Take the validated detached manifest and sort its records by `record_id` using Python's Unicode-codepoint string ordering. Preserve order within other arrays, including `available_options`. Serialize using `json.dumps(sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)` and UTF-8. Hash the exact prefix `arknights-vision-agent/manifest/v1` plus newline plus those bytes with SHA-256; output lowercase hexadecimal.

Dictionary key order and record order do not affect this digest. Other declared values, including label, permission, media reference, and option ordering, remain represented. Seed and weights are recorded separately and do not change the manifest digest. This digest binds the report to declared metadata; it is not a source-media hash, authentication, or content-deduplication check.

## Exact report structure

All returned containers are plain dictionaries/lists, detached from arguments. The root contains exactly:

- `schema_version`: integer 1.
- `scope`: `metadata_only`.
- `manifest_digest`: exactly `algorithm` and `sha256`, as above.
- `split`: exactly `algorithm`, `seed`, and `weights`, as above.
- `records`: sorted by record ID; each entry has exactly `record_id`, `leakage_group_id`, `partition`, `metadata_eligible` (Boolean), and `exclusion_reasons` (list).
- `groups`: sorted by leakage-group ID; each has exactly `leakage_group_id`, `partition`, `record_count`, and `eligible_record_count`.
- `summary`: structure below.
- `verification`: exactly `media_inspected`, `label_evidence_verified`, `permission_verified`, `training_started`, and `game_clear_verified`, all false.

The summary contains exactly `record_count`, `eligible_record_count`, `excluded_record_count`, `group_count`, `eligible_group_count`, `exclusion_reason_counts`, `partitions`, `empty_partitions`, and `eligible_empty_partitions`.

`exclusion_reason_counts` contains all four reason codes, including zero counts; one record may contribute to several reasons, so the reason-count sum may exceed `excluded_record_count`. `partitions` has train, validation, and test entries, each with exactly `record_count`, `eligible_record_count`, `group_count`, and `eligible_group_count`. `empty_partitions` lists partitions with no assigned records. `eligible_empty_partitions` lists partitions with no eligible records. Both use fixed partition order; zero-weight partitions are not omitted. A partition with synthetic/rejected-only records is not empty by assignment but is empty by eligibility.

Reports retain opaque record/group IDs but omit media paths, actions, observations, and evidence/reviewer identifiers. Submitted identifier values are data, not executable instructions. There is no export, success rate, training-ready flag, automatic review promotion, or inferred game-clear claim.

The verification flags describe what this reporting operation inspected, verified, or started, not the global history of a project or recording. Leakage groups are declarations; their validation cannot establish that undeclared duplicate media is absent.

## Required verification

- Genuine red/green tests for eligibility reasons, exact configuration types/bounds, whole-group assignments, report counts, stable ordering/digest, and input/output isolation.
- Actual-hash golden vectors and threshold boundaries, different seeds, cross-process hash-seed independence, row-order and additional-group stability.
- Invalid excluded records still fail through the shared manifest boundary. Rejected, pending, permission-denied, and synthetic examples are distinguished from eligible recorded examples.
- Explicit assigned-empty versus eligible-empty cases and groups with mixed eligibility. No source files need exist.
- Existing suite stays green, then specification review followed by independent quality review. Passing fixtures demonstrates software behavior only.
