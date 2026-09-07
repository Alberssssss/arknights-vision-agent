# Replay Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exercise the reviewed action boundary against a deterministic synthetic trace and produce honest, inspectable dry-run outcomes.

**Architecture:** A pure replay function consumes a parsed trace and uses the shared action guard. A small command-line layer reads one bounded JSON file and writes events plus a summary into a newly created output directory. There is no simulator, policy model, live controller, device connection, or wall-clock waiting.

**Tech Stack:** Python 3.11+ standard library and `unittest`.

---

## Prerequisite

- [ ] Complete specification and code-quality review of the action-boundary task. Import its `ActionValidationError`, `parse_action`, and `validate_action` APIs without duplicating their rules.

## Task 1: Pure replay and results

**Files:** Create `src/arknights_vision_agent/replay.py` and `tests/test_replay.py`.

Trace schema is a plain object with exactly `schema_version`, `run_id`, `source`, and `steps`. `schema_version` is integer 1, `source` is synthetic or recorded, and `steps` is a non-empty list of at most 1000 entries. Each entry has exactly `observation`, `action_json`, and `decision_at_ms`. Its observation follows the action-boundary schema; its run and source must match the trace. Observation IDs are unique within the trace. Capture and decision timestamps must not move backward across steps. Reject malformed traces before producing successful results. Invalid proposed actions instead produce an explicit blocked event and terminate processing; they are not silently dropped.

Expose `ReplayValidationError(ValueError)` for trace-structure failures. Require plain dictionaries/lists, exact integers rather than booleans, and string `action_json` values. Validate the entire trace structure and all observation schemas before processing actions, including steps after an eventual stop. Reuse the shared action guard to validate observations (a schema-valid matching stop proposal can serve this purpose); do not copy its identifier, screen, option, or time validation rules. Trace IDs have the same identifier requirements as observation IDs.

Public function: `replay_trace(trace: dict) -> dict`. The result has `schema_version: 1`, `mode: "dry_run"`, `source`, `run_id`, `events`, and `summary`. Each event records the one-based step index, observation ID, proposed action or parse error, and `status` equal to `allowed_dry_run`, `stopped`, or `blocked`. Include a readable error for blocked actions but do not log arbitrary oversized input verbatim. All events include `executed: false`. A stop terminates the trace. There are no events for skipped later steps.

The summary contains `steps_available`, `steps_processed`, `allowed_actions`, `blocked_actions`, `stopped`, `trace_exhausted`, `game_clear_verified: false`, and `mode: "dry_run"`. Report completion only with this precise replay vocabulary; never expose a generic `success: true` that could be mistaken for gameplay success.

`allowed_actions` counts only `allowed_dry_run` events, not stop. `steps_processed` counts every emitted event, including a blocked or stopped event. `trace_exhausted` means the event count equals `steps_available`, even when the final available step stops or is blocked; it is not a correctness or gameplay result. Do not mutate the trace or return mutable references to its nested objects.

- [ ] Write tests first. A valid sample is:

```python
trace = {
    "schema_version": 1, "run_id": "demo", "source": "synthetic",
    "steps": [{
        "observation": {
            "run_id": "demo", "observation_id": "frame-1",
            "screen": "recruitment", "available_options": ["option-a"],
            "captured_at_ms": 1000, "source": "synthetic",
        },
        "action_json": '{"run_id":"demo","observation_id":"frame-1",'
                       '"kind":"select","option_id":"option-a"}',
        "decision_at_ms": 1100,
    }],
}
result = replay_trace(trace)
assert result["events"][0]["status"] == "allowed_dry_run"
assert result["events"][0]["executed"] is False
assert result["summary"]["game_clear_verified"] is False
```

- [ ] Observe an initial failing test, then implement the valid path.
- [ ] Add failing cases before implementing rejection for schema/version/source errors, mismatched provenance, duplicate observation IDs, backward clocks, excessive or empty steps, and wrong data types.
- [ ] Add tests that stale/invalid actions yield a blocked event, halt before later actions, and never report game success; test stop short-circuiting and non-mutation.
- [ ] Verify `PYTHONPATH=src python3 -m unittest discover -s tests -v` and `python3 -m compileall -q src tests`.
- [ ] Complete specification then code-quality reviews and commit `feat: add deterministic dry-run replay`.

## Task 2: CLI, synthetic example, and documentation

**Files:** Create `src/arknights_vision_agent/__main__.py`, `src/arknights_vision_agent/cli.py`, `tests/test_cli.py`, and `examples/synthetic_recruitment.json`. Update README and packaging metadata only as needed for the documented CLI.

Command:

```sh
PYTHONPATH=src python3 -m arknights_vision_agent replay \
  --trace examples/synthetic_recruitment.json --output work/demo-run
```

The trace file is limited to 2 MiB. Parse strict JSON without duplicate keys or NaN/Infinity and reject unexpected shapes through `replay_trace`. Catch validation and filesystem failures and print a concise diagnostic to stderr with a nonzero exit code. Existing output directories must be rejected without modifying them; do not provide a force-overwrite option in this milestone. The command creates a new directory and writes `events.jsonl` plus `summary.json`. Render JSON with standard finite values only. A blocked action exits nonzero while retaining the diagnostic report. Valid dry-run output prints its path and explicitly says no game or device was controlled.

The synthetic example contains generic choices only: one valid recruitment selection, one bounded wait on an unknown screen, and one terminal stop, with unique observation IDs and increasing timestamps. Do not include Arknights screenshots, real operator strategy claims, or a claim that a learned model supplied the decisions.

- [ ] Write subprocess-based CLI tests using temporary directories: help, valid trace, malformed JSON, blocked action, missing file, oversized file, existing output with sentinel preservation, and invalid output parent.
- [ ] Observe red, implement the smallest parser/entrypoint/output code, and verify green. Tests must run the actual module, not mock the CLI.
- [ ] Run the documented demo in a fresh ignored output directory, inspect both files, and confirm `executed` and `game_clear_verified` are false.
- [ ] Check the README accurately describes replay versus a simulator/live player and links the human-help queue.
- [ ] Complete specification then quality review; commit `feat: add offline replay CLI and synthetic demo`.

## Milestone acceptance

- [ ] All tests pass, the demo works in a clean environment without MaaFramework/model packages, and the output vocabulary remains explicit.
- [ ] The coordinator updates `STATUS.md` with exact commands/counts and publishes only reviewed commits.
- [ ] The overall project goal remains active; the offline demonstration does not close the human-dependent validation requirements.
