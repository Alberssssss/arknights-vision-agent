# Arknights Vision Agent

An offline-first research project toward an Arknights Integrated Strategies agent using image/video models, imitation learning, and a validated game-control interface.

**This is not a finished game-playing bot.** No model training, real-device control, or game clear has been demonstrated by this repository. See [STATUS.md](STATUS.md) for checks actually completed and [HUMAN_HELP.md](HUMAN_HELP.md) for items awaiting the owner.

The current phase is setup and training-data preparation. The owner has explicitly deferred actual training; no pretraining or fine-tuning job should start automatically.

## Continue this project in another Codex session

Open this repository's root and start with [AGENTS.md](AGENTS.md),
[HANDOFF.md](HANDOFF.md), [STATUS.md](STATUS.md), and
[HUMAN_HELP.md](HUMAN_HELP.md). The [fresh-clone/IDE continuation guide](docs/continuation-guide.md)
contains baseline checks, portable development/review steps, and local-runtime
rebuild boundaries; the [CP0–CP10 roadmap](docs/project-roadmap.md) keeps the full
project objective and acceptance gates visible.

The next video-processing increment is described in the
[native-index proposal](docs/native-index-proposal.md), awaiting H08 design-scope
confirmation. It is not yet a native-indexing or frame-extraction capability.

This handoff is stored in Git, so development does not require the old chat.
Codex desktop sessions/goals, credentials, private material, ignored build products
and machine configuration do not transfer with a clone. Recheck actual branch
and environment state; do not infer H20/model/game readiness from the documents.

## Intended system

```text
Screen and recent history
          |
          v
State tracking and a decision policy
          |
          v
Strict action validation
          |
          v
Replay/dry-run first; gated real execution later
          |
          v
Fresh observation, verification, and an audit log
```

The development assistant builds and tests the system. A future deployed policy and controller would play the game; the coding assistant is not implicitly part of that runtime.

## First milestone

The current development branch is `codex/offline-foundation`. The reviewed offline foundation includes:

1. An observation-bound action contract that rejects malformed, unknown, stale, cross-run, and unavailable actions.
2. A deterministic replay harness with explicit dry-run outcomes.
3. A small synthetic example, command-line runner, and machine-readable logs.
4. Independent reviews and automated regression tests.

The initial action vocabulary is deliberately limited to selecting a known menu option, bounded waiting, and stopping. Battle deployment, skills, recruitment quality, vision/OCR, model inference, and live device operations are not implied by this vocabulary.

Synthetic fixtures exercise software contracts. They are neither gameplay demonstrations nor evidence that a model can win. A replay is also not a simulator: selecting a different action does not generate an alternate game state.

## Offline replay demo

From the repository root, run the committed generic synthetic trace into a fresh output path:

```sh
PYTHONPATH=src python3 -m arknights_vision_agent replay \
  --trace examples/synthetic_recruitment.json --output work/demo-run
```

This dry run validates recorded observations and proposed action text; it is not a simulator or a live player. It does not wait in real time, generate new game states, contact a model service, or control a game or device. It requires no GPU, model weights, controller dependency, MaaFramework installation, or network access.

The command creates `events.jsonl`, with one attempted action per line, and `summary.json`, with dry-run counts and `game_clear_verified: false`. A blocked action is retained in those reports and makes the command exit nonzero. The command will not overwrite an existing output directory, file, or symbolic link, and it has no force option; choose a new output path for each run.

## Metadata preparation demo

The local implementation can validate a demonstration manifest and write an offline metadata-eligibility and leakage-group split report:

```sh
PYTHONPATH=src python3 -m arknights_vision_agent prepare \
  --manifest examples/synthetic_demonstrations.json \
  --output work/preparation-demo
```

The command creates one `preparation.json` file. It is metadata-only: no media is inspected and no training is started. The public fixture contains no actual media, and all three records are excluded from eligibility because they are synthetic and/or lack accepted, permission-attested labels. Its referenced paths are declarations only.

Choose a fresh output path for every run. The command will not overwrite an existing directory, file, or symbolic link and has no force option. A custom deterministic split can be requested, for example:

```sh
PYTHONPATH=src python3 -m arknights_vision_agent prepare \
  --manifest examples/synthetic_demonstrations.json \
  --output work/preparation-seed-7 \
  --seed 7 --weights 8000 1000 1000
```

Split weights are approximate ratios across complete leakage groups, so small inputs may leave partitions empty. The command warns when any partition has no metadata-eligible records. The reported manifest digest covers canonicalized declarations; it is not a hash of referenced media and does not verify media, labels, reviewers, or permission claims.

See the [manifest design](docs/superpowers/specs/2026-09-07-demonstration-manifest-design.md), [preparation-report design](docs/superpowers/specs/2026-09-07-preparation-report-design.md), [training-data collection plan](docs/training-data-collection.md), and [human-help queue](HUMAN_HELP.md) for the exact boundary and remaining real-data work.

## Local byte inventory demo

Inventory an explicit selection before decoding or annotation:

```sh
PYTHONPATH=src python3 -m arknights_vision_agent inventory \
  --request examples/synthetic_inventory.json \
  --media-root examples --output work/inventory-demo
```

This writes one `inventory.json` with byte counts, SHA-256 fingerprints, and exact-byte duplicate candidates. The example contains three synthetic plain-text files, not videos; two match and the third differs. It does not demonstrate real-media quality or training eligibility.

Defaults are 1 GiB per file and 4 GiB total. Override them with integer byte counts using `--max-file-bytes` and `--max-total-bytes`. Each request selects 1..1000 assets; its strict UTF-8 JSON file is limited to 2 MiB, and media-byte reads use chunks no larger than 1 MiB. Empty files and arbitrary bytes are valid. Distinct requested hard-link paths count separately.

The reader requires POSIX descriptor-relative no-follow support. It accepts only regular files and rejects descendant symlinks. The explicitly selected media root (including a root symlink and its ancestors) and output parent are owner-trusted. Choose a new output path: existing files, directories, and live or dangling symlinks are refused before any input is read. There is no force option. Input or hashing failures create no output; a later write failure may retain newly created partial output for inspection.

Source bytes are not intentionally modified, but reading may update access time. No folders are scanned, files copied, media decoded, or training started. Size and before/after file metadata checks reject detectable changes; this is not an immutable snapshot, a hostile-filesystem sandbox, or a wall-clock timeout. Supply stable local originals; later decoding must recheck content identity.

Keep real reports private; relative names, IDs, and hashes can be sensitive, and duplicate candidates require review. Matching bytes do not detect edited/near-duplicate videos, verify rights or labels, merge leakage groups, or prove game performance. Timestamp indexing and label verification remain separate work. See the [exact byte-inventory boundary](docs/superpowers/specs/2026-09-07-byte-inventory-design.md).

## Offline setup preflight

Compare an explicit model/controller declaration with the repository's saved research snapshot and collect limited facts about the calling interpreter and host:

```sh
PYTHONPATH=src python3 -m arknights_vision_agent preflight \
  --profile examples/setup_qwen38.json --output work/setup-report
```

The command writes exactly one `preflight.json`. The examples declare only candidate contracts: the shown 27B profile or `--profile examples/setup_qwen3vl8b.json` for the 8B profile. They are not a final model/controller choice and do not enable a runtime. The research snapshot records fixed declarations, not the latest releases or tested compatibility locks. A `matches_research_snapshot` result is not ready-to-run or compatibility evidence.

Each null integration receives a `not_configured` warning, and unfamiliar model IDs/revisions or controller releases receive an `unreviewed_contract` warning. No compatibility is established. An exact known model/revision paired with the wrong architecture produces `contradicts_research_snapshot`: the diagnostic report is retained, and the command will exit 2 even when the controller also needs a warning. Other well-formed declarations exit 0 after the report is written; neither status authorizes execution. Invalid input, declarations, or local observations exit 2 without creating output parents.

Choose a fresh output path for every run. Existing files, directories, and live or dangling symlinks are refused before input is read or local facts are collected. The output parent is owner-trusted; a later write failure may retain newly created partial output. Keep real reports private: declarations and host facts may be sensitive. The selected profile must be a regular strict UTF-8/JSON file no larger than 2 MiB; an explicitly selected profile symlink is allowed. The CLI requires `O_NONBLOCK` for its regular-file input boundary. The reporting API can report absent POSIX inventory features or `uname`; the CLI does not require the other inventory features just to report their absence. Feature availability is not a tested filesystem boundary or a wall-clock timeout.

Observed values describe this command's current host, not a target H20 or its GPU memory. Executable presence is only a boolean PATH lookup for `ffmpeg`, `ffprobe`, `adb`, and `nvidia-smi`; no native tools are executed. The command does not load or download models, inspect private media, perform training or inference, contact a device, or start follow-on jobs. GPU identity/memory, model snapshots/processors, dependency compatibility, media timestamps and decoding, label quality, controller integration, and game performance still need separate, appropriately authorized checks. See the [exact setup-report boundary](docs/superpowers/specs/2026-09-07-setup-preflight-design.md) and [setup research notes](docs/setup-preflight-notes.md).

## Development

The offline core targets Python 3.11+ and uses the standard library. It must run without GPU drivers, model weights, MaaFramework, a game account, or network services.

Run the tests from the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

Tests are added before their implementation. Each task receives a specification review followed by a separate code-quality review before publication.

## Subsequent milestones

- Inventory approved real media, confirm clock alignment, and complete human review of inferred labels and corrections from failed attempts.
- Prepare baseline comparison and future fine-tuning configurations. Actual fine-tuning requires the owner's later training decision, private data, and approved GPU access.
- Add a version-pinned controller adapter behind explicit live-access gates.
- Measure real capture-to-action latency and verify actions on an approved environment.
- Evaluate complete unattended runs against an unchanged baseline under declared conditions.

The target theme, difficulty, roster, and acceptable reliability remain owner decisions. They are not guessed to manufacture a success claim.

## Human collaboration

The owner asked the development assistant to continue independent work while parking human-dependent items. [HUMAN_HELP.md](HUMAN_HELP.md) lists each item, what it unlocks, and the work that can proceed meanwhile. Responses can be supplied in the Codex conversation by item ID.

Do not put recordings, account details, connection credentials, datasets, model weights, or checkpoints in this public repository. Local material belongs in ignored private directories. Live game control and paid compute require the appropriate approval and setup.

## Project documents

- [Progress and verification](STATUS.md)
- [Human help needed](HUMAN_HELP.md)
- [Offline foundation design](docs/superpowers/specs/2026-09-07-offline-foundation-design.md)
- [Action-boundary implementation plan](docs/superpowers/plans/2026-09-07-action-boundary.md)
- [Replay implementation plan](docs/superpowers/plans/2026-09-07-replay-harness.md)
- [Staged demonstration-data contract](docs/demonstration-data-design.md)
- [Implemented v1 manifest validation](docs/superpowers/specs/2026-09-07-demonstration-manifest-design.md)
- [Training-data collection plan](docs/training-data-collection.md)
- [MaaFramework integration notes](docs/maaframework-integration-notes.md)
- [Model and hardware research snapshot](docs/model-and-hardware-notes.md)

License selection is awaiting the owner. This is an independent research project, not an official Arknights or MAA release.
