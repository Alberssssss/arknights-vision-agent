# Action Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and test a strict, pure observation-to-action safety boundary for the offline prototype.

**Architecture:** A small schema/guard module validates JSON actions against an explicit observation. No filesystem, network, controller, model, or clock access occurs inside validation. Later replay and live adapters must call this shared boundary.

**Tech Stack:** Python 3.11+, standard-library `json` and `unittest`; `src/` package layout.

---

## Task 1: Strict action boundary

Completed and independently reviewed at `57bfd9f`: 56 tests passed. The steps below retain the original test-first execution checklist; all were completed, including follow-up Unicode, integer-limit, and numeric-overflow regression fixes.

**Files:**
- Create `pyproject.toml` for a package named `arknights-vision-agent`, Python >=3.11, no runtime dependencies, setuptools build backend.
- Create `src/arknights_vision_agent/__init__.py` with package version `0.1.0`.
- Create `src/arknights_vision_agent/actions.py`.
- Create `tests/test_actions.py`.

Public API:

```python
class ActionValidationError(ValueError):
    pass

def parse_action(payload: str) -> dict:
    """Parse a bounded strict JSON object; reject duplicate keys and constants."""

def validate_action(action: dict, observation: dict, *, now_ms: int,
                    max_age_ms: int = 5000) -> dict:
    """Return a validated copy of action or raise ActionValidationError."""
```

### Step 1: Write behavioral tests before implementation

- [x] Add a minimal test file. Use this complete happy-path example as the first case:

```python
import unittest

class ActionBoundaryTests(unittest.TestCase):
    def test_select_available_option(self):
        from arknights_vision_agent.actions import parse_action, validate_action
        observation = {
            "run_id": "synthetic-run", "observation_id": "frame-1",
            "screen": "recruitment", "available_options": ["option-a", "option-b"],
            "captured_at_ms": 1000, "source": "synthetic",
        }
        action = parse_action('{"run_id":"synthetic-run","observation_id":"frame-1",'
                              '"kind":"select","option_id":"option-a"}')
        result = validate_action(action, observation, now_ms=1100)
        self.assertEqual(result, action)
        self.assertIsNot(result, action)

if __name__ == "__main__":
    unittest.main()
```

- [x] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` and record the initial missing-feature failure. Once the importable module exists, add each negative case before adding the corresponding validation and observe a behavioral failure.

### Step 2: Implement the exact contract in small red/green increments

- [x] Define `ActionValidationError` as the public failure type.
- [x] Make `parse_action` require a string no larger than 16,384 UTF-8 bytes; use `json.loads` with `object_pairs_hook` that rejects repeated keys and `parse_constant` that rejects NaN/Infinity. Reject float decoding that overflows to a non-finite value so later JSON reports remain serializable. Require a top-level object. Convert expected JSON/Unicode/type failures to `ActionValidationError` without evaluating any text.
- [x] Make `validate_action` require plain dictionaries and the exact observation fields from the design. Reject missing/unknown fields, wrong types, empty/whitespace-only identifiers, identifiers over 128 characters, duplicate options, and invalid provenance or screen names.
- [x] Validate integers with `type(value) is int`, not `isinstance(value, int)`, so booleans cannot pass. `captured_at_ms`, `now_ms`, and `max_age_ms` are non-negative integers.
- [x] Require action identifiers to match the observation before accepting any action. Enforce exact fields per kind. A select action needs one available option and a recruitment/route/event screen; wait needs 1..10,000 ms and a non-terminal screen; stop has no extra fields.
- [x] Reject future and stale observations for select/wait. Stop still requires matching identifiers and a valid schema but can stop a stale trace.
- [x] Return a new dictionary, never a mutation of input data. The module must import no controller, model, subprocess, network, or filesystem functionality.

### Step 3: Complete the contract test matrix

- [x] Add real behavioral tests for: select on each supported menu; wait on unknown; stop on terminal and stale observations; unavailable option; duplicate options; missing and additional keys; invalid kind; option fields on wait/stop; wait bounds and boolean values; wrong run; wrong observation; future time; exact age boundary and stale time; unknown/terminal selection; malformed JSON; duplicate JSON keys; NaN/Infinity; array/scalar top level; oversized payload; invalid Unicode; non-dictionary direct calls; input non-mutation.
- [x] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v` and `python3 -m compileall -q src tests`. Both must pass.

### Step 4: Review and commit

- [x] Inspect the diff for network/device side effects and unrelated edits.
- [x] Request an independent specification review, address findings, then request a separate code-quality review.
- [x] Commit only this task's files with `feat: add strict offline action boundary` after verification. Do not push or edit `STATUS.md`; the coordinating agent handles reviewed publication and status.

## Follow-on plans

Replay, logging, and the command-line demo are separate, bounded tasks after this API is reviewed. Controller integration and model training are not part of this implementation step and must not be represented as working.
