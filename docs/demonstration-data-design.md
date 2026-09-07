# Demonstration data: staged contract

This describes the staged offline data pipeline. Strict manifest validation and metadata eligibility/group-partition reporting are implemented as pure APIs and exposed through the offline `prepare` command. Real-media preparation remains follow-on work. It is a reversible continuation of the owner-approved plan. Real recordings and label review remain H02/H03 in `HUMAN_HELP.md`.

## What a useful example contains

A video clip alone is not yet an observation/action training pair. This project will preserve separate records for the source media, the information visible before a decision, the proposed or demonstrated action, and the evidence supporting its label. An edited winning video is not assumed to reveal every input, its timing, or the reason for a decision.

The first data tool validates an explicitly authored manifest; it does not infer button presses from video, download recordings, decode media, or train a model. Its exact representation is fixed in [the implemented v1 manifest contract](superpowers/specs/2026-09-07-demonstration-manifest-design.md). Automatic label proposals can be added later, but must remain distinguishable from input logs and human-verified labels.

Its initial labels are limited to the reviewed action vocabulary: supported menu choices, waiting, and stopping. Deployment, operator skills, retreating, and other battle actions cannot yet be represented and must not be silently coerced into these labels. A menu-only data export would not train a complete battle-playing policy.

## Design choices

1. Ingest all video frames directly as training examples: not selected. It loses action provenance and risks placing near-identical frames from the same run in training and evaluation.
2. Immediately build an annotation web application: deferred until a real sample reveals which review interactions are needed.
3. Start with a strict manifest, review eligibility checks, and group-aware splits: selected. This is testable using generic synthetic metadata without accessing private media.

## Manifest direction

Each demonstration record will reference:

- An opaque record ID, run ID, source recording ID, and leakage-group ID. The leakage group covers related runs, duplicate uploads, edits, or multiple camera views that must stay in the same split.
- An observation using the existing schema and the decision timestamp on the same run-relative clock.
- A source-media interval ending no later than the decision timestamp. Media paths are relative to a separately configured private root; no URLs, embedded credentials, absolute paths, or directory traversal.
- The demonstrated action in the existing action vocabulary. The shared action guard must accept it against its observation.
- Label origin (`input_log`, `human`, or `inferred`) and review status (`pending`, `accepted`, or `rejected`). A manifest entry claiming acceptance is provenance metadata, not proof that a reviewer inspected it.
- Declared permission to use the media. This is an owner attestation, not an automatic rights determination.

Unknown or inconsistent metadata should fail validation with a record index and a concise reason. Unreviewed and rejected labels may be stored for review, but never silently promoted to training-ready examples. Synthetic examples must be kept separate from recorded examples in eligibility reports.

## Split rules

The implemented report follows [the exact v1 eligibility and partition contract](superpowers/specs/2026-09-07-preparation-report-design.md). These are assignments over declared metadata, not exported or inspected media.

Splits must preserve whole runs and source recordings. Explicit leakage groups make related recordings indivisible as well. A run or recording appearing under multiple leakage groups is an error rather than an opportunity to put it in both training and evaluation.

Use a deterministic ordering based on a recorded seed and stable group identifiers. Split assignments must not depend on input row order. Small datasets may not populate all partitions; report actual group and record counts rather than claiming an evaluation set exists. This first split is an infrastructure aid, not a claim of adequate statistical power or game coverage.

## Future media preparation

Once H02 is available, inspect actual frame rate, duration, edits, visual legibility, and input-log alignment. Select causal frame windows before each action. Keep future outcome frames out of policy inputs; store run outcome separately for analysis. Record extraction settings and source hashes in generated metadata. The manifest-only stage cannot verify file existence, content, frame timestamps, visual coverage, input-log truth, or data-use rights.

## Concrete v1 decisions from design review

These decisions narrow the implementation contract; they do not validate any real recording:

- Keep media-relative and run-relative clocks separate. Declare a constant integer `media_to_run_offset_ms` per run/recording pair, with `run_ms = media_ms + offset_ms`. Nonlinear or edited alignment is outside v1. Media intervals include both endpoint timestamps. Require a nonnegative mapped start, `mapped_start <= mapped_end`, `mapped_end == observation.captured_at_ms`, and `captured_at_ms <= decision_at_ms`. Here the decision timestamp means action onset. This binds the observation to the latest input frame and applies causality even to stop labels, despite the execution guard's intentionally permissive stop timing.
- Require an opaque label-evidence ID. Accepted or rejected reviews must carry an opaque review ID; pending labels have no review ID. A reviewed inferred label stays marked inferred. These references are declarations only and are not opened or independently verified by the manifest validator.
- Make record IDs globally unique and `(run_id, observation_id)` pairs unique. Every run and recording has exactly one leakage group across all records, including excluded records. A recording has one path and source type; one literal media path must not masquerade as multiple recording IDs. Constant clock mappings must agree for each run/recording pair. Multiple runs per recording and recordings per run are permitted when these consistency rules hold.
- Media references are literal relative POSIX paths. Reject absolute paths, backslashes, colons, empty segments, `.`/`..` segments, control characters, and home-expansion prefixes. Do not expand variables, decode URLs, normalize away traversal, inspect files, or resolve symlinks. Report lexical validation only. A future reader must separately enforce resolved containment in its approved private root.
- Assign each leakage group with a versioned SHA-256 algorithm over a canonical JSON encoding of `[seed, leakage_group_id]` and fixed integer-weight partition thresholds. Record the algorithm, seed, and weights. Assignment is independent of row order and label/permission eligibility. Never use Python's process-randomized `hash()`. Empty partitions remain empty and are reported as such.
- Report metadata eligibility separately: exactly recorded source, accepted review, and literal Boolean permission `true`. Report all exclusion reasons; synthetic, pending, rejected, and permission-denied records never count toward recorded export eligibility. Reject live-source manifests entirely. Neither metadata eligibility nor partition membership proves that a sample is correct or trainable.

## Acceptance for a later implementation plan

1. A synthetic example can be validated and split without opening a media file or importing a model/controller package.
2. Bad actions, timing, provenance, paths, duplicate IDs, or split-group conflicts are rejected by tests.
3. Only explicitly accepted, permission-attested, recorded examples are eligible for a real training export; the tool explains every exclusion.
4. Reordering records preserves assignments and neither source recording nor run can leak across partitions.
5. Reports remain explicit about declared metadata versus independently verified evidence.

No training export format is locked yet. It will be selected against the pinned model processor and training library after their current interfaces have been verified.
