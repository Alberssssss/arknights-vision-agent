# Offline foundation design

## Basis and scope

The owner approved autonomous continuation of the previously discussed layered design on 2026-09-07, with human-dependent questions parked while independent work continues. This document selects the reversible offline portion as the first milestone. It does not approve live gameplay, paid compute, device access, or an unbounded training run.

The broader system has observation, state, policy, execution, training, and evaluation components. This first milestone establishes the boundary between observations and proposed actions, then exercises it with explicitly synthetic input. It is not a game simulator and is not a vision model.

## Alternatives considered

1. Start with a full learned controller. Rejected for the first milestone: no real input logs, target scope, device, or GPU connection is available yet.
2. Start by modifying all of MAA's Roguelike decision logic. Deferred: this introduces integration assumptions before a small contract can be tested.
3. Start with an offline action boundary and replay harness. Selected: it is testable now and supports later real-controller and model integrations without pretending those integrations already work.

## Contract

The offline core is standard-library Python 3.11+.

An observation contains exactly these fields:

- `run_id`: non-empty identifier, at most 128 characters.
- `observation_id`: non-empty identifier, at most 128 characters.
- `screen`: one of `recruitment`, `route`, `event`, `unknown`, or `terminal`.
- `available_options`: an ordered list of unique, non-empty option identifiers.
- `captured_at_ms`: a non-negative integer; booleans are not integers for this schema.
- `source`: `synthetic`, `recorded`, or `live`. Provenance is preserved, not inferred.

An action contains `run_id`, `observation_id`, and `kind`. `select` additionally requires only `option_id`; `wait` additionally requires only `wait_ms`; `stop` has no additional fields. Unknown fields and action kinds are rejected. Wait durations are integers from 1 to 10,000 ms. Selection is valid only on a known supported menu and for an available option. Terminal screens permit only stop; unknown screens permit only wait or stop.

Actions are bound to the observation and run that produced them. For select/wait, a guard rejects mismatched identifiers, future-dated observations, or observations older than a supplied age limit. A stop request may terminate even on a stale or future observation, but must still match run and observation identifiers and pass schema and clock-type checks. This exception permits fail-closed stopping, not a game interaction. The caller supplies `now_ms`, so an offline replay never treats wall-clock time as a recorded timestamp.

JSON parsing is bounded, rejects duplicate keys and non-standard numeric constants, and does not execute model-generated text. Invalid input raises a project-specific validation error with a useful diagnostic, not a guessed action.

## Replay semantics

The subsequent replay module will feed recorded contexts and proposed actions through the same guard. It will never connect to a model service or a controller. A validated action in replay is marked `allowed_dry_run`, not `executed` or `game_success`. Invalid actions are logged as blocked and cause fail-closed termination of that trace. Waiting does not sleep in replay.

A replay fixture is not an interactive environment: an action cannot generate a new game state. Logs and documentation must retain this distinction. Synthetic success means only that the fixture exercised the software contract.

## Data and publication boundaries

No game assets, recordings, trained weights, credentials, local connection details, or personal email addresses are included. Generic synthetic menu examples are allowed. The code and documentation can be published to the development branch after review. User-dependent inputs remain in a public, non-sensitive queue.

## Acceptance criteria for this milestone

1. Invalid, ambiguous, stale, cross-run, and unsupported actions are rejected by automated tests.
2. A known synthetic trace can be processed through the guard and a dry-run controller without external connections.
3. Every attempted action has a structured outcome, and software completion is never represented as a real game clear.
4. Output files are not silently overwritten.
5. The package can be run and tested without GPU access or heavyweight model dependencies.
6. Independent specification and code-quality reviews have no unresolved important findings.

## Human review queue

Target game conditions, real recordings, annotation review, controller access, GPU access, and supervised evaluation are explicitly deferred in `HUMAN_HELP.md`. Development may continue on the offline contract while the owner reviews this document asynchronously.
