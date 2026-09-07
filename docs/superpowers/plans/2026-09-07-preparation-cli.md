# Offline Preparation CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the reviewed metadata report as a bounded, non-overwriting offline command with a synthetic example.

**Architecture:** Extend the existing CLI with `prepare`; share only file-boundary mechanics while retaining the replay contract. Strict JSON and the pure preparation function own parsing and semantic rules. The command reads only its explicit manifest and writes one report, never referenced media.

**Tech Stack:** Python 3.11+ standard library, `unittest`, subprocess CLI tests.

---

## Task 1: Command, synthetic fixture, and usage documentation

**Files:** Modify `src/arknights_vision_agent/cli.py` and `README.md`. Create `tests/test_preparation_cli.py` and `examples/synthetic_demonstrations.json`. Preserve existing tests and all replay behavior. Supply the complete `2026-09-07-preparation-cli-design.md` contract to the implementer. Start only after manifest and report implementations pass specification/quality review.

### 1. Write failing real-command tests

- [ ] Start the new test file with this subprocess boundary and smoke test before adding the command:

```python
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "synthetic_demonstrations.json"
LIMIT = 16 * 1024 * 1024


class PreparationCLITests(unittest.TestCase):
    def run_cli(self, *arguments):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "arknights_vision_agent", *map(str, arguments)],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, check=False,
        )

    def test_prepare_help(self):
        result = self.run_cli("prepare", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for flag in ("--manifest", "--output", "--seed", "--weights"):
            self.assertIn(flag, result.stdout)

    def test_public_example_creates_metadata_only_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "report"
            result = self.run_cli("prepare", "--manifest", EXAMPLE, "--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((output / "preparation.json").read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["record_count"], 3)
            self.assertEqual(report["summary"]["eligible_record_count"], 0)
            self.assertEqual(report["summary"]["empty_partitions"], [])
            self.assertEqual(report["summary"]["eligible_empty_partitions"],
                             ["train", "validation", "test"])
            self.assertEqual(report["scope"], "metadata_only")
            self.assertTrue(all(v is False for v in report["verification"].values()))
            self.assertIn("metadata-only", result.stdout.lower())
            self.assertIn("no training started", result.stdout.lower())
            self.assertIn("no media inspected", result.stdout.lower())
            self.assertIn("warning", result.stdout.lower())
            self.assertEqual([p.name for p in output.iterdir()], ["preparation.json"])
```

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -p test_preparation_cli.py -v`. The initial failure must show the missing `prepare` command. Then implement the minimal help/fixture/report path to pass.

### 2. Add this complete synthetic fixture

- [ ] Create `examples/synthetic_demonstrations.json` with exactly this content. There are no actual videos and no recorded-source claims:

```json
{
  "schema_version": 1,
  "max_action_age_ms": 5000,
  "records": [
    {
      "record_id": "synthetic-select", "recording_id": "synthetic-recording-1",
      "leakage_group_id": "group-demo",
      "observation": {"run_id": "synthetic-run-1", "observation_id": "frame-1",
        "screen": "recruitment", "available_options": ["option-a"],
        "captured_at_ms": 1000, "source": "synthetic"},
      "action": {"run_id": "synthetic-run-1", "observation_id": "frame-1",
        "kind": "select", "option_id": "option-a"},
      "decision_at_ms": 1100,
      "media": {"kind": "video", "path": "synthetic/source-1.mp4",
        "start_ms": 0, "end_ms": 1000, "media_to_run_offset_ms": 0},
      "label": {"origin": "human", "status": "pending",
        "evidence_id": "synthetic-evidence-1", "review_id": null},
      "usage_permitted": false
    },
    {
      "record_id": "synthetic-wait", "recording_id": "synthetic-recording-2",
      "leakage_group_id": "group-5",
      "observation": {"run_id": "synthetic-run-2", "observation_id": "frame-1",
        "screen": "unknown", "available_options": [],
        "captured_at_ms": 1000, "source": "synthetic"},
      "action": {"run_id": "synthetic-run-2", "observation_id": "frame-1",
        "kind": "wait", "wait_ms": 500},
      "decision_at_ms": 1100,
      "media": {"kind": "video", "path": "synthetic/source-2.mp4",
        "start_ms": 0, "end_ms": 1000, "media_to_run_offset_ms": 0},
      "label": {"origin": "inferred", "status": "accepted",
        "evidence_id": "synthetic-evidence-2", "review_id": "synthetic-review-2"},
      "usage_permitted": false
    },
    {
      "record_id": "synthetic-stop", "recording_id": "synthetic-recording-3",
      "leakage_group_id": "group-4",
      "observation": {"run_id": "synthetic-run-3", "observation_id": "frame-1",
        "screen": "terminal", "available_options": [],
        "captured_at_ms": 1000, "source": "synthetic"},
      "action": {"run_id": "synthetic-run-3", "observation_id": "frame-1",
        "kind": "stop"},
      "decision_at_ms": 1100,
      "media": {"kind": "video", "path": "synthetic/source-3.mp4",
        "start_ms": 0, "end_ms": 1000, "media_to_run_offset_ms": 0},
      "label": {"origin": "input_log", "status": "rejected",
        "evidence_id": "synthetic-evidence-3", "review_id": "synthetic-review-3"},
      "usage_permitted": false
    }
  ]
}
```

### 3. Extend the CLI under regression tests

- [ ] Add imports `PreparationValidationError, build_preparation_report` from `arknights_vision_agent.preparation`, and `_MANIFEST_MAX_BYTES = 16 * 1024 * 1024`. Update the module docstring to cover both commands.
- [ ] Add this parser before `_build_parser` returns:

```python
    prepare_parser = commands.add_parser("prepare", help="report metadata eligibility and group splits")
    prepare_parser.add_argument("--manifest", required=True, type=Path)
    prepare_parser.add_argument("--output", required=True, type=Path)
    prepare_parser.add_argument("--seed", type=int, default=0)
    prepare_parser.add_argument("--weights", type=int, nargs=3,
                                metavar=("TRAIN", "VALIDATION", "TEST"))
```

- [ ] Preserve `_load_trace` as a delegate to the following shared reader; preparation calls the same helper with kind `manifest` and its own limit. Run existing CLI tests before and after extraction.

```python
def _load_object(path: Path, *, max_bytes: int, kind: str) -> dict:
    with path.open("rb") as input_file:
        payload = input_file.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise _CLIError(f"{kind} file exceeds the {max_bytes // (1024 * 1024)} MiB size limit")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _CLIError(f"{kind} file is not valid UTF-8") from error
    return load_json_object(text, max_bytes=max_bytes)


def _load_trace(path: Path) -> dict:
    return _load_object(path, max_bytes=_TRACE_MAX_BYTES, kind="trace")
```

- [ ] Factor only the existing non-overwrite writer mechanics. Filenames come from fixed internal dictionaries, never submitted records:

```python
def _write_report_files(output: Path, files: dict[str, str]) -> None:
    if os.path.lexists(output):
        raise _CLIError(f"output path already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    for name, content in files.items():
        with (output / name).open("x", encoding="utf-8") as report_file:
            report_file.write(content)


def _write_reports(output: Path, events: str, summary: str) -> None:
    _write_report_files(output, {"events.jsonl": events, "summary.json": summary})


def _prepare_command(manifest_path: Path, output: Path, seed: int, weights: list[int] | None) -> int:
    manifest = _load_object(manifest_path, max_bytes=_MANIFEST_MAX_BYTES, kind="manifest")
    named_weights = None if weights is None else dict(zip(("train", "validation", "test"), weights))
    report = build_preparation_report(manifest, seed=seed, weights=named_weights)
    rendered = json.dumps(report, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n"
    _write_report_files(output, {"preparation.json": rendered})
    summary = report["summary"]
    print(f"Metadata-only report written to {output}; "
          f"{summary['eligible_record_count']} of {summary['record_count']} records metadata-eligible; "
          "no media inspected and no training started.")
    if summary["eligible_empty_partitions"]:
        print("Warning: no metadata-eligible records in partitions: "
              + ", ".join(summary["eligible_empty_partitions"]))
    return 0
```

- [ ] Extend dispatch inside `main` and expected error handling without changing replay's error labels:

```python
        if arguments.command == "prepare":
            return _prepare_command(arguments.manifest, arguments.output,
                                    arguments.seed, arguments.weights)
```

```python
    except StrictJSONError as error:
        kind = "manifest" if arguments.command == "prepare" else "trace"
        print(f"error: invalid {kind} JSON: {error}", file=sys.stderr)
    except PreparationValidationError as error:
        print(f"error: invalid preparation data or configuration: {error}", file=sys.stderr)
```

Keep existing `ReplayValidationError`, `_CLIError`, and `OSError` handling and exit 2 after expected failures.

### 4. Expand boundary tests before each corresponding change

- [ ] Test flags forwarded to the public report: invoke seed 7 and weights `0 10000 0`, read `split.seed`, `split.weights`, and assert all groups are validation. Invalid seeds `-1`, `9223372036854775808`, and text, invalid weights negative/overlimit/wrong sum/nonnumeric/wrong arity, and missing required arguments exit 2 without creating output.
- [ ] Add a temporary, explicitly test-authored manifest with two accepted/permission-attested recorded-source rows in the same leakage group (consistent run/recording identities and distinct observations), plus one excluded row in another group. Run with weights `10000 0 0`. Assert the report and console show two of three metadata-eligible records, while global and train-partition `eligible_group_count` are each one. All evidence-verification flags must remain false: test metadata is not proof of real recordings, review, or training readiness.
- [ ] Loop over invalid payloads (`{"private-marker":`, duplicate `schema_version`, `NaN`, `Infinity`, `1e999`, escaped lone surrogate, top-level list) written to temporary manifest files; also write invalid UTF-8 bytes and invalid manifest schema/action. Require exit 2, no traceback, no private payload marker in either output stream, and neither output nor its missing parents created. Apply the same no-output/no-parent check to invalid configuration.
- [ ] Write the valid example bytes followed by whitespace to exactly `LIMIT` bytes: success. Append one more byte: size-limit error and no output. Add a reader-boundary test using a context-manager mock for the explicit input stream, asserting `.read(LIMIT + 1)`; pair it with real-file tests rather than replacing them.
- [ ] Test missing input, a file as output parent, existing output directory with sentinel, existing output file, existing symlink to file/directory, and dangling symlink. All exit 2; all pre-existing content/links remain unchanged. No recursive cleanup or force option.
- [ ] Inject an expected `OSError` at report writing in a direct `main` test and assert failure without traceback. A directory/file already created by this invocation may remain; it must not be advertised as a successful report.
- [ ] Assert exact false evidence flags, one report file, sorted-key finite JSON with final newline, and no referenced-media reader. Run top-level help and all original replay tests unchanged.

### 5. Add user-facing documentation

- [ ] Add a README section before Development with the demo command from the spec, `preparation.json`, optional `--seed 7 --weights 8000 1000 1000`, and these explicit points: metadata-only; fixture has no actual media and all rows excluded; no media inspected/training started; output not overwritten; group ratios approximate and empty eligible partitions warned; declaration digest is not a media hash. Link the manifest and report designs, collection plan, and human-help queue. Preserve current menu-only/no-game-clear limitations and deferred-training instruction.
- [ ] Change the subsequent-milestone bullet from implementing validation/splits to real-media inventory/alignment/review work, but only once this task passes review. Add a documentation test asserting command, output filename, exclusion explanation, and no-training/no-overwrite boundaries.

### 6. Verify, commit, and review

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `python3 -m compileall -q src tests`, and `git diff --check`; inspect actual diff for unrelated changes.
- [ ] Commit only the four task files as `feat: add offline metadata preparation command`. Do not push or update status from the implementer.
- [ ] Coordinator obtains specification then independent quality review and returns findings for tested fixes. Then build/install with no index/dependencies in a fresh ignored environment, run both real example commands, inspect reports, and run the full suite. Publish only reviewed changes; report exact checks and remaining limitations.
