# Project roadmap and checkpoints

Recorded from the owner's project outline on 2026-09-07. Checkpoints require
evidence; they are not completion percentages. Current detailed evidence lives
in [STATUS.md](../STATUS.md), and the immediate next task in
[HANDOFF.md](../HANDOFF.md).

## Intended system

Screen/recent video and run history → perception/state → decision policy →
strict action validation → execution adapter → fresh observation and outcome
verification → next decision.

Develop slower menu/route/recruitment decisions and time-sensitive battle
operations as distinct, measurable parts. Preserve logs and eventually persistent
run state so restarts, stale observations, uncertainty, and recovery can be
handled explicitly. The current offline replay is not that live system.

## Checkpoints

| ID | Deliverable | Acceptance evidence | Current boundary / human gate |
| --- | --- | --- | --- |
| CP0 | First theme, difficulty, ending, roster and evaluation agreement | Written scope, baseline, intervention rules and success criteria | Awaiting H01; do not invent the target |
| CP1 | Offline action guard, replay and audit logs | Strict rejection cases, deterministic synthetic dry run, installed checks and independent reviews | Implemented for menu selection, wait and agent stop only |
| CP2 | Private asset intake and provenance | Selected originals inventoried; source/use scope, editing, input logs, privacy and related versions recorded | Byte inventory and metadata tooling implemented; real intake awaits H02 |
| CP3 | Native timing index and causal frame preparation | Reviewed runtime; measured synthetic timing/orientation; actual returned frame identities; clock/coordinate alignment; approved real-sample check | Local CPU build and narrow synthetic timing measured; orientation and product indexing/extraction not implemented |
| CP4 | Complete action/annotation contract | Reviewable menu and later battle actions; input-request/controller-result/game-effect distinctions; accepted evidence with origin and uncertainty preserved | Initial menu schema/review metadata only; real review H03 |
| CP5 | Reproducible model/runtime setup | Pinned files/processor/template/dependencies and actual bounded image/video inference memory/latency on the target | Configuration report implemented; actual model/H20 work awaits H05 |
| CP6 | Frozen offline evaluation and unchanged baseline | Whole-group held-out data; per-scene action quality, validity, refusal, coverage, latency and failure reports | Tooling/real model evaluation remain; real results need CP2–CP5 |
| CP7 | Controlled training and comparison | Separate launch decision and budget; verified supervision/trainable modules; measured optimizer-step memory; held-out improvement versus unchanged baseline | **PAUSED by owner. No weight updates or paid job.** |
| CP8 | Gated real controller | Approved device; capture/coordinate calibration; one action at a time; bounded uncertain-outcome stop; fresh observation confirms effects | Offline adapter tests may proceed; real access H04 |
| CP9 | Progressive game loop | Menu → one battle → one floor → complete target run, with persistent state, logs, verified outcomes and counted interventions | Later; fixed supervised batch requires H07 |
| CP10 | Reliability acceptance | Predeclared conditions, trial count and thresholds; all attempts counted; baseline comparison, uncertainty, interventions, failures and long-run stability | Later; a single clear is not stable automatic play |

## CP3 sub-checkpoints

1. Process/resource cleanup under failure, timeout and output limits.
2. Local CPU build identity, actual features and linkage.
3. Synthetic calibration: real presentation timestamps, variable intervals,
   reordered decoding, nonzero origins and orientation cases as separately tested.
4. A specified native index with input/stream/timestamp provenance and limits.
5. Verified extraction, clock uncertainty and recorded pixel-space transforms.
6. H02/H03 approved real-sample review.

Do not promote source checksums to build evidence, a build to timing evidence,
or timing evidence to a training-ready dataset. The first runtime experiment
tested a narrow H.264/MOV case, not every case needed by the later media pipeline.
Its [receipt](media-runtime-calibration.md) records the completed local build,
variable presentation intervals and observed B pictures. It did not test
packet-level reordering, nonzero/negative origins, sub-millisecond timing or
orientation. CP3 remains incomplete; specifying the product index is next.

## Data acquisition and pilot

Prefer owner-supplied human play with synchronized inputs. An approved,
instrumented automation baseline is another source, with requested inputs,
controller responses and observed outcomes retained separately. Existing videos
the owner is entitled to use may supply candidate labels, but inferred actions
need review. Public visibility alone is not an import/republication decision;
do not bulk-download videos automatically.

Start with three to five short menu-decision segments and one unchanged complete
run if already available. This tests intake and annotation, not whether a model
has enough training data. Later expand actual coverage across conditions,
mistakes, failed attempts, recovery and human corrections. Preserve original
recordings privately; keep related runs/edits in the same data partition.

The actionable handoff is [recording-pilot.md](recording-pilot.md); the detailed
collection and annotation rules are [training-data-collection.md](training-data-collection.md).

## Dependency and evaluation rules

- Model/runtime preparation, data preparation and offline controller tests can
  advance in parallel where independent. CP7 being paused does not block them.
- An offline action agreement score is not a game clear rate. Replay cannot
  produce counterfactual game states, so it is not a reinforcement-learning
  environment or evidence of recovery under a different action sequence.
- When using a hybrid policy, report which actions came from the model versus
  rules/baseline automation. Do not credit every result to the learned model.
- Count human intervention, timeout, unsupported states and abandoned attempts
  according to predeclared rules. Do not hide them by changing the denominator.
- H06 affects an explicit release/reuse policy, not permission to continue
  independent offline development. Do not silently license the project.
