from contextlib import redirect_stderr, redirect_stdout
import hashlib
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
from arknights_vision_agent.inventory import InventoryError


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "synthetic_inventory.json"
LIMIT = 2 * 1024 * 1024


class InventoryCLITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.media_root = self.base / "private-marker-root"
        self.media_root.mkdir()
        (self.media_root / "source.bin").write_bytes(b"abc")
        self.request = self.base / "private-marker-request.json"
        self.request.write_text(json.dumps({
            "schema_version": 1,
            "assets": [{"asset_id": "private-marker-id", "path": "source.bin"}],
        }), encoding="utf-8")

    def run_cli(self, *arguments):
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "arknights_vision_agent", *map(str, arguments)],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=10,
        )

    def arguments(self, output, *extra, request=None, media_root=None):
        return [
            "inventory", "--request", request or self.request,
            "--media-root", media_root or self.media_root, "--output", output, *extra,
        ]

    def assert_failure(self, result, *, private=True):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("assets hashed", result.stdout)
        self.assertNotIn("Inventory written", result.stdout)
        if private:
            self.assertNotIn("private-marker", result.stdout + result.stderr)

    def test_help_lists_inventory_and_its_exact_options(self):
        top = self.run_cli("--help")
        self.assertEqual(top.returncode, 0, top.stderr)
        for command in ("inventory", "replay", "prepare"):
            self.assertIn(command, top.stdout)
        result = self.run_cli("inventory", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        for option in ("--request", "--media-root", "--output", "--max-file-bytes", "--max-total-bytes"):
            self.assertIn(option, result.stdout)
        self.assertNotIn("--force", result.stdout)

    def test_public_plain_text_example_creates_canonical_private_report(self):
        output = self.base / "report"
        result = self.run_cli(*self.arguments(output, request=EXAMPLE, media_root=ROOT / "examples"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(path.name for path in output.iterdir()), ["inventory.json"])
        payload = (output / "inventory.json").read_bytes()
        report = json.loads(payload)
        self.assertEqual(payload, (json.dumps(report, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        expected_contents = (b"synthetic inventory alpha\n", b"synthetic inventory alpha\n", b"synthetic inventory beta\n")
        self.assertEqual(report["assets"], [
            {"asset_id": f"synthetic-{letter}", "path": f"synthetic_inventory_assets/{letter}.txt",
             "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
            for letter, content in zip("abc", expected_contents)
        ])
        self.assertEqual(report["duplicate_candidates"], [{
            "size_bytes": len(expected_contents[0]),
            "sha256": hashlib.sha256(expected_contents[0]).hexdigest(),
            "asset_ids": ["synthetic-a", "synthetic-b"],
        }])
        self.assertEqual(report["summary"], {"asset_count": 3, "total_bytes": sum(map(len, expected_contents)), "duplicate_group_count": 1})
        self.assertEqual(report["verification"], {
            "file_bytes_hashed": True, "media_decoded": False, "timestamps_verified": False,
            "label_evidence_verified": False, "permission_verified": False,
            "training_started": False, "game_clear_verified": False,
        })
        self.assertNotIn(str(ROOT), payload.decode("utf-8"))
        self.assertIn("3 selected assets hashed", result.stdout)
        self.assertIn("no media decoded and no training started", result.stdout)
        self.assertIn("Keep real reports private; duplicate candidates require review.", result.stdout)
        for letter, content in zip("abc", expected_contents):
            self.assertEqual((ROOT / "examples" / "synthetic_inventory_assets" / f"{letter}.txt").read_bytes(), content)

    def test_explicit_byte_cap_overrides_are_recorded(self):
        output = self.base / "report"
        result = self.run_cli(*self.arguments(output, "--max-file-bytes", 9, "--max-total-bytes", 3))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((output / "inventory.json").read_bytes())
        self.assertEqual(report["limits"], {"max_assets": 1000, "max_file_bytes": 9, "max_total_bytes": 3, "read_chunk_bytes": 1048576})
        self.assertEqual((self.media_root / "source.bin").read_bytes(), b"abc")

    def test_strict_json_failures_are_labeled_private_and_create_no_parents(self):
        payloads = {
            "malformed": b'{"private-marker":',
            "duplicate": b'{"schema_version":1,"schema_version":1}',
            "nan": b'{"private-marker":NaN}',
            "infinity": b'{"private-marker":Infinity}',
            "overflow": b'{"private-marker":1e999}',
            "surrogate": b'{"private-marker":"\\ud800"}',
            "array": b'[]',
            "deep": b'{"private-marker":' + b'[' * 101 + b'0' + b']' * 101 + b'}',
        }
        for name, payload in payloads.items():
            with self.subTest(name=name):
                self.request.write_bytes(payload)
                parent = self.base / "absent" / name
                result = self.run_cli(*self.arguments(parent / "report"))
                self.assert_failure(result)
                self.assertIn("invalid inventory request JSON", result.stderr)
                self.assertFalse(parent.exists())

    def test_invalid_utf8_and_schema_create_no_output_parents(self):
        for payload in (b'\xff', b'{"schema_version":true,"assets":[]}', b'{}',
                        b'{"schema_version":1,"assets":[{"asset_id":"private-marker","path":"../private-marker"}]}'):
            with self.subTest(payload=payload):
                self.request.write_bytes(payload)
                parent = self.base / "absent"
                result = self.run_cli(*self.arguments(parent / "report"))
                self.assert_failure(result)
                self.assertIn("invalid inventory", result.stderr)
                self.assertFalse(parent.exists())

    def test_exact_request_limit_is_accepted_and_plus_one_is_rejected(self):
        encoded = self.request.read_bytes()
        for padding, expected in ((LIMIT, 0), (LIMIT + 1, 2)):
            with self.subTest(size=padding):
                self.request.write_bytes(encoded + b" " * (padding - len(encoded)))
                parent = self.base / f"parent-{padding}"
                result = self.run_cli(*self.arguments(parent / "report"))
                self.assertEqual(result.returncode, expected, result.stderr)
                if expected:
                    self.assert_failure(result)
                    self.assertIn("2 MiB size limit", result.stderr)
                    self.assertFalse(parent.exists())

    def test_missing_and_directory_request_fail_privately(self):
        for request in (self.base / "private-marker-missing", self.media_root):
            with self.subTest(request=request.name):
                result = self.run_cli(*self.arguments(self.base / "absent/report", request=request))
                self.assert_failure(result)
                self.assertIn("inventory request", result.stderr)
                self.assertFalse((self.base / "absent").exists())

    def test_explicit_request_symlink_is_allowed(self):
        link = self.base / "request-link"
        link.symlink_to(self.request)
        result = self.run_cli(*self.arguments(self.base / "report", request=link))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_request_and_asset_fifos_are_rejected_in_bounded_subprocesses(self):
        fifo = self.media_root / "private-marker-fifo"
        os.mkfifo(fifo)
        result = self.run_cli(*self.arguments(self.base / "absent/request", request=fifo))
        self.assert_failure(result)
        self.assertIn("regular file", result.stderr)
        self.request.write_text(json.dumps({
            "schema_version": 1,
            "assets": [{"asset_id": "private-marker-id", "path": fifo.name}],
        }), encoding="utf-8")
        result = self.run_cli(*self.arguments(self.base / "absent/asset"))
        self.assert_failure(result)
        self.assertIn("asset 1", result.stderr)
        self.assertIn("regular file", result.stderr)
        self.assertFalse((self.base / "absent").exists())

    def test_invalid_caps_and_hash_failures_create_no_output_parents(self):
        for name in ("--max-file-bytes", "--max-total-bytes"):
            for value in (0, -1, 2**63, "1.5", 2):
                with self.subTest(name=name, value=value):
                    parent = self.base / "absent"
                    result = self.run_cli(*self.arguments(parent / "report", name, value))
                    self.assert_failure(result)
                    self.assertFalse(parent.exists())
        result = self.run_cli(*self.arguments(self.base / "absent/report", media_root=self.base / "private-marker-missing"))
        self.assert_failure(result)
        self.assertFalse((self.base / "absent").exists())

    def test_missing_required_flags_have_no_side_effects(self):
        arguments = self.arguments(self.base / "absent/report")
        for flag in ("--request", "--media-root", "--output"):
            with self.subTest(flag=flag):
                index = arguments.index(flag)
                result = self.run_cli(*(arguments[:index] + arguments[index + 2:]))
                self.assert_failure(result)
                self.assertIn(flag, result.stderr)
                self.assertFalse((self.base / "absent").exists())

    def test_all_existing_outputs_are_refused_before_missing_request_is_read(self):
        existing_file = self.base / "file"
        existing_file.write_bytes(b"keep")
        existing_directory = self.base / "directory"
        existing_directory.mkdir()
        (existing_directory / "sentinel").write_bytes(b"keep")
        file_link, directory_link, dangling = (self.base / name for name in ("file-link", "directory-link", "dangling"))
        file_link.symlink_to(existing_file)
        directory_link.symlink_to(existing_directory, target_is_directory=True)
        dangling.symlink_to(self.base / "missing-target")
        for output in (existing_file, existing_directory, file_link, directory_link, dangling):
            with self.subTest(output=output.name):
                result = self.run_cli(*self.arguments(output, request=self.base / "private-marker-missing"))
                self.assert_failure(result)
                self.assertIn("output path already exists", result.stderr)
                self.assertNotIn("cannot read", result.stderr)
        self.assertEqual(existing_file.read_bytes(), b"keep")
        self.assertEqual((existing_directory / "sentinel").read_bytes(), b"keep")
        self.assertTrue(all(path.is_symlink() for path in (file_link, directory_link, dangling)))
        self.assertFalse((self.base / "missing-target").exists())

    def test_repeated_success_output_preserves_report_bytes(self):
        output = self.base / "report"
        first = self.run_cli(*self.arguments(output))
        self.assertEqual(first.returncode, 0, first.stderr)
        before = (output / "inventory.json").read_bytes()
        self.request.unlink()
        second = self.run_cli(*self.arguments(output))
        self.assert_failure(second)
        self.assertIn("output path already exists", second.stderr)
        self.assertEqual((output / "inventory.json").read_bytes(), before)

    def test_write_failure_returns_two_and_retains_actual_partial_output(self):
        output = self.base / "report"
        real_open = Path.open

        class FailingWriter:
            def __init__(self, actual):
                self.actual = actual

            def __enter__(self):
                self.actual.__enter__()
                return self

            def write(self, text):
                self.actual.write(text[:20])
                self.actual.flush()
                raise OSError("injected output write failure")

            def __exit__(self, *args):
                return self.actual.__exit__(*args)

        def failing_open(path, *args, **kwargs):
            actual = real_open(path, *args, **kwargs)
            return FailingWriter(actual) if path == output / "inventory.json" else actual

        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(Path, "open", new=failing_open), redirect_stdout(stdout), redirect_stderr(stderr):
            status = cli.main(list(map(str, self.arguments(output))))
        self.assertEqual(status, 2)
        self.assertIn("injected output write failure", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(len((output / "inventory.json").read_bytes()), 20)

    def test_request_fdopen_failure_closes_descriptor_and_sanitizes_error(self):
        real_open = os.open
        descriptors = []

        def tracked_open(*args, **kwargs):
            descriptor = real_open(*args, **kwargs)
            descriptors.append(descriptor)
            return descriptor

        with mock.patch.object(os, "open", side_effect=tracked_open) as opened, \
                mock.patch.object(os, "supports_dir_fd", os.supports_dir_fd | {opened}), \
                mock.patch.object(os, "fdopen", side_effect=OSError("private-marker")):
            with self.assertRaisesRegex(InventoryError, "cannot read the inventory request") as caught:
                cli._load_inventory_request(self.request)
        self.assertNotIn("private-marker", str(caught.exception))
        self.assertEqual(len(descriptors), 1)
        with self.assertRaises(OSError):
            os.fstat(descriptors[0])

    def test_request_reader_is_bounded_and_closes_files_on_all_outcomes(self):
        real_fdopen = os.fdopen
        opened_files, read_sizes = [], []

        class TrackedReader:
            def __init__(self, actual):
                self.actual = actual

            def __enter__(self):
                self.actual.__enter__()
                return self

            def fileno(self):
                return self.actual.fileno()

            def read(self, size):
                read_sizes.append(size)
                return self.actual.read(size)

            def __exit__(self, *args):
                return self.actual.__exit__(*args)

        def tracked_fdopen(*args, **kwargs):
            actual = real_fdopen(*args, **kwargs)
            opened_files.append(actual)
            return TrackedReader(actual)

        original = self.request.read_bytes()
        for payload in (original, b"\xff", original + b" " * LIMIT):
            self.request.write_bytes(payload)
            with mock.patch.object(os, "fdopen", side_effect=tracked_fdopen):
                if payload == original:
                    self.assertEqual(cli._load_inventory_request(self.request), json.loads(original))
                else:
                    with self.assertRaises(InventoryError):
                        cli._load_inventory_request(self.request)
        self.assertEqual(read_sizes, [LIMIT + 1] * 3)
        self.assertTrue(all(file.closed for file in opened_files))

    def test_unsupported_platform_is_private_and_creates_no_output(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(os, "supports_dir_fd", set()), redirect_stdout(stdout), redirect_stderr(stderr):
            status = cli.main(list(map(str, self.arguments(self.base / "absent/report"))))
        self.assertEqual(status, 2)
        self.assertIn("requires POSIX", stderr.getvalue())
        self.assertNotIn("private-marker", stdout.getvalue() + stderr.getvalue())
        self.assertFalse((self.base / "absent").exists())

    def test_request_stat_os_error_is_private_and_closes_the_open_file(self):
        real_fdopen = os.fdopen
        opened_files = []

        def tracked_fdopen(*args, **kwargs):
            input_file = real_fdopen(*args, **kwargs)
            opened_files.append(input_file)
            return input_file

        with mock.patch.object(os, "fdopen", side_effect=tracked_fdopen), \
                mock.patch.object(os, "fstat", side_effect=OSError("private-marker")):
            with self.assertRaisesRegex(InventoryError, "cannot read the inventory request") as caught:
                cli._load_inventory_request(self.request)
        self.assertNotIn("private-marker", str(caught.exception))
        self.assertTrue(all(input_file.closed for input_file in opened_files))

    def test_import_help_replay_and_prepare_do_not_require_inventory_flags(self):
        code = """
import os
import sys
for name in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK'):
    if hasattr(os, name):
        delattr(os, name)
from arknights_vision_agent.cli import main
try:
    main(['--help'])
except SystemExit as error:
    assert error.code == 0
assert main(['replay', '--trace', 'examples/synthetic_recruitment.json', '--output', sys.argv[1]]) == 0
assert main(['prepare', '--manifest', 'examples/synthetic_demonstrations.json', '--output', sys.argv[2]]) == 0
"""
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        result = subprocess.run(
            [sys.executable, "-c", code, str(self.base / "replay"), str(self.base / "prepare")],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.base / "replay/summary.json").is_file())
        self.assertTrue((self.base / "prepare/preparation.json").is_file())


class InventoryDocumentationTests(unittest.TestCase):
    def test_readme_inventory_command_and_honest_boundaries(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "PYTHONPATH=src python3 -m arknights_vision_agent inventory \\\n"
            "  --request examples/synthetic_inventory.json \\\n"
            "  --media-root examples --output work/inventory-demo",
            readme,
        )
        self.assertLess(readme.index("## Local byte inventory demo"), readme.index("## Development"))
        for statement in (
            "inventory.json", "1 GiB", "4 GiB", "--max-file-bytes", "--max-total-bytes",
            "1000", "2 MiB", "1 MiB", "POSIX", "regular files", "descendant symlinks",
            "owner-trusted", "Keep real reports private", "duplicate candidates require review",
            "not an immutable snapshot", "access time", "not intentionally modified",
            "No folders are scanned", "media decoded", "training started",
            "Timestamp indexing and label verification remain separate work",
            "docs/superpowers/specs/2026-09-07-byte-inventory-design.md",
        ):
            with self.subTest(statement=statement):
                self.assertIn(statement, readme)
        self.assertIn("synthetic plain-text files, not videos", readme)


if __name__ == "__main__":
    unittest.main()
