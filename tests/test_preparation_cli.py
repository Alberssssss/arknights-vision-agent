from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from arknights_vision_agent import cli


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "synthetic_demonstrations.json"
LIMIT = 16 * 1024 * 1024


def make_manifest():
    return {
        "schema_version": 1,
        "max_action_age_ms": 5000,
        "records": [
            {
                "record_id": "record-1",
                "recording_id": "recording-shared",
                "leakage_group_id": "group-shared",
                "observation": {
                    "run_id": "run-shared",
                    "observation_id": "frame-1",
                    "screen": "unknown",
                    "available_options": [],
                    "captured_at_ms": 1000,
                    "source": "recorded",
                },
                "action": {
                    "run_id": "run-shared",
                    "observation_id": "frame-1",
                    "kind": "wait",
                    "wait_ms": 100,
                },
                "decision_at_ms": 1100,
                "media": {
                    "kind": "video",
                    "path": "test/shared.mp4",
                    "start_ms": 0,
                    "end_ms": 1000,
                    "media_to_run_offset_ms": 0,
                },
                "label": {
                    "origin": "human",
                    "status": "accepted",
                    "evidence_id": "evidence-1",
                    "review_id": "review-1",
                },
                "usage_permitted": True,
            },
            {
                "record_id": "record-2",
                "recording_id": "recording-shared",
                "leakage_group_id": "group-shared",
                "observation": {
                    "run_id": "run-shared",
                    "observation_id": "frame-2",
                    "screen": "terminal",
                    "available_options": [],
                    "captured_at_ms": 1200,
                    "source": "recorded",
                },
                "action": {
                    "run_id": "run-shared",
                    "observation_id": "frame-2",
                    "kind": "stop",
                },
                "decision_at_ms": 1300,
                "media": {
                    "kind": "video",
                    "path": "test/shared.mp4",
                    "start_ms": 0,
                    "end_ms": 1200,
                    "media_to_run_offset_ms": 0,
                },
                "label": {
                    "origin": "input_log",
                    "status": "accepted",
                    "evidence_id": "evidence-2",
                    "review_id": "review-2",
                },
                "usage_permitted": True,
            },
            {
                "record_id": "record-3",
                "recording_id": "recording-excluded",
                "leakage_group_id": "group-excluded",
                "observation": {
                    "run_id": "run-excluded",
                    "observation_id": "frame-1",
                    "screen": "terminal",
                    "available_options": [],
                    "captured_at_ms": 1000,
                    "source": "synthetic",
                },
                "action": {
                    "run_id": "run-excluded",
                    "observation_id": "frame-1",
                    "kind": "stop",
                },
                "decision_at_ms": 1100,
                "media": {
                    "kind": "video",
                    "path": "test/excluded.mp4",
                    "start_ms": 0,
                    "end_ms": 1000,
                    "media_to_run_offset_ms": 0,
                },
                "label": {
                    "origin": "human",
                    "status": "pending",
                    "evidence_id": "evidence-3",
                    "review_id": None,
                },
                "usage_permitted": False,
            },
        ],
    }


class PreparationCLITests(unittest.TestCase):
    def run_cli(self, *arguments):
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "arknights_vision_agent",
                *map(str, arguments),
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )

    def write_manifest(self, directory, manifest, name="manifest.json"):
        path = Path(directory) / name
        path.write_text(
            json.dumps(manifest, allow_nan=False),
            encoding="utf-8",
        )
        return path

    def assert_expected_failure(self, completed):
        self.assertEqual(completed.returncode, 2)
        self.assertNotIn("Traceback", completed.stderr)

    def test_prepare_help(self):
        result = self.run_cli("prepare", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for flag in ("--manifest", "--output", "--seed", "--weights"):
            self.assertIn(flag, result.stdout)
        for prohibited in ("--force", "--training", "--model", "--device"):
            self.assertNotIn(prohibited, result.stdout)

    def test_top_level_help_lists_both_offline_commands(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prepare", result.stdout)
        self.assertIn("replay", result.stdout)

    def test_public_example_creates_metadata_only_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "report"
            result = self.run_cli(
                "prepare", "--manifest", EXAMPLE, "--output", output
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(
                (output / "preparation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["summary"]["record_count"], 3)
            self.assertEqual(report["summary"]["eligible_record_count"], 0)
            self.assertEqual(report["summary"]["empty_partitions"], [])
            self.assertEqual(
                report["summary"]["eligible_empty_partitions"],
                ["train", "validation", "test"],
            )
            self.assertEqual(report["scope"], "metadata_only")
            self.assertEqual(report["split"]["seed"], 0)
            self.assertTrue(
                all(value is False for value in report["verification"].values())
            )
            self.assertIn("metadata-only", result.stdout.lower())
            self.assertIn("no training started", result.stdout.lower())
            self.assertIn("no media inspected", result.stdout.lower())
            self.assertIn("warning", result.stdout.lower())
            self.assertIn("train, validation, test", result.stdout.lower())
            self.assertEqual(
                [path.name for path in output.iterdir()], ["preparation.json"]
            )
            expected_verification = {
                "media_inspected": False,
                "label_evidence_verified": False,
                "permission_verified": False,
                "training_started": False,
                "game_clear_verified": False,
            }
            self.assertEqual(report["verification"], expected_verification)
            rendered = (output / "preparation.json").read_text(encoding="utf-8")
            self.assertTrue(rendered.endswith("\n"))
            self.assertEqual(
                rendered,
                json.dumps(
                    report,
                    allow_nan=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
            )
            self.assertNotIn("NaN", rendered)
            self.assertNotIn("Infinity", rendered)
            fixture = json.loads(EXAMPLE.read_text(encoding="utf-8"))
            self.assertTrue(
                all(
                    row["observation"]["source"] == "synthetic"
                    and row["usage_permitted"] is False
                    for row in fixture["records"]
                )
            )
            for row in fixture["records"]:
                self.assertFalse((ROOT / row["media"]["path"]).exists())

    def test_seed_and_weights_are_forwarded_to_the_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report"

            result = self.run_cli(
                "prepare",
                "--manifest",
                EXAMPLE,
                "--output",
                output,
                "--seed",
                7,
                "--weights",
                0,
                10000,
                0,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(
                (output / "preparation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["split"]["seed"], 7)
            self.assertEqual(
                report["split"]["weights"],
                {"train": 0, "validation": 10000, "test": 0},
            )
            self.assertTrue(
                all(
                    group["partition"] == "validation"
                    for group in report["groups"]
                )
            )

    def test_invalid_configuration_and_missing_arguments_create_nothing(self):
        cases = (
            ("negative-seed", "--seed", -1),
            ("large-seed", "--seed", 2**63),
            ("text-seed", "--seed", "not-an-integer"),
            ("negative-weight", "--weights", -1, 1, 10000),
            ("large-weight", "--weights", 10001, 0, 0),
            ("wrong-sum", "--weights", 8000, 1000, 999),
            ("text-weight", "--weights", 8000, "text", 2000),
            ("few-weights", "--weights", 8000, 2000),
            ("many-weights", "--weights", 8000, 1000, 1000, 0),
        )
        with tempfile.TemporaryDirectory() as directory:
            for case in cases:
                with self.subTest(case=case[0]):
                    parent = Path(directory) / case[0]
                    output = parent / "report"
                    result = self.run_cli(
                        "prepare",
                        "--manifest",
                        EXAMPLE,
                        "--output",
                        output,
                        *case[1:],
                    )

                    self.assert_expected_failure(result)
                    self.assertFalse(parent.exists())

            required_cases = (
                ("missing-manifest", "prepare", "--output"),
                ("missing-output", "prepare", "--manifest"),
            )
            for name, command, supplied_flag in required_cases:
                with self.subTest(case=name):
                    parent = Path(directory) / name
                    value = parent / "value"
                    result = self.run_cli(command, supplied_flag, value)

                    self.assert_expected_failure(result)
                    self.assertFalse(parent.exists())

    def test_explicit_eligible_metadata_stays_one_group_and_unverified(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self.write_manifest(directory, make_manifest())
            output = Path(directory) / "report"

            result = self.run_cli(
                "prepare",
                "--manifest",
                manifest,
                "--output",
                output,
                "--weights",
                10000,
                0,
                0,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(
                (output / "preparation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["summary"]["eligible_record_count"], 2)
            self.assertEqual(report["summary"]["eligible_group_count"], 1)
            self.assertEqual(
                report["summary"]["partitions"]["train"][
                    "eligible_record_count"
                ],
                2,
            )
            self.assertEqual(
                report["summary"]["partitions"]["train"][
                    "eligible_group_count"
                ],
                1,
            )
            self.assertIn("2 of 3", result.stdout)
            self.assertTrue(
                all(value is False for value in report["verification"].values())
            )

    def test_non_strict_json_is_rejected_without_disclosing_content(self):
        marker = "private-marker"
        payloads = {
            "malformed": '{"private-marker":',
            "duplicate": '{"schema_version":1,"schema_version":1}',
            "nan": '{"value":NaN}',
            "infinity": '{"value":Infinity}',
            "overflow": '{"value":1e999}',
            "lone-surrogate": '{"value":"\\ud800"}',
            "too-deep": '{"value":'
            + "[" * 101
            + "0"
            + "]" * 101
            + "}",
            "top-list": "[]",
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, payload in payloads.items():
                with self.subTest(name=name):
                    manifest = Path(directory) / f"{name}.json"
                    manifest.write_text(payload, encoding="utf-8")
                    parent = Path(directory) / "missing" / name
                    output = parent / "report"

                    result = self.run_cli(
                        "prepare",
                        "--manifest",
                        manifest,
                        "--output",
                        output,
                    )

                    self.assert_expected_failure(result)
                    self.assertNotIn(marker, result.stdout.lower())
                    self.assertNotIn(marker, result.stderr.lower())
                    self.assertFalse(parent.exists())

    def test_invalid_utf8_schema_and_action_create_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid_utf8 = Path(directory) / "invalid-utf8.json"
            invalid_utf8.write_bytes(b'{"value":"\xff"}')
            invalid_schema = Path(directory) / "invalid-schema.json"
            invalid_schema.write_text(
                '{"schema_version":1,"records":[]}',
                encoding="utf-8",
            )
            invalid_action_value = make_manifest()
            invalid_action_value["records"][0]["action"]["kind"] = "tap"
            invalid_action = self.write_manifest(
                directory,
                invalid_action_value,
                "invalid-action.json",
            )

            for name, manifest in (
                ("utf8", invalid_utf8),
                ("schema", invalid_schema),
                ("action", invalid_action),
            ):
                with self.subTest(name=name):
                    parent = Path(directory) / "missing" / name
                    output = parent / "report"
                    result = self.run_cli(
                        "prepare",
                        "--manifest",
                        manifest,
                        "--output",
                        output,
                    )

                    self.assert_expected_failure(result)
                    self.assertFalse(parent.exists())

    def test_manifest_file_limit_is_inclusive(self):
        encoded = EXAMPLE.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            exact = Path(directory) / "exact.json"
            exact.write_bytes(encoded + b" " * (LIMIT - len(encoded)))
            exact_output = Path(directory) / "exact-report"

            exact_result = self.run_cli(
                "prepare",
                "--manifest",
                exact,
                "--output",
                exact_output,
            )

            self.assertEqual(exact_result.returncode, 0, exact_result.stderr)
            self.assertTrue((exact_output / "preparation.json").is_file())

            oversized = Path(directory) / "oversized.json"
            oversized.write_bytes(encoded + b" " * (LIMIT + 1 - len(encoded)))
            parent = Path(directory) / "missing" / "oversized"
            oversized_output = parent / "report"
            oversized_result = self.run_cli(
                "prepare",
                "--manifest",
                oversized,
                "--output",
                oversized_output,
            )

            self.assert_expected_failure(oversized_result)
            self.assertIn("size limit", oversized_result.stderr)
            self.assertFalse(parent.exists())

    def test_manifest_reader_requests_only_limit_plus_one_bytes(self):
        input_file = mock.MagicMock()
        input_file.__enter__.return_value.read.return_value = b"{}"
        with mock.patch.object(Path, "open", return_value=input_file):
            self.assertEqual(
                cli._load_object(
                    Path("explicit-manifest.json"),
                    max_bytes=LIMIT,
                    kind="manifest",
                ),
                {},
            )

        input_file.__enter__.return_value.read.assert_called_once_with(LIMIT + 1)
        input_file.__exit__.assert_called_once()

    def test_missing_input_and_file_output_parent_create_no_report(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            output = Path(directory) / "missing-report"
            missing_result = self.run_cli(
                "prepare", "--manifest", missing, "--output", output
            )

            self.assert_expected_failure(missing_result)
            self.assertFalse(output.exists())

            parent = Path(directory) / "parent-file"
            parent.write_text("keep-parent", encoding="utf-8")
            child_output = parent / "report"
            parent_result = self.run_cli(
                "prepare",
                "--manifest",
                EXAMPLE,
                "--output",
                child_output,
            )

            self.assert_expected_failure(parent_result)
            self.assertEqual(parent.read_text(encoding="utf-8"), "keep-parent")

    def test_existing_outputs_and_all_symlink_kinds_are_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            existing_directory = base / "existing-directory"
            existing_directory.mkdir()
            sentinel = existing_directory / "sentinel.txt"
            sentinel.write_text("keep-directory", encoding="utf-8")
            existing_file = base / "existing-file"
            existing_file.write_text("keep-file", encoding="utf-8")
            link_to_file = base / "link-to-file"
            link_to_file.symlink_to(existing_file)
            link_to_directory = base / "link-to-directory"
            link_to_directory.symlink_to(existing_directory, target_is_directory=True)
            dangling_target = base / "missing-target"
            dangling_link = base / "dangling-link"
            dangling_link.symlink_to(dangling_target)

            outputs = (
                existing_directory,
                existing_file,
                link_to_file,
                link_to_directory,
                dangling_link,
            )
            for output in outputs:
                with self.subTest(output=output.name):
                    result = self.run_cli(
                        "prepare",
                        "--manifest",
                        EXAMPLE,
                        "--output",
                        output,
                    )
                    self.assert_expected_failure(result)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep-directory")
            self.assertEqual(existing_file.read_text(encoding="utf-8"), "keep-file")
            self.assertTrue(link_to_file.is_symlink())
            self.assertTrue(link_to_directory.is_symlink())
            self.assertTrue(dangling_link.is_symlink())
            self.assertFalse(dangling_target.exists())

    def test_write_oserror_returns_two_and_retains_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report"

            def partial_writer(path, files):
                path.mkdir()
                (path / "preparation.json").write_text(
                    files["preparation.json"][:20],
                    encoding="utf-8",
                )
                raise OSError("injected write failure")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with mock.patch.object(
                cli,
                "_write_report_files",
                side_effect=partial_writer,
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                return_code = cli.main(
                    [
                        "prepare",
                        "--manifest",
                        str(EXAMPLE),
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(return_code, 2)
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertIn("injected write failure", stderr.getvalue())
            self.assertNotIn("report written", stdout.getvalue().lower())
            self.assertTrue((output / "preparation.json").is_file())


class PreparationDocumentationTests(unittest.TestCase):
    def test_readme_documents_preparation_command_and_boundaries(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("python3 -m arknights_vision_agent prepare", readme)
        self.assertIn("examples/synthetic_demonstrations.json", readme)
        self.assertIn("preparation.json", readme)
        self.assertIn("all three records are excluded", readme.lower())
        self.assertIn("no media is inspected", readme.lower())
        self.assertIn("no training is started", readme.lower())
        self.assertIn("not overwrite", readme.lower())


if __name__ == "__main__":
    unittest.main()
