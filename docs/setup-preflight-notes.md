# Setup preflight: declarations, local facts, and unmeasured work

Date: 2026-09-07. This is the next-milestone design basis, not an implemented preflight command or a GPU-readiness verdict. Training remains explicitly deferred by the owner.

## Local observation, not H20 evidence

The coordinator used isolated standard-library Python to inspect the current interpreter and selected package metadata. No discovered executable, optional model/controller package, native decoder, or GPU operation was run.

| Observation | Result in the current development environment |
| --- | --- |
| Interpreter | CPython 3.13.7 |
| Host | Darwin/macOS, arm64 |
| Byte-inventory capabilities | Descriptor-relative open and `O_DIRECTORY`, `O_NOFOLLOW`, `O_NONBLOCK` available |
| Selected programs on current PATH | `ffmpeg`, `ffprobe`, `adb`, `nvidia-smi` not found |
| Selected distribution metadata | No installed metadata found for torch, transformers, peft, accelerate, safetensors, qwen-vl-utils, av, or maa-framework; Pillow metadata reported 12.0.0 |

These observations apply only to that interpreter, host, and PATH. Missing metadata is not a search of every environment; present metadata would not establish importability or compatibility. No absolute paths, environment contents, device identifiers, or credentials were recorded. The H20 machine and Python 3.11/3.12 remain untested.

## Smallest useful next boundary

Prepare an offline setup-profile/local-facts report. Its purpose is to catch a declared loader mismatch and show what has actually been observed without contacting a target machine or loading weights.

- A strict bounded profile declares intended model ID, immutable revision, architecture, and intended MaaFramework release. Either integration can be absent. It contains no live/training switch, credentials, endpoints, device addresses, shell commands, or implicit environment-derived configuration.
- Compare declarations against the existing repository research snapshot using explicit categories: matches the snapshot, contradicts it, or is unreviewed. A new immutable revision is not automatically compatible.
- Keep the known Qwen3.8/Qwen3.5-family architecture distinct from Qwen3-VL. Do not infer loaders from a broad model-name substring.
- Collect only bounded current-process/OS facts and boolean discovery of specifically named executables. Do not execute those programs, scan snapshots, import heavyweight libraries, install anything, or contact the network/device/GPU.
- Keep `declared`, `observed_local`, and `unmeasured` sections separate. Do not emit an aggregate “ready” flag, pass percentage, memory-fit verdict, or training authorization.
- Reuse strict input parsing, regular-file input checks, privacy-safe diagnostics, and fresh output directories. Successful reporting means a report was produced, not that an integration works.

The exact profile schema/report and implementation plan still need to be specified and reviewed before code. This note intentionally does not define a command users should run now.

## Checks that remain separate

| Gate | Evidence still needed |
| --- | --- |
| H05 / H20 host | Approved access, exact GPU/partition, available memory/storage, driver/software compatibility, and measurements |
| Model snapshot | Approved local files, immutable identity, processor/template hashes, a tested dependency lock, local-only loading, and measured inference memory/latency |
| H04/H07 / controller | Approved device, installed SDK behavior, capture timing/resolution, coordinate calibration, action completion, and supervised stop behavior |
| H02/H03 / data | Approved originals, actual media timestamps, causal windows, label evidence and review |
| Native media parser | Trusted executable/build and separately specified parser, timestamp, output, and extraction limits |
| Actual training | A later explicit owner decision; no setup/preflight result overrides the current deferral |

Executable presence cannot populate GPU/device measurements. A successful byte inventory cannot populate video/label/model checks. A valid model ID or syntactically pinned revision cannot establish runtime compatibility.

## Source and test discipline

Use the already pinned [model/hardware notes](model-and-hardware-notes.md) and [MaaFramework contract](maaframework-integration-notes.md) as research declarations. Transformers v5.16.1 is an interface reference in those notes, not a tested dependency lock. Fresh primary-source verification is needed when selecting a real lock, changing revisions, or implementing a native interface. The delegated preflight web checks returned no source content, so they provide no new external verification.

Essential acceptance tests for a later implementation: exact profile schema/types and immutable revisions; both known model tuples and wrong-loader cases; unknown revisions kept unreviewed; pure detached validation; absent/present executables that never become measured hardware; no optional imports/subprocess/network/media access; bounded regular-file JSON input; non-overwriting output and failure privacy; installed-wheel operation; all existing commands unchanged. Synthetic tests establish the software boundary, not external readiness.
