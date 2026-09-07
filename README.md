# Arknights Vision Agent

An offline-first research project toward an Arknights Integrated Strategies agent using image/video models, imitation learning, and a validated game-control interface.

**This is not a finished game-playing bot.** No model training, real-device control, or game clear has been demonstrated by this repository. See [STATUS.md](STATUS.md) for checks actually completed and [HUMAN_HELP.md](HUMAN_HELP.md) for items awaiting the owner.

The current phase is setup and training-data preparation. The owner has explicitly deferred actual training; no pretraining or fine-tuning job should start automatically.

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

## Development

The offline core targets Python 3.11+ and uses the standard library. It must run without GPU drivers, model weights, MaaFramework, a game account, or network services.

Run the tests from the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
```

Tests are added before their implementation. Each task receives a specification review followed by a separate code-quality review before publication.

## Subsequent milestones

- Validate demonstration records, action provenance, and splits grouped by complete run/source recording.
- Add a review workflow for inferred labels and corrections from failed attempts.
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
