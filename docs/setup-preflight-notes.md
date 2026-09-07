# Setup preflight: declarations, local facts, and unmeasured work

Date: 2026-09-07. The offline preflight report is implemented and reviewed through `4fbcafac3fdab72401bd497ac30dbfca38b3caab` (feature `5b7e68e` plus the real subprocess write-failure regression). This completes a configuration-report boundary, not GPU/model/controller readiness. Training remains explicitly deferred by the owner.

The [exact implemented specification](superpowers/specs/2026-09-07-setup-preflight-design.md) defines the schema, comparison rules, collector, command, and acceptance boundary; the [implementation plan](superpowers/plans/2026-09-07-setup-preflight.md) records the work sequence. [Project status](../STATUS.md) records verification and publication limits.

## Implemented command and report boundary

From the repository root, select an explicit profile and a fresh ignored output path:

```sh
PYTHONPATH=src python3 -m arknights_vision_agent preflight \
  --profile examples/setup_qwen38.json --output work/setup-report
```

`examples/setup_qwen3vl8b.json` is the second candidate declaration. Neither example chooses or enables a runtime. The command writes exactly one `preflight.json`; it has no force, live, training, download, model-path, device-address, credential, endpoint, or shell-command option. No profile values are inferred from the environment.

The strict v1 profile contains exactly `schema_version`, `model`, and `controller`. Either integration may independently be null. A configured model declares an ID, a syntactically pinned 40-character lowercase hexadecimal revision, and an architecture name; a controller declares the distinct `maa` or `maaframework` backend and a numeric release. The entire profile is validated and detached before collecting facts. A syntactic revision pin does not authenticate a snapshot or prove compatibility.

The report's metadata is `schema_version: 1`, `scope: offline_setup_preflight`, and fixed `research_snapshot_id: repository-research-2026-09-07-v1`. Its evidence sections stay separate:

| Section | What it means |
| --- | --- |
| `declared` | Detached, validated submitted profile; not discovered or enabled configuration |
| `comparison` | Model and controller comparisons with the fixed repository research snapshot |
| `observed_local` | Calling interpreter/OS features and boolean discovery of four fixed executable names |
| `unmeasured` | Exactly 12 ordered identifiers for evidence this command does not collect |
| `execution` | Exactly five flags, all always false |

The ordered `unmeasured` identifiers are `gpu_identity`, `gpu_memory`, `model_snapshot`, `model_processor`, `dependency_compatibility`, `model_inference`, `media_decoding`, `media_timestamps`, `label_quality`, `controller_connection`, `controller_actions`, and `game_performance`.

The five `execution` fields are `training_started`, `inference_started`, `device_contacted`, `model_downloaded`, and `native_tools_executed`. Each remains false regardless of declarations, comparison results, null integrations, or executable presence. There is no aggregate ready flag, pass percentage, memory-fit verdict, or training authorization.

## Fixed research comparison, not a compatibility lock

The implemented tuples are exactly the saved declarations in the [model/hardware notes](model-and-hardware-notes.md), [MaaFramework contract](maaframework-integration-notes.md), and exact specification. The saved Qwen3.8 tuple names `Qwen3_5ForConditionalGeneration`, while the saved Qwen3-VL tuple names `Qwen3VLForConditionalGeneration`; no broad model-name substring selects a loader. Architecture names are compared as strings, never imported or instantiated.

Only an exact known model ID and revision supplies an expected architecture. The correct declaration is `matches_research_snapshot`; a different architecture for that exact tuple is `contradicts_research_snapshot`. An unfamiliar ID or revision is `unreviewed_contract`, even when a familiar ID is paired with a new revision. Controller matching requires the backend and release together; a different numeric release stays unreviewed. Null integrations are `not_configured`.

These are fixed research references, not claims about the latest releases, installed dependencies, or runtime compatibility. Transformers v5.16.1 remains an interface reference from the existing notes, not a tested dependency lock. This closeout adds no new external verification; the earlier delegated preflight web checks returned no source content and provided none. Selecting a real dependency lock, changing revisions, or implementing a native interface still needs fresh primary-source verification and separate execution evidence.

## Exit status, warnings, and output safety

- A successfully written report with no known model contradiction exits 0, including unknown or null integrations. Exit 0 means reporting succeeded, not readiness or compatibility.
- A well-formed known model/architecture contradiction retains its diagnostic report and exits 2. Every null or unreviewed integration independently receives a warning, including a null/unreviewed controller beside a contradictory model. The warning does not suppress or replace the contradiction result.
- Invalid JSON/profile data, unreadable or nonregular input, missing nonblocking-input support, or local-observation failure exits 2 without creating a report or missing output parents. Field-only or fixed diagnostics do not echo submitted private values.

The explicitly selected profile must be a regular strict UTF-8/JSON file no larger than 2 MiB; the bounded reader reads at most 2 MiB + 1 bytes. A user-selected profile symlink is allowed. The CLI requires `O_NONBLOCK`, but not the other inventory features merely to report their absence; the reporting API can report absent inventory capabilities or `uname`. Existing inventory retains its stronger POSIX feature gate, and replay/preparation input behavior is unchanged.

Existing output files, directories, and live or dangling symlinks are refused before reading input or collecting facts. Reports are fully built and rendered before creating a fresh output directory, then written as finite, sorted-key compact JSON with a final newline. The output parent is owner-trusted; a later write failure may retain newly created partial output. Neither interface availability nor bounded byte reads establish a hostile-filesystem sandbox or wall-clock deadline.

Keep real reports private: declarations and host facts may be sensitive. No report starts a follow-on job or changes a profile automatically.

## Observed local evidence, not H20 evidence

The retained installed-package reports and a fresh isolated `python -I -B` collector check observed:

| Observation | Result in the current development environment |
| --- | --- |
| Interpreter | CPython 3.13.7 |
| Host | `darwin` / `posix`, `arm64` |
| Byte-inventory interface features | POSIX, descriptor-relative open, `O_DIRECTORY`, `O_NOFOLLOW`, and `O_NONBLOCK` booleans true; their conjunction true |
| Selected programs on current PATH | `ffmpeg`, `ffprobe`, `adb`, `nvidia-smi` not found |

The collector retains only booleans from `shutil.which` for those four fixed names; it does not execute the programs. It records no absolute executable/interpreter paths, hostname, username, environment contents, package inventory, or device identifiers. It does not import optional runtimes, scan snapshots, access private media, install/download/load models, run inference/native decoding, contact a device/GPU, or train. These observations apply only to the calling interpreter, host, and PATH, not every installed environment or a target machine. The H20 machine and Python 3.11/3.12 remain untested.

Earlier, separate package-metadata research on the current Mac found no installed metadata for torch, transformers, peft, accelerate, safetensors, qwen-vl-utils, av, or maa-framework, and reported Pillow 12.0.0. This historical observation is not a preflight field or a newly repeated package audit. Missing metadata is not a search of all environments; present metadata would not establish importability or compatibility.

Closeout reused the existing exact-reviewed-HEAD wheel and installed environment, confirmed the module resolved from installed `site-packages` under isolated Python, and checked all 12 package Python files against the Git commit, archived source, wheel, and installation. All five retained preflight reports exactly matched fresh installed API output, including the ordered unmeasured fields and false execution flags. A real installed-command retry against an existing report exited 2 with unchanged bytes and SHA-256. Exact hashes and test counts are in [project status](../STATUS.md); absolute interpreter/module paths remain private.

The full suite ran in the installed environment, but its CLI subprocess tests explicitly select the archived source path. Separate real `-I` installed command checks cover replay, preparation, inventory, and preflight; these are distinct from running the test suite in that environment. Synthetic replay remains non-executing, preparation has three assigned groups and zero eligible records/groups, and inventory covers three synthetic text assets, not videos.

## Checks that remain separate

| Gate | Evidence still needed |
| --- | --- |
| H05 / H20 host | Approved access, exact GPU/partition, available memory/storage, driver/software compatibility, and measurements |
| Model snapshot | Approved local files, immutable identity, processor/template hashes, a tested dependency lock, local-only loading, and measured inference memory/latency |
| H04/H07 / controller | Approved device, installed SDK behavior, capture timing/resolution, coordinate calibration, action completion, and supervised stop behavior |
| H02/H03 / data | Approved originals, actual media timestamps, causal windows, label evidence and review |
| Native media parser | Trusted executable/build and separately specified parser, timestamp, output, and extraction limits |
| Actual training | A later explicit owner decision; no setup/preflight result overrides the current deferral |

Executable presence cannot populate GPU/device measurements. A successful byte inventory cannot populate video/label/model checks. A valid model ID or syntactically pinned revision cannot establish runtime compatibility. Native-runtime work remains in verification/build preparation: downloaded-source identity checks are not a completed build or decoder validation, and no actual decoding calibration has been completed.

## Implemented acceptance coverage and limits

Reviewed tests cover exact profile shapes/types and immutable-revision syntax; both known tuples, wrong-loader cases, unfamiliar revisions/releases, and independent nulls; detached validation and reports; actual and simulated local capabilities; fixed-name PATH presence without execution; prevention of optional imports/subprocess/network/media work; bounded strict regular-file input; privacy-safe failures; pre-read output refusal; retained contradiction reports and warnings; and output-write failures, including the real subprocess regression. Existing command behavior and the empty runtime-dependency list remain covered.

These checks establish the software/report boundary on the observed Python 3.13.7 Mac. They do not establish a real dependency lock, model loading or quality, GPU memory/latency, media timing/labels, controller behavior, or game performance, and they do not resume training.
