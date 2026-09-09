# Human help needed

The project remains unfinished. These items are parked, not reasons to stop independent offline work that does not depend on them. This queue does not describe an active client scheduler or running background process. Reply in the Codex task when you can help. Do not paste passwords, tokens, or private connection details into this public file.

Priority update, **2026-09-08**: the owner asked to tackle MAA/control and the
game loop first. H04's remaining environment/setup details and test scope are
still needed; H01 is also needed before a battle/full-run acceptance target
can be fixed. H08 remains a later video-design decision, not a blocker to
controller research. Training remains deferred.

Owner confirmation, **2026-09-09**: the game runs on a **Windows PC with a MuMu
Android emulator**. The exact MuMu release and existing MAA installation/
connection status are not yet known. This is owner-provided information, not
an observed connection or approval to contact the device. The next question is
whether MAA on that Windows PC already connects to MuMu successfully.

| ID | Needed from the owner | What it unlocks | Work continuing meanwhile | Status |
| --- | --- | --- | --- | --- |
| H01 | First Integrated Strategies theme, difficulty, intended ending, and representative roster | Real acceptance criteria and a relevant baseline | Generic observation/action contracts and synthetic replay | Awaiting owner |
| H02 | A small representative set of recordings you are entitled to use, stored privately; indicate whether they are edited and whether input logs exist | Dataset inspection, real perception tests, and action-label audit | Data schemas, validators, split rules, and review workflow | Awaiting owner |
| H03 | Review a small sample of proposed action labels and explain ambiguous gameplay decisions | Trustworthy supervision and correction examples | Label provenance and confidence tracking | Awaiting sample and reviewer |
| H04 | Windows PC + MuMu confirmed by the owner. Still needed: existing MAA connection status, exact MuMu/MAA versions, explicitly selected instance, client language, capture resolution, and agreed bounded connection/input-test scope | Real controller smoke tests and latency measurements | Replay backend and adapter contract tests; no device contact | Partially answered; remaining setup details and test scope await owner |
| H05 | When ready: an approved way to access the H20 machine and available storage; configure credentials privately. A training budget/launch decision belongs to the later training phase | Approved environment/model preflight; actual training remains separately deferred | Configuration validation, offline data preparation, environment documentation | Machine access awaiting owner; training deferred by owner |
| H06 | Licensing choice before a broader code release or reuse policy is announced | An explicit repository license | Development continues without inventing a license | Awaiting owner |
| H07 | Approval for a fixed, supervised live-game evaluation batch and its stop conditions | Evidence of real action execution and run completion | Offline regression tests, failure classification, reporting | Awaiting offline readiness and owner |
| H08 | Review the [native-index proposal](docs/native-index-proposal.md): narrow supervised local H.264 MP4/MOV indexing, raw timing/geometry and conservative evidence flags, synthetic inputs first | Complete the new product specification/plan, then test-first native-index implementation | Controller-first research/design and other independent work; the helper close-failure follow-up is complete | Awaiting owner design-scope confirmation; later than the newly prioritized controller track; no new data/device/training authorization |

## How to help later

Actual model training is explicitly deferred by the owner as of 2026-09-07. There is no need to arrange a training run now. For the controller-first track, first clarify whether the Windows PC already has MAA working with MuMu; then collect the exact releases and remaining H04 details without re-asking the confirmed platform/emulator. H01 supplies the gameplay target. A bounded H04 test still needs its own agreed scope; H02 remains the later private recording pilot.

For H08, read the short Chinese decision paragraph at the start of the proposal.
You can reply "H08：同意先按 A 方案做离线视频索引" or describe a change to the
scope. The detailed native invocation and interface still require their own
specification, synthetic acceptance and review; H02/H03 and other access gates
are not waived by this design decision. The new-interface brainstorming review
gate is separate from the completed helper regression follow-up.

The proposed [data-collection workflow](docs/training-data-collection.md) explains which recordings and logs will be most useful. It is preparation guidance, not a request to start unattended device operation.

For H02, the [small private pilot handoff](docs/recording-pilot.md) shows what to supply and what may remain unknown. Video-only samples are useful for an initial inspection; they are not automatically verified observation/action pairs. Keep the packet private and outside this public repository.

- Refer to an item ID in the conversation, for example: "H01: start with ...".
- Provide recordings and secrets through an appropriate private location or configured connection, not Git commits.
- The agent will update this table as items are resolved and keep other work moving.
