# Training-data collection plan

Status: preparation only. Actual collection from a game/device requires the owner's approved environment; model training is explicitly deferred. No recording, controller, inference, or training job is started by this document.

## Recommended sources, in order

1. **Owner-recorded human play with synchronized inputs.** Preserve unedited video, timestamps, and the original input events. Add a small amount of human review to map those inputs to meaningful game decisions. This is the preferred pilot because the owner can explain ambiguous actions and recording conditions.
2. **Owner-approved, instrumented baseline automation.** Keep the baseline's decisions, low-level input requests, completion reports, screenshots, and observed outcomes separate. Use it to collect repeatable trajectories and compare later policies, not as an unquestioned expert. A real run is a later authorized device operation.
3. **Existing recordings the owner is entitled to use.** Treat video-derived actions as inferred until reviewed. Keep the original source identity and known edits. Do not bulk-download public videos or assume that public visibility establishes permission to use or republish them.

The first goal is a small, inspectable pilot, not a large video archive. For example, begin with a few short menu-decision segments and a complete run if available. These are workflow tests, not a claim that this quantity is enough to train a useful agent.

The [private pilot handoff](recording-pilot.md) gives a suggested packet layout, a file-selection example, and an intake/review worksheet. Missing inputs or clock information can remain unknown; do not manufacture logs or precise timestamps to fill the packet.

## What the existing automation tools actually provide

Primary-source inspection on 2026-09-07 used MaaFramework v5.12.3 (`0c3f6454902b8ff9f7697cc6b09a7a935a41cdbb`) and MAA v6.17.2 (`e523b2038c6790f5f45d95c2e1de84c3450cc357`). No SDK was run against a device.

MaaFramework's `RecordController` records operations forwarded through that controller, not arbitrary human inputs elsewhere. Its JSONL carries low-level parameters, reported success, a start timestamp, and duration; requested successful screenshots are saved as images. The start clock is monotonic elapsed milliseconds since recorder construction. It does not automatically provide continuous video, media-clock alignment, or semantic game labels. Its log file is opened with truncation, so a future integration must allocate a fresh session directory and never reuse a previous log path.

Sources: [recorder implementation](https://github.com/MaaXYZ/MaaFramework/blob/0c3f6454902b8ff9f7697cc6b09a7a935a41cdbb/source/MaaRecordControlUnit/RecordController.cpp), [record types](https://github.com/MaaXYZ/MaaFramework/blob/0c3f6454902b8ff9f7697cc6b09a7a935a41cdbb/include/MaaControlUnit/RecordTypes.h).

The recording wrapper operates around the underlying control unit and creates a new outer controller agent. Recorded raw coordinates and images therefore must not be blindly paired with resized observations from the outer controller. The integration must explicitly configure scaling and retain both coordinate spaces and their transform.

Sources: [wrapper construction](https://github.com/MaaXYZ/MaaFramework/blob/0c3f6454902b8ff9f7697cc6b09a7a935a41cdbb/source/MaaFramework/API/MaaFramework.cpp), [controller coordinate conversion](https://github.com/MaaXYZ/MaaFramework/blob/0c3f6454902b8ff9f7697cc6b09a7a935a41cdbb/source/MaaFramework/Controller/ControllerAgent.cpp).

MAA has useful partial semantic evidence, including recruitment selection logs. This is not a complete, synchronized training demonstration. In particular, `RoguelikeCombatEnd` is emitted for both successful and unsuccessful combat; it must not be used as a win label. MaaFramework action details likewise report controller results, not proof of a game objective.

Sources: [MAA recruitment selection](https://github.com/MaaAssistantArknights/MaaAssistantArknights/blob/e523b2038c6790f5f45d95c2e1de84c3450cc357/src/MaaCore/Task/Roguelike/RoguelikeRecruitTaskPlugin.cpp), [MAA combat-end behavior](https://github.com/MaaAssistantArknights/MaaAssistantArknights/blob/e523b2038c6790f5f45d95c2e1de84c3450cc357/src/MaaCore/Task/Roguelike/RoguelikeBattleTaskPlugin.cpp), [MaaFramework action details](https://github.com/MaaXYZ/MaaFramework/blob/0c3f6454902b8ff9f7697cc6b09a7a935a41cdbb/docs/en_us/2.2-IntegratedInterfaceOverview.md).

MAA's `VideoRecognition` is documented for combat video and can infer copilot deployment, retreat, and skill actions. Recognition failures and ambiguous changes remain possible. It is a candidate label-proposal aid, not recovery of authoritative original inputs or demonstrated coverage of complete Integrated Strategies menu decisions. Its battle labels do not yet fit this project's initial menu-only action schema.

Sources: [integration task documentation](https://github.com/MaaAssistantArknights/MaaAssistantArknights/blob/e523b2038c6790f5f45d95c2e1de84c3450cc357/docs/en-us/protocol/integration.md), [video-recognition implementation](https://github.com/MaaAssistantArknights/MaaAssistantArknights/blob/e523b2038c6790f5f45d95c2e1de84c3450cc357/src/MaaCore/Task/Experiment/CombatRecordRecognitionTask.cpp).

MAA and MaaFramework are distinct systems. The existence of MaaFramework's recorder does not mean it transparently records all operations from an unchanged MAA process. Integration and alignment require their own tests on an approved environment.

## What to retain per session

- An opaque session/run ID, source recording ID, and leakage-group ID for related recordings or edits.
- Declared theme, difficulty, intended ending, roster context, client language, game version if known, and capture settings. Unknown context stays explicitly unknown.
- Original media in private storage, with an integrity hash after import and its frame timestamps/time base. Preserve the original resolution and any known crop or scaling transform.
- Input events on a documented clock: input/request ID, event type, coordinates or other parameters, start time, completion time, and reported status. These describe input requests or recorded inputs, not guaranteed game effects.
- A mapping between input, capture, and video clocks. Include uncertainty and discontinuities; do not pretend an edited video has a single exact clock offset.
- Human label evidence and review references. Keep pending/rejected labels and their reasons outside the eligible export.
- A separately reviewed outcome such as clear, loss, abandonment, or unknown. Outcome information may be used in analysis but must not leak future frames into a decision's input.

Video alone, raw inputs, normalized action labels, and verified outcomes are different layers. The data pipeline should preserve each layer instead of collapsing them into a single success label.

## Processing stages

```text
Private original media and event logs
                 |
                 v
Inventory, integrity hashes, and clock/coordinate alignment
                 |
                 v
Causal observation windows and candidate action labels
                 |
                 v
Human review, provenance, and metadata validation
                 |
                 v
Whole-group partitioning and eligibility report
                 |
                 v
Model-specific export and offline evaluation preparation
```

There is no training step in the current phase. Existing replay fixtures test the software contract only; they are not real training demonstrations.

## Label review checklist

For each candidate decision, check:

1. Do the input frames end before the action starts, using a documented clock mapping?
2. Does the label match the actual visible option or input, including coordinate transforms?
3. Are relevant options and prior context visible? If not, mark the sample ambiguous rather than inventing a target.
4. Was the input only requested, acknowledged by the controller, or confirmed by a later observation? Preserve those distinctions.
5. Does the normalized action fit the current schema? Battle deployments and skills are outside the first menu-only schema and need their own extension.
6. Does the label have an evidence ID and an accepted review reference? Acceptance is declared metadata until the reviewer and evidence are actually checked.

Maintain the original label origin after review: a reviewed inferred action remains `inferred`, not `input_log`. Corrected labels should retain their previous version and correction reason in the later review workflow.

## Coverage and evaluation

Collect a mixture of successful decisions, mistakes, recovery, failed runs, and human corrections when the owner can supply them. Report the coverage actually present: menu type, stage, difficulty, roster conditions, action kind, and source/review status. Do not fill missing coverage with synthetic data and then count it as real gameplay evidence.

Keep all frames from a run or source recording in one partition; keep related recordings together using leakage groups. Do not randomly split neighboring frames. Report empty evaluation partitions honestly. Final gameplay clear rates require a later, approved live evaluation; offline action agreement does not establish a clear rate.

## Privacy and import limits

Keep raw recordings, extracted frames, event logs, and datasets out of this public repository. Its ignore rules help prevent accidental commits but are not secure storage. Inspect recordings for account identifiers, chat overlays, notifications, and other unrelated personal material before sharing. Do not place passwords, tokens, or connection details in manifests.

The implemented manifest validator checks declarations and lexical paths only. It does not establish data-use rights, resolve symlinks, inspect real media, verify label truth, or claim that a sample is ready for training. See [the exact v1 manifest contract](superpowers/specs/2026-09-07-demonstration-manifest-design.md) for the boundary. The implemented [metadata eligibility/group report](superpowers/specs/2026-09-07-preparation-report-design.md) and non-overwriting `prepare` command retain that distinction; actual media preparation is still future work, informed by [the video-input research](media-preparation-notes.md).

## Owner input that unlocks the pilot

- H01: choose the first theme/difficulty/ending and representative roster.
- H02: supply a small private recording sample and state whether it is edited or has input logs.
- H03: review a handful of aligned candidate labels once they exist.
- H04: provide environment details and approval before any instrumented capture/control test.

GPU access and actual training can wait while these preparation tools are completed.
