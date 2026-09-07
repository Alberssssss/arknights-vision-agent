import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
EXAMPLE_TRACE = REPOSITORY_ROOT / "examples" / "synthetic_recruitment.json"
TRACE_LIMIT = 2 * 1024 * 1024


def observation(
    observation_id="observation-1",
    *,
    screen="recruitment",
    available_options=None,
    captured_at_ms=1000,
):
    if available_options is None:
        available_options = ["option-a"]
    return {
        "run_id": "run-synthetic-demo",
        "observation_id": observation_id,
        "screen": screen,
        "available_options": available_options,
        "captured_at_ms": captured_at_ms,
        "source": "synthetic",
    }


def trace_with_action(action_json):
    return {
        "schema_version": 1,
        "run_id": "run-synthetic-demo",
        "source": "synthetic",
        "steps": [
            {
                "observation": observation(),
                "action_json": action_json,
                "decision_at_ms": 1100,
            }
        ],
    }


class ReplayCLITests(unittest.TestCase):
    def run_cli(self, *arguments):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(SOURCE_ROOT)
        return subprocess.run(
            [sys.executable, "-m", "arknights_vision_agent", *map(str, arguments)],
            cwd=REPOSITORY_ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )

    def write_trace(self, directory, trace, name="trace.json"):
        path = Path(directory) / name
        path.write_text(json.dumps(trace, allow_nan=False), encoding="utf-8")
        return path

    def assert_expected_failure(self, completed, marker=None):
        self.assertNotEqual(0, completed.returncode)
        self.assertNotIn("Traceback", completed.stderr)
        if marker is not None:
            self.assertNotIn(marker, completed.stderr)

    def test_help_runs_the_actual_module(self):
        completed = self.run_cli("--help")

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("replay", completed.stdout)
        self.assertIn("--help", completed.stdout)
        self.assertEqual("", completed.stderr)

    def test_committed_synthetic_fixture_writes_honest_reports(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "reports" / "demo"

            completed = self.run_cli(
                "replay", "--trace", EXAMPLE_TRACE, "--output", output
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertIn(str(output), completed.stdout)
            self.assertIn("no game or device was controlled", completed.stdout.lower())
            events = [
                json.loads(line)
                for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(3, len(events))
            self.assertEqual(
                ["allowed_dry_run", "allowed_dry_run", "stopped"],
                [event["status"] for event in events],
            )
            self.assertTrue(all(event["executed"] is False for event in events))
            self.assertIs(summary["game_clear_verified"], False)
            self.assertIs(summary["stopped"], True)
            self.assertNotIn("NaN", (output / "events.jsonl").read_text(encoding="utf-8"))
            self.assertNotIn("Infinity", (output / "summary.json").read_text(encoding="utf-8"))

    def test_valid_trace_without_stop_exits_zero(self):
        action_json = (
            '{"run_id":"run-synthetic-demo","observation_id":"observation-1",'
            '"kind":"select","option_id":"option-a"}'
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            trace = self.write_trace(temporary_directory, trace_with_action(action_json))
            output = Path(temporary_directory) / "output"

            completed = self.run_cli("replay", "--trace", trace, "--output", output)

            self.assertEqual(0, completed.returncode, completed.stderr)
            event = json.loads((output / "events.jsonl").read_text(encoding="utf-8"))
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertIs(event["executed"], False)
            self.assertIs(summary["game_clear_verified"], False)

    def test_rejects_malformed_and_non_strict_trace_json(self):
        marker = "PRIVATE-TRACE-MARKER"
        payloads = {
            "malformed": '{"PRIVATE-TRACE-MARKER":',
            "duplicate": '{"schema_version":1,"schema_version":1}',
            "nan": '{"value":NaN}',
            "overflow": '{"value":1e999}',
            "invalid-unicode": '{"value":"\\ud800"}',
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            for name, payload in payloads.items():
                with self.subTest(name=name):
                    trace = Path(temporary_directory) / f"{name}.json"
                    trace.write_text(payload, encoding="utf-8")
                    output = Path(temporary_directory) / f"{name}-output"

                    completed = self.run_cli(
                        "replay", "--trace", trace, "--output", output
                    )

                    self.assert_expected_failure(completed, marker)
                    self.assertFalse(output.exists())

    def test_rejects_invalid_utf8_trace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            trace = Path(temporary_directory) / "invalid-utf8.json"
            trace.write_bytes(b'{"marker":"\xff"}')
            output = Path(temporary_directory) / "output"

            completed = self.run_cli("replay", "--trace", trace, "--output", output)

            self.assert_expected_failure(completed)
            self.assertIn("UTF-8", completed.stderr)
            self.assertFalse(output.exists())

    def test_rejects_invalid_replay_structure_without_creating_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            trace = self.write_trace(temporary_directory, {"schema_version": 1})
            output = Path(temporary_directory) / "output"

            completed = self.run_cli("replay", "--trace", trace, "--output", output)

            self.assert_expected_failure(completed)
            self.assertIn("replay trace", completed.stderr)
            self.assertFalse(output.exists())

    def test_blocked_malformed_and_overflowing_actions_persist_reports(self):
        marker = "PRIVATE-ACTION-MARKER"
        action_payloads = {
            "malformed": marker + "-not-json",
            "overflow": '{"value":1e999}',
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            for name, action_json in action_payloads.items():
                with self.subTest(name=name):
                    trace = self.write_trace(
                        temporary_directory,
                        trace_with_action(action_json),
                        f"{name}.json",
                    )
                    output = Path(temporary_directory) / f"{name}-output"

                    completed = self.run_cli(
                        "replay", "--trace", trace, "--output", output
                    )

                    self.assert_expected_failure(completed, marker)
                    self.assertIn("blocked", completed.stderr.lower())
                    event = json.loads((output / "events.jsonl").read_text(encoding="utf-8"))
                    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
                    self.assertEqual("blocked", event["status"])
                    self.assertIs(event["executed"], False)
                    self.assertEqual(1, summary["blocked_actions"])
                    self.assertIs(summary["game_clear_verified"], False)

    def test_missing_trace_is_reported_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing.json"
            output = Path(temporary_directory) / "output"

            completed = self.run_cli("replay", "--trace", missing, "--output", output)

            self.assert_expected_failure(completed)
            self.assertIn("error", completed.stderr.lower())
            self.assertFalse(output.exists())

    def test_actual_oversized_file_is_rejected_before_json_decoding(self):
        marker = "PRIVATE-OVERSIZE-MARKER"
        with tempfile.TemporaryDirectory() as temporary_directory:
            trace = Path(temporary_directory) / "oversized.json"
            trace.write_bytes(b"{" + marker.encode("ascii") + b"x" * TRACE_LIMIT)
            output = Path(temporary_directory) / "output"

            completed = self.run_cli("replay", "--trace", trace, "--output", output)

            self.assert_expected_failure(completed, marker)
            self.assertIn("size limit", completed.stderr)
            self.assertFalse(output.exists())

    def test_valid_trace_at_exact_file_limit_is_accepted(self):
        action_json = (
            '{"run_id":"run-synthetic-demo","observation_id":"observation-1",'
            '"kind":"select","option_id":"option-a"}'
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            trace = Path(temporary_directory) / "exact-limit.json"
            encoded = json.dumps(trace_with_action(action_json)).encode("utf-8")
            trace.write_bytes(encoded + b" " * (TRACE_LIMIT - len(encoded)))
            output = Path(temporary_directory) / "output"

            completed = self.run_cli("replay", "--trace", trace, "--output", output)

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertTrue((output / "summary.json").is_file())

    def test_existing_output_directory_and_sentinel_are_untouched(self):
        action_json = (
            '{"run_id":"run-synthetic-demo","observation_id":"observation-1",'
            '"kind":"select","option_id":"option-a"}'
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            trace = self.write_trace(temporary_directory, trace_with_action(action_json))
            output = Path(temporary_directory) / "output"
            output.mkdir()
            sentinel = output / "sentinel.txt"
            sentinel.write_text("keep-me", encoding="utf-8")

            completed = self.run_cli("replay", "--trace", trace, "--output", output)

            self.assert_expected_failure(completed)
            self.assertEqual("keep-me", sentinel.read_text(encoding="utf-8"))
            self.assertEqual([sentinel], list(output.iterdir()))

    def test_existing_output_file_or_symlink_is_refused(self):
        action_json = (
            '{"run_id":"run-synthetic-demo","observation_id":"observation-1",'
            '"kind":"select","option_id":"option-a"}'
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            trace = self.write_trace(temporary_directory, trace_with_action(action_json))
            existing_file = Path(temporary_directory) / "existing-file"
            existing_file.write_text("keep-file", encoding="utf-8")
            link = Path(temporary_directory) / "existing-link"
            link.symlink_to(existing_file)

            for output in (existing_file, link):
                with self.subTest(output=output.name):
                    completed = self.run_cli(
                        "replay", "--trace", trace, "--output", output
                    )
                    self.assert_expected_failure(completed)

            self.assertEqual("keep-file", existing_file.read_text(encoding="utf-8"))
            self.assertTrue(link.is_symlink())

    def test_ordinary_file_as_output_parent_is_rejected(self):
        action_json = (
            '{"run_id":"run-synthetic-demo","observation_id":"observation-1",'
            '"kind":"select","option_id":"option-a"}'
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            trace = self.write_trace(temporary_directory, trace_with_action(action_json))
            parent = Path(temporary_directory) / "parent-file"
            parent.write_text("keep-parent", encoding="utf-8")
            output = parent / "output"

            completed = self.run_cli("replay", "--trace", trace, "--output", output)

            self.assert_expected_failure(completed)
            self.assertEqual("keep-parent", parent.read_text(encoding="utf-8"))


class ReplayDocumentationTests(unittest.TestCase):
    def test_readme_documents_offline_cli_outputs_and_boundaries(self):
        readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("python3 -m arknights_vision_agent replay", readme)
        self.assertIn("events.jsonl", readme)
        self.assertIn("summary.json", readme)
        self.assertIn("blocked", readme.lower())
        self.assertIn("not overwrite", readme.lower())
        self.assertIn("not a simulator", readme.lower())
        self.assertIn("no GPU", readme)
        self.assertIn("HUMAN_HELP.md", readme)
        self.assertIn("deferred actual training", readme)
