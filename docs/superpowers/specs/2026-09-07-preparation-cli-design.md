# Offline preparation command design

## Scope and approval basis

This command makes the reviewed metadata-preparation report usable without writing Python. It is part of the owner's authorized setup/data-preparation phase; actual training remains deferred. Implement only after manifest validation and preparation reporting pass their reviews.

A new annotation application would require real-sample workflow choices. A model-specific export would require a tested processor/training stack. The selected smaller interface is a metadata-only CLI, reusing the existing strict JSON, manifest, and preparation boundaries.

## Interface

```sh
PYTHONPATH=src python3 -m arknights_vision_agent prepare \
  --manifest examples/synthetic_demonstrations.json --output work/preparation-demo
```

`--manifest` and `--output` are required filesystem paths. Optional `--seed` is an integer (default 0); optional `--weights TRAIN VALIDATION TEST` supplies three integers. Defaults and exact range/sum validation belong to `build_preparation_report`, not a duplicate CLI policy. There are no training, device, model, download, force, or overwrite switches.

The command reads the one explicitly supplied JSON manifest file, not its referenced media. Use a bounded binary read of at most 16 MiB plus one byte, then strict UTF-8 decoding and the existing `load_json_object` with the same 16 MiB limit. Reject duplicate keys, nonfinite values, bad Unicode, oversized/deep input, malformed schemas, and invalid preparation configuration through the reviewed boundaries. Reading a manifest path does not authorize opening source media or following references inside it.

Render the complete report before creating output. Create a fresh output directory (including missing parents) and exclusively create `preparation.json` as UTF-8 JSON with sorted keys, `allow_nan=False`, compact separators, and one trailing newline. Refuse an already existing output directory, file, or symlink, including a dangling symlink. There is no overwrite or cleanup of existing data. If an I/O failure leaves a newly created directory or incomplete file, retain it and report failure; do not imply atomic multi-file transactions or permission to remove unrelated files.

Successful report creation exits 0 even if no rows are metadata-eligible. This means the reporting operation succeeded, not that training/evaluation is ready. Print the output location, eligible/total record counts, explicit "metadata-only" scope, and that no media was inspected or training started. When `eligible_empty_partitions` is nonempty, print their names as a warning. Expected parser, JSON, validation, and filesystem failures exit 2 without a traceback; invalid manifest contents must not be echoed.

The existing `replay` command, its 2 MiB limit, output filenames, return codes, messages, and non-execution guarantees remain unchanged. Small shared file-reading/writing helpers may be extracted under regression tests, but no new dependency or unrelated behavior is needed.

## Public synthetic example

Add `examples/synthetic_demonstrations.json` with exactly three synthetic-source rows referencing nonexistent relative media files, each in its own run/recording/group. Use the known default-weight groups `group-demo`, `group-5`, and `group-4` to exercise all three partitions. Use valid menu select, wait, and stop labels respectively, and label statuses pending, accepted, and rejected; pending has null review ID, others have synthetic review IDs. Permission is false for all three. Every row remains excluded; the accepted row must not masquerade as reviewed real gameplay. No actual image/video accompanies the fixture.

Document the command, output filename, metadata-only meaning, non-overwrite policy, optional split settings, why all fixture rows are excluded, current menu-only action vocabulary, and links to the collection plan and human-help queue. Keep private manifests, recordings, datasets, and outputs out of public commits. The example is explicitly synthetic and safe to publish.

## Verification

Use real subprocess tests for top/subcommand help, the committed example, seed/weight forwarding, eligibility warning, exact 16 MiB boundary, oversized input, malformed/duplicate/nonfinite/invalid-Unicode JSON, missing input, invalid schema/configuration, all-ineligible success, and existing output file/directory/live or dangling symlink refusal. Check sentinel contents and absence of new output on invalid input. Exercise a file as output parent and expected failure without traceback.

Add a small white-box bounded-read check if needed to prove the reader requests limit+1 rather than reading the entire input; retain real file boundary tests as the behavioral evidence. Existing replay tests must pass unchanged. Test installation in a fresh environment and run both example commands with no network or heavyweight packages before publication. Keep training and real-game claims false in persisted output.
