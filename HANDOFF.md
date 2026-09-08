# Project handoff — read before continuing

Snapshot updated: **2026-09-08**. This file is the starting point for another
Codex session, including an IDE session with no access to the old conversation.
It records project facts and the next work, not a transferable running session.

## Mission and current owner direction

Build `Alberssssss/arknights-vision-agent` toward an Arknights Integrated
Strategies player: image/video observations, state and history, a decision
policy, validated actions, a bounded controller, fresh-observation verification,
reviewed demonstration data, and honest offline/live evaluation.

The owner approved continuing independent offline development while human
dependencies wait. **Actual training is explicitly deferred:** do not start
pretraining, fine-tuning, optimizer steps, or paid compute. Do not access private
recordings, a GPU host, credentials, or a game/device without the corresponding
owner involvement. A configuration report is not permission to do those things.

The initial scope is setup and training-data preparation, not a promise of a
trained model or successful game clears. Keep the full project goal open. Use
Chinese for user-facing progress updates.

## First actions in a fresh session

1. Read [AGENTS.md](AGENTS.md), [STATUS.md](STATUS.md), and
   [HUMAN_HELP.md](HUMAN_HELP.md). Then use the
   [continuation guide](docs/continuation-guide.md) to inspect the actual branch,
   working changes, and local environment.
2. Run the offline baseline before implementation. Preserve unrelated changes.
   Do not install a model/controller stack just to run the standard-library core.
3. Locate the first unfinished item below. Read its entire current specification
   and implementation plan; use current evidence rather than an old plan's
   unchecked boxes to decide what remains.
4. Keep owner-dependent items parked and continue the next independent task.
   Do not silently replace missing real data or measurements with synthetic proof.

The active development line at this handoff is `codex/offline-foundation`.
The reviewed portable-handoff checkpoint `bb15e44` was published to both that
branch and the default `main` entry on 2026-09-08. A subsequent remote lookup
confirmed both refs and the default branch. Verify actual refs after cloning;
a handoff document cannot attest to future branch state. Never reset an existing
dirty checkout to match it.

A genuine GitHub clone without a branch argument selected `main` at that
checkpoint and passed the source baseline, developer-helper suite and all four
synthetic CLI examples. This was a new checkout on the same Mac, not a newly
launched Codex/VS Code client or a test on another operating system or GPU host.
See the dated publication evidence in [STATUS.md](STATUS.md).

## What is already implemented

The application code through `4fbcafac3fdab72401bd497ac30dbfca38b3caab` has been
reviewed; its setup-preflight closeout is recorded by documentation commit
`a8eb449`. Later documentation changes do not imply a new model/runtime result.
See [STATUS.md](STATUS.md) for full commits and exact evidence.

| Boundary | Implemented behavior | What it does not establish |
| --- | --- | --- |
| Actions | Strict observation/run-bound `select`, bounded `wait`, and `stop` | Vision, battle deployment/skills, or live execution |
| Replay | Deterministic dry-run outcomes, event logs and summaries | An interactive simulator or alternate future game states |
| Demonstration manifest | Strict declarations, clocks, label origin and review metadata | Correct labels, permission verification, or media inspection |
| Preparation | Eligibility reasons and stable whole-group partitions | A decoded/exported training dataset |
| Byte inventory | Explicit local-file selection, bounded byte hashing and exact duplicate candidates | Video validity, near-duplicate detection, or timing alignment |
| Setup preflight | Fixed research comparison and limited current-host facts | A dependency lock, GPU/model readiness, inference, or training |
| Developer-only media experiment | Local CPU build and measured 12-frame H.264 presentation timing | A product index/extractor, native parser sandbox, or real-data readiness |

The latest application baseline contains **307 tests**, verified on CPython
3.13.7/macOS arm64. Source-selected CLI tests and genuine installed-package
checks are distinct evidence; do not describe all tests as installed CLI tests.
Python 3.11/3.12, native Windows, Linux/H20, real media, and real-game behavior
still require their own checks.

The developer-only process helper is retained in
[`tools/media_runtime`](tools/media_runtime/README.md), now with 12 real-process
tests. The three close-failure regressions were retained on 2026-09-08 at
reviewed checkpoint `5e5abf8`; the runner itself and application code did not
change. It bounds trusted local experiment commands; it is not a product
decoder or a containment guarantee for arbitrary child processes.

## First unfinished work and continuation order

### 1. Review the native-index proposal (H08), then specify and implement it

The local CPU build and narrow synthetic calibration have finished. The
[runtime receipt](docs/media-runtime-calibration.md) retains actual identities,
features, dynamic linkage, warnings, the necessary pkgconf correction and the
12-frame timing table. No experiment command remains active at this snapshot.
Do not repeat the identical experiment merely because the historical plan has
unchecked boxes. Recheck artifacts before using them on the original host; a
fresh clone has no decoder binary and must rebuild/revalidate its local runtime
before native execution. The receipt is not a transferable running environment.

The source-informed [native-index proposal](docs/native-index-proposal.md) now
records alternatives, the recommended narrow subprocess boundary, exact-source
pitfalls and proposed acceptance work. **H08 awaits the owner's design-scope
confirmation** under the brainstorming review workflow. The proposal is not an
implemented API, approved native invocation or permission to use real data.

The complete native-index product specification, implementation plan and API
**do not exist yet**. After H08, the concrete next action is to finalize and
independently review that specification and file-by-file plan, using the
[media preparation notes](docs/media-preparation-notes.md),
[runtime design](docs/superpowers/specs/2026-09-07-media-runtime-design.md),
[runtime plan](docs/superpowers/plans/2026-09-07-media-runtime.md), and
[byte-inventory contract](docs/superpowers/specs/2026-09-07-byte-inventory-design.md).
Then add failing acceptance tests before product implementation. Do not treat
the proposed flags/limits as execution-tested, or the source review as clean-EOF,
orientation or causal-extraction evidence. The already planned helper regression
follow-up was completed while this new design decision waited; do not redo it
as a substitute for resolving the next boundary.

Define trusted executable identity, explicit selected local input, stream
selection, file identity rechecks, process/output/frame/dimension limits, error
semantics, and raw timing and orientation representation. The completed
calibration does not cover negative/nonzero origins, sub-millisecond timing,
rotation, packet reordering or verified frame extraction. Keep GPU/device/model
imports out of the default path. Use only synthetic media until H02/H03 permit
real-sample work; this design work does not need those gates to be resolved.

### 2. Implement verified causal frame extraction and sample projection

Also **not implemented**. Select actual frames visible before a decision,
preserve crop/rotation/scale and coordinate transforms, and explicitly map
media and action clocks with uncertainty. Do not silently round native rational
timestamps into the v1 millisecond manifest or include future outcome frames.
Missing or ambiguous evidence stays excluded/unknown rather than fabricated.

### 3. Connect the reviewed pilot, action expansion, and offline evaluation

H02/H03 unlock real sample inspection and label review. Start with the existing
[private pilot](docs/recording-pilot.md), then extend the menu-only action schema
for battles in a separately reviewed design. Build offline policy/evaluation
interfaces and baseline reports; model execution needs approved model files and
environment access. Training remains a separate, deferred decision.

These tasks are preparation for the full
[CP0–CP10 roadmap](docs/project-roadmap.md), not a reduced definition of success.
Persistent live run state, perception/state tracking, model integration,
controller execution, recovery, and real-game evaluation remain future work.

## Decisions that must survive the handoff

- `stop` ends the agent/replay session without another game interaction. It is
  **not** pause, retreat, abandoning a run, or quitting the game.
- Keep a decision policy separate from the controller. Parse and validate a
  proposed action; never execute model text as a shell command or arbitrary input.
  A successful controller request is not proof of the observed game effect.
- MAA and MaaFramework are different systems. Their recording and execution
  limitations are in the [integration notes](docs/maaframework-integration-notes.md)
  and [collection plan](docs/training-data-collection.md). No real adapter is
  implemented or tested yet.
- Preserve the owner's `Qwen3.8-27B` and H20/141 GB descriptions; do not
  automatically correct them to another model or H200. The
  [model/hardware research snapshot](docs/model-and-hardware-notes.md) records
  fixed candidate identities and architecture differences, not an installed
  loader, a latest-release claim, a best-model result, or memory-fit evidence.
- Keep original media, inputs, normalized actions, review evidence, and verified
  outcomes separate. A reviewed video-inferred label remains inferred; it does
  not become an original input log. Entire related runs/recordings stay together
  when splitting data. Include mistakes and recovery as well as successful play.
- Synthetic fixtures test software contracts only. They are not gameplay
  demonstrations, eligible real training data, or evidence of model/game quality.
- No repository license has been selected; H06 remains open. Do not choose one
  or claim a reuse policy merely because a candidate model has license metadata.

## Human dependencies and what does not transfer

H01–H08 are tracked in [HUMAN_HELP.md](HUMAN_HELP.md): target scope, private
recordings, label review, limited device testing, H20 access, license choice, and
supervised live evaluation, plus confirmation of the next native-index proposal.
Do not put credentials or recordings in that public queue. H05 access and H08
design confirmation do not authorize CP7 training or other separate access gates.

Git transfers the code, these documents, synthetic examples, and committed
tests. It does not transfer the old Codex goal/scheduler, chat window, model
settings, subagent sessions, permissions, machine configuration, virtual
environments, source downloads, decoder binaries, raw reports, recordings, or
weights. The old `work/...` locations in evidence are historical provenance,
not paths that a new machine can use.

After each meaningful step, update this file's next action, record exact evidence
in `STATUS.md`, and update the human queue when relevant. Publication must be
verified from actual remote state. Keep unverified or unfinished work explicit.
