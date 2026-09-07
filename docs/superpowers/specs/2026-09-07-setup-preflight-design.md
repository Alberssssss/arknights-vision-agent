# Offline setup profile and local facts

Date: 2026-09-07. This continues the owner-approved setup phase. It neither launches training nor treats a configuration as authorization to access a GPU, model, media, or device.

## Purpose and alternatives

Implement the report proposed in `docs/setup-preflight-notes.md`: catch a model/loader contradiction now and provide a reproducible way to collect limited host facts later. This is one preparation step toward real model/controller integrations, not their replacement. Native media runtime setup is researched separately in parallel.

Alternatives: a static checklist cannot detect a submitted mismatch; an eager GPU/model “doctor” would contact or load unavailable resources and conflate compatibility with configuration; select a strict declaration comparison plus limited current-process discovery. Snapshot auditing, dependency installation/locking, native execution, media parsing, inference and training are not part of this command.

## Public interfaces and profile

New module `preflight.py` exports `PreflightError(ValueError)`, `validate_setup_profile(profile: dict) -> dict`, `collect_local_facts() -> dict`, and `build_preflight_report(profile: dict) -> dict`. Validation is pure and detached. Building a report validates the entire profile before collecting any local facts; it never reads referenced model files or contacts a service.

Exact profile shape:

```json
{
  "schema_version": 1,
  "model": {
    "model_id": "Qwen/Qwen3.8-27B",
    "revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
    "architecture": "Qwen3_5ForConditionalGeneration"
  },
  "controller": {"backend": "maaframework", "version": "5.12.3"}
}
```

- Every object is a plain dictionary with exactly its stated keys; schema version is exact integer 1, not Boolean. Both `model` and `controller` may independently be null.
- `model_id` is a plain ASCII string matching `[A-Za-z0-9][A-Za-z0-9._-]{0,127}/[A-Za-z0-9][A-Za-z0-9._-]{0,127}` in full. It is a declaration, never a URL or filesystem path.
- `revision` is exactly 40 lowercase hexadecimal characters; reject branch/tag names, upper-case hashes, and other shapes. This syntactic pin is not authenticity or compatibility evidence.
- `architecture` is a plain string matching `[A-Za-z][A-Za-z0-9_]{0,127}` in full. Do not import or instantiate it.
- Controller backend is exactly `maa` or `maaframework`, two distinct systems. Version is a plain string matching `[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}` in full. No leading `v` or mutable release names. Unknown numeric releases stay unreviewed; they do not select another backend automatically.
- No additional fields for endpoints, addresses, credentials, model paths, live/training enablement, commands, or environment defaults. Reject bad values with field-only diagnostics, never their submitted contents.

## Research comparison, not compatibility certification

Use fixed snapshot ID `repository-research-2026-09-07-v1` and the already documented declarations:

| Model | Revision | Architecture |
| --- | --- | --- |
| Qwen/Qwen3.8-27B | 1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0 | Qwen3_5ForConditionalGeneration |
| Qwen/Qwen3-VL-8B-Instruct | 0c351dd01ed87e9c1b53cbc748cba10e6187ff3b | Qwen3VLForConditionalGeneration |

Controller snapshot releases are `maaframework`/`5.12.3` and `maa`/`6.17.2`, from the existing integration and collection notes. These are research references, not installed/tested dependency locks or claims that they are the latest releases.

Model comparison has exactly `status` and `expected_architecture`. Null model means `not_configured`/null. A known model ID **and exact known revision** yields its expected architecture and either `matches_research_snapshot` or `contradicts_research_snapshot` according to architecture equality. Every other model ID/revision combination is `unreviewed_contract`/null, even if the ID is known; do not extrapolate architecture to an unreviewed revision.

Controller comparison has exactly `status`. Null means `not_configured`; a known backend/release pair means `matches_research_snapshot`; every other syntactically valid release means `unreviewed_contract`. Do not treat a new SDK release as compatible or as a proven contradiction merely because it differs.

## Observed local facts

Collect only the calling interpreter/host facts below:

- Python implementation from `sys.implementation.name` and version string `major.minor.micro` from `sys.version_info`.
- `sys.platform`, `os.name`, and `os.uname().machine` if `os.uname` exists, otherwise null. Do not use `platform.platform()`, query hostnames, or run hardware commands to fill missing fields.
- Five booleans: POSIX OS, `os.open` membership in `os.supports_dir_fd`, and existence of each of `O_DIRECTORY`, `O_NOFOLLOW`, `O_NONBLOCK`. Their conjunction is `required_features_present`; it describes interface availability, not a tested filesystem.
- For exactly `ffmpeg`, `ffprobe`, `adb`, and `nvidia-smi`, call `shutil.which(name)` and retain only whether it returns a path. Never serialize returned paths or execute the programs. PATH is observed only for this fixed-name discovery, not used to choose model/controller configuration.

No hostname, username, environment contents, timestamps, absolute executable/interpreter paths, full package list, file scanning, optional-package imports, subprocesses, network activity, or target hardware measurements. `os.uname`/PATH OS errors become a generic `PreflightError` without raw path-bearing error details. Collection is not a filesystem wall-clock timeout or a check of every installed environment. The API remains callable on hosts without POSIX inventory support; report absent capabilities honestly.

## Exact report

```json
{
  "schema_version": 1,
  "scope": "offline_setup_preflight",
  "research_snapshot_id": "repository-research-2026-09-07-v1",
  "declared": {"schema_version":1,"model":null,"controller":null},
  "comparison": {
    "model":{"status":"not_configured","expected_architecture":null},
    "controller":{"status":"not_configured"}
  },
  "observed_local": {
    "python":{"implementation":"cpython","version":"3.13.7"},
    "platform":"darwin",
    "os_name":"posix",
    "machine":"arm64",
    "inventory_features":{"posix":true,"open_dir_fd":true,"o_directory":true,"o_nofollow":true,"o_nonblock":true,"required_features_present":true},
    "executables_on_path":{"ffmpeg":false,"ffprobe":false,"adb":false,"nvidia-smi":false}
  },
  "unmeasured":["gpu_identity","gpu_memory","model_snapshot","model_processor","dependency_compatibility","model_inference","media_decoding","media_timestamps","label_quality","controller_connection","controller_actions","game_performance"],
  "execution":{"training_started":false,"inference_started":false,"device_contacted":false,"model_downloaded":false,"native_tools_executed":false}
}
```

`declared` is the detached validated submitted profile, not always the null example. `observed_local` contains actually collected values; the example host/program values above are illustrative, not constants. The unmeasured array has exactly the shown identifiers and order; all execution flags remain false regardless of profile, local executable presence, or comparison result. No aggregate “ready” flag, suitability verdict, pass percentage, or permission to train/run.

## CLI boundary

```sh
PYTHONPATH=src python3 -m arknights_vision_agent preflight \
  --profile examples/setup_qwen38.json --output work/setup-report
```

Only required `--profile` and `--output` are added. Refuse any existing output file/directory/live or dangling symlink before reading the profile or collecting facts. Profile input is explicitly user-selected; open nonblocking, require a regular file, and read at most 2 MiB + 1 bytes. Reuse strict UTF-8/JSON parsing and exclusive fresh-output mechanics. A user-selected profile symlink is allowed, as for inventory requests.

The CLI's regular-input boundary requires `O_NONBLOCK`; if absent, fail clearly before opening input. It does **not** require `O_DIRECTORY`, `O_NOFOLLOW`, or POSIX descriptor-relative opening just to report their absence. Existing replay/preparation portability and inventory's stronger platform gate must stay unchanged. Initial acceptance execution targets the current macOS environment; the reporting API must support absent `uname`/inventory capabilities. No platform execution is established by this design alone.

Extract only shared regular-file input mechanics into a CLI helper `_load_regular_object(path, *, max_bytes, kind)`. Inventory retains its existing `require_inventory_platform()` gate and exact existing error labels by wrapping helper failures as needed. Do not change replay/preparation input readers. The helper must close descriptors even if wrapping a descriptor fails. Kind labels are internal fixed strings, not submitted values.

Fully build and render before creating output. Invalid profile/JSON, unreadable/nonregular input, unsupported nonblocking input, or observation failures exit exactly 2 without a report, missing output parents, traceback, or submitted values. Successful collection writes exactly `preflight.json`, finite sorted-key compact JSON with final newline. Trusted output-parent and partial-new-output-on-write-failure semantics are unchanged; real reports may contain sensitive declarations and should stay private.

A well-formed **known contradiction** still writes the diagnostic report and prints an error explaining that it is retained. After successful writing, exit 2 if and only if the model comparison is `contradicts_research_snapshot`; otherwise exit 0. Independently emit a warning for every unreviewed or unconfigured integration, including a null/unreviewed controller paired with a contradictory model. Matches never print “ready” or “compatible.” Always state on a successful report write that it records local facts only and no training, inference, or device contact occurred. No report may start a follow-on job or change a profile automatically.

Commit two demonstration profiles: `setup_qwen38.json` uses the exact shown 27B tuple and MaaFramework release; `setup_qwen3vl8b.json` uses the exact 8B tuple and same controller reference. They demonstrate declarations, not a final model/controller choice or runtime enablement. README explains known mismatch exit/report behavior, research-only comparisons, local versus target facts, private output, fresh paths, and next GPU/media/integration checks.

## Acceptance

Test-first work covers exact shapes/types/nulls/regex boundaries, mutable/invalid revisions and private error text, detached validation, both known tuples, wrong architecture, unfamiliar IDs/revisions/releases, and no cross-backend matching. Malformed profiles must prevent all local collection.

Local-fact tests use fixed injected low-level observations and test real collection separately; do not introduce public test-only injection switches. Verify absent inventory features/`uname`, all executables appearing present without execution, suppression of discovered paths, generic OS-error handling, and unmeasured/false fields under every comparison result. Patch forbidden subprocess/network entry points to fail if invoked; do not mock the public reporting function itself to prove safety.

Real subprocess tests cover help, both examples, exact serialized output, strict 2 MiB/UTF-8/JSON limits, FIFO/regular-file rejection with a test timeout, profile symlinks, pre-read output refusal, canonical/unchanged output, failure privacy/no new parents, write failures, retained contradiction reports and exit 2 (including null and unknown-release controllers), and unknown/unconfigured warnings and exit 0 when no contradiction exists. Regression tests retain all three existing commands and inventory's stronger platform gate/error behavior. Finish with fresh installed-package checks and independent specification then final quality review.
