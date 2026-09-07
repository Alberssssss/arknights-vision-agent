# Offline Setup Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect declared model/loader contradictions and report limited local host facts without loading models, probing a GPU/device, or launching training.

**Architecture:** A pure profile validator precedes comparison against the repository's pinned research snapshot. A separate collector observes only interpreter/OS features and boolean discovery of four fixed executable names. The CLI shares regular-file JSON mechanics with inventory while preserving its stronger platform gate and existing commands.

**Tech Stack:** Python 3.11+ standard library, `unittest`, isolated subprocess CLI tests, no new dependencies.

---

## Task 1: Profile/report API and command

Coordinator supplies the complete `2026-09-07-setup-preflight-design.md` contract. This one task owns:

- Create `src/arknights_vision_agent/preflight.py`, `tests/test_preflight.py`, `tests/test_preflight_cli.py`.
- Modify `src/arknights_vision_agent/cli.py` and `README.md`.
- Create `examples/setup_qwen38.json` and `examples/setup_qwen3vl8b.json`.
- Do not modify inventory internals, old tests, status, research notes, or other coordinator documents. Raise any necessary scope change before acting.

### Step 1: API red test and strict validation

- [ ] Write and run this smoke test before adding the module:

```python
import copy
import unittest
from unittest.mock import patch

from arknights_vision_agent.preflight import (
    PreflightError, build_preflight_report, validate_setup_profile,
)


PROFILE = {
    "schema_version": 1,
    "model": {"model_id": "Qwen/Qwen3.8-27B",
              "revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
              "architecture": "Qwen3_5ForConditionalGeneration"},
    "controller": {"backend": "maaframework", "version": "5.12.3"},
}


class PreflightTests(unittest.TestCase):
    def test_known_profile_is_detached_and_reported_without_execution(self):
        profile = copy.deepcopy(PROFILE)
        validated = validate_setup_profile(profile)
        self.assertEqual(validated, profile)
        self.assertIsNot(validated["model"], profile["model"])
        report = build_preflight_report(profile)
        self.assertEqual(report["comparison"]["model"], {
            "status": "matches_research_snapshot",
            "expected_architecture": "Qwen3_5ForConditionalGeneration",
        })
        self.assertEqual(report["comparison"]["controller"],
                         {"status": "matches_research_snapshot"})
        self.assertTrue(all(v is False for v in report["execution"].values()))
        self.assertIn("gpu_memory", report["unmeasured"])
        report["declared"]["model"]["architecture"] = "Changed"
        self.assertEqual(profile, PROFILE)
```

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -p test_preflight.py -v`; confirm expected missing-module/API failure. Add exact-schema/type/regex/null rejection tests before validation branches.
- [ ] Implement `PreflightError`, exact-object checking, string full-match validation with `re.fullmatch`, and `validate_setup_profile`. Use `type(value) is dict/str/int`, not coercion. Copy only after complete validation. Diagnostic messages identify fixed fields only. These full helpers define the validation approach:

```python
def _fields(value, keys, where):
    if type(value) is not dict or set(value) != keys:
        raise PreflightError(f"{where} fields do not match the schema")


def _string(value, pattern, where):
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        raise PreflightError(f"{where} is invalid")


def validate_setup_profile(profile: dict) -> dict:
    _fields(profile, {"schema_version", "model", "controller"}, "setup profile")
    if type(profile["schema_version"]) is not int or profile["schema_version"] != 1:
        raise PreflightError("setup profile schema_version must be integer 1")
    model = profile["model"]
    if model is not None:
        _fields(model, {"model_id", "revision", "architecture"}, "model")
        _string(model["model_id"],
                r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}/[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
                "model model_id")
        _string(model["revision"], r"[0-9a-f]{40}", "model revision")
        _string(model["architecture"], r"[A-Za-z][A-Za-z0-9_]{0,127}",
                "model architecture")
    controller = profile["controller"]
    if controller is not None:
        _fields(controller, {"backend", "version"}, "controller")
        _string(controller["backend"], r"maa|maaframework", "controller backend")
        _string(controller["version"], r"[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}",
                "controller version")
    return copy.deepcopy(profile)
```

- [ ] Test exact boundaries (model ID 128-character segments, architecture 128 characters, 40-character lowercase revision, version 5-digit components) and their one-over/invalid forms. Include Boolean version, dict/list subclasses, unknown fields, mutable revisions, control/surrogate/non-ASCII strings, whitespace, URLs/extra slashes, invalid backend, and all combinations of null integrations. Invalid late controller fields must prevent all local collection.

### Step 2: Snapshot comparison and collector under tests

- [ ] Add comparison tests before implementation: both exact known model tuples; known tuple with wrong architecture; unfamiliar ID; known ID with unfamiliar revision and wrong architecture remains unreviewed; both controller snapshot pairs; swapped/new controller releases stay unreviewed; null fields stay unconfigured. No guess based on model-name prefixes.
- [ ] Define the two model tuples from the spec as a private dictionary keyed by `(model_id, revision)`, and controller tuples as a private set `{("maa", "6.17.2"), ("maaframework", "5.12.3")}`. Model classification code:

```python
def _compare_model(model):
    if model is None:
        return {"status": "not_configured", "expected_architecture": None}
    expected = _MODEL_SNAPSHOTS.get((model["model_id"], model["revision"]))
    if expected is None:
        return {"status": "unreviewed_contract", "expected_architecture": None}
    status = ("matches_research_snapshot" if model["architecture"] == expected
              else "contradicts_research_snapshot")
    return {"status": status, "expected_architecture": expected}


def _compare_controller(controller):
    if controller is None:
        return {"status": "not_configured"}
    known = (controller["backend"], controller["version"]) in _CONTROLLER_SNAPSHOTS
    return {"status": "matches_research_snapshot" if known else "unreviewed_contract"}
```

- [ ] Add low-level observation tests before collector code. Use real collection once, and patch `sys`/`os.uname`/`shutil.which` inputs to cover absent capabilities and discovered private paths. Never execute the discovered program. This full collector is the intended boundary:

```python
def collect_local_facts() -> dict:
    try:
        features = {
            "posix": os.name == "posix",
            "open_dir_fd": os.open in os.supports_dir_fd,
            "o_directory": hasattr(os, "O_DIRECTORY"),
            "o_nofollow": hasattr(os, "O_NOFOLLOW"),
            "o_nonblock": hasattr(os, "O_NONBLOCK"),
        }
        features["required_features_present"] = all(features.values())
        machine = os.uname().machine if hasattr(os, "uname") else None
        programs = {name: shutil.which(name) is not None
                    for name in ("ffmpeg", "ffprobe", "adb", "nvidia-smi")}
    except OSError as error:
        raise PreflightError("cannot collect local capability facts") from error
    version = sys.version_info
    return {
        "python": {"implementation": sys.implementation.name,
                   "version": f"{version.major}.{version.minor}.{version.micro}"},
        "platform": sys.platform,
        "os_name": os.name,
        "machine": machine,
        "inventory_features": features,
        "executables_on_path": programs,
    }
```

- [ ] Add standard imports `copy`, `os`, `re`, `shutil`, `sys`. `build_preflight_report` validates, then compares and collects; returns exactly the design's report with new containers for fixed unmeasured/execution fields. No optional injection parameter, aggregate readiness flag, timestamps, or environment defaults. The `unmeasured` list is exactly the 12 ordered identifiers in the spec, and the five execution flags are always false.
- [ ] Test all report keys/nesting/order, detached profile and fixed fields across calls, actual local versus declared data, required-features conjunction, absent `uname`, generic OS-error privacy, and all-four-programs-present without changing unmeasured/execution fields. Patch `subprocess.Popen`, socket network connection entry points, and optional-import paths to raise if invoked; exercise the real collector/report. Don't use mocked report return values to prove safety.

### Step 3: Shared regular input without inventory regression

- [ ] Add direct/new subprocess tests showing preflight missing command red. Add inventory input-regression tests in the new file before refactoring: existing labels/gates, OS/UTF-8/size failures, fd wrapping failure cleanup, malformed JSON propagation. Existing test files remain unchanged.
- [ ] Extract `_load_regular_object(path, *, max_bytes, kind)` in CLI using existing inventory reader mechanics. It requires only availability of `O_NONBLOCK`, opens `O_RDONLY|O_NONBLOCK`, requires regular `fstat`, bounds `.read(max_bytes+1)`, closes on every success/error including failed `fdopen`, validates size and UTF-8, then calls shared strict JSON. Raise `_CLIError` with fixed kind strings. Preserve inventory messages exactly: `cannot read the inventory request`, `inventory request must be a regular file`, `inventory request exceeds the 2 MiB size limit`, `inventory request is not valid UTF-8`.
- [ ] Replace the inventory wrapper with this full delegation. Its stronger capability guard stays before the helper:

```python
def _load_inventory_request(path: Path) -> dict:
    require_inventory_platform()
    try:
        return _load_regular_object(path, max_bytes=_TRACE_MAX_BYTES,
                                    kind="inventory request")
    except _CLIError as error:
        raise InventoryError(str(error)) from error
```

- [ ] On missing `O_NONBLOCK`, helper raises `_CLIError` before opening input; absence of the other inventory capabilities does not prevent preflight file reading. Keep replay/preparation `_load_object` behavior unchanged. Run the entire existing suite before/after extraction and record evidence.

### Step 4: Preflight command and examples

- [ ] Add `preflight` parser with only required `--profile` and `--output` Path arguments, then add the new report API/error imports. Implement this command after its real subprocess tests are red:

```python
def _preflight_command(profile_path: Path, output: Path) -> int:
    if os.path.lexists(output):
        raise _CLIError(f"output path already exists: {output}")
    profile = _load_regular_object(profile_path, max_bytes=_TRACE_MAX_BYTES,
                                   kind="setup profile")
    report = build_preflight_report(profile)
    rendered = json.dumps(report, allow_nan=False, sort_keys=True,
                          separators=(",", ":")) + "\n"
    _write_report_files(output, {"preflight.json": rendered})
    print(f"Preflight report written to {output}; local facts only; "
          "no training, inference, or device contact occurred.")
    for name in ("model", "controller"):
        status = report["comparison"][name]["status"]
        if status in ("unreviewed_contract", "not_configured"):
            print(f"Warning: {name} is {status}; no compatibility established.")
    if report["comparison"]["model"]["status"] == "contradicts_research_snapshot":
        print(f"error: model architecture contradicts the research snapshot; "
              f"diagnostic report retained in {output}", file=sys.stderr)
        return 2
    return 0
```

- [ ] Add `main` dispatch and `PreflightError` handling (`error: invalid setup profile or local facts: ...`, exit 2). Extend strict JSON label map with `preflight: setup profile`, preserving all old labels. Invalid inputs/facts never write output; valid contradiction reports intentionally remain.
- [ ] Create `examples/setup_qwen38.json` with the exact spec's primary example. Create `setup_qwen3vl8b.json` with schema1, model `Qwen/Qwen3-VL-8B-Instruct`, revision `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`, architecture `Qwen3VLForConditionalGeneration`, controller backend `maaframework`, version `5.12.3`. No paths, device addresses, enablement or hidden model choice.
- [ ] Add subprocess helper with source PYTHONPATH, root cwd, DEVNULL stdin, captured text, and timeout10. Cover both examples, actual host metadata, exact output keys/canonical serialization/final newline, false/unmeasured fields, no source/private-discovery paths, wrong-architecture retained reports, contradiction with null/new controller release still exit2, valid unknown/null warnings exit0, no ready/compatible success claim.
- [ ] Cover exact2MiB/+1 payload, strict UTF-8/JSON/duplicate keys/nonfinite/surrogate/list data, malformed profile, profile symlink, missing/file-directory/FIFO input, required flags, nonblocking missing before input open, other inventory flags absent while preflight works, and inventory stronger gate retained. Failures exit2/no traceback/no payload/no missing output parents. Test output file/directory/live/dangling symlink refusal before a missing profile, repeated unchanged output, injected write failure/no success, and new partial-output behavior.

### Step 5: Documentation, verification, commit, reviews

- [ ] Add README preflight section before Development, exact example command and second profile option, `preflight.json`, fixed research snapshot versus latest/compatibility, both null/unknown warnings, retained contradiction exit2, local-host not remote-H20 observations, required nonblocking file-input support, API missing-feature reporting, no native/model/device execution, private fresh outputs, no automatic follow-on job, and remaining integration/data/GPU measurements. Link design and setup notes. Profile examples are candidate declarations, not a chosen/enabled runtime.
- [ ] Add documentation and no-added-runtime-dependency checks to new tests. Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `python3 -m compileall -q src tests`, `git diff --check`; inspect exact file ownership/diff and self-review. Commit only the seven task files with `feat: report offline setup profiles and local facts`; do not push or update status.
- [ ] Report red/green evidence, count, commit, files, limitations, and DONE/DONE_WITH_CONCERNS/BLOCKED/NEEDS_CONTEXT. Coordinator independently checks actual code, obtains specification then independent final quality/integration review, and returns findings to the implementer with regression tests before re-review.
- [ ] Coordinator builds/installs fresh wheel with no index/dependencies and verifies all four installed commands under isolated Python, real observed host values, warning/contradiction exits and non-overwrite. Update status/research notes accurately, publish reviewed branch without force, verify remote hash and clean worktree. Keep full goal active; actual training remains deferred.
