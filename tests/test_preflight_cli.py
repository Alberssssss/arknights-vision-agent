import ast
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from types import SimpleNamespace
from unittest import mock

from arknights_vision_agent import cli
from arknights_vision_agent.inventory import InventoryError
from arknights_vision_agent.strict_json import StrictJSONError


ROOT = Path(__file__).resolve().parents[1]
LIMIT = 2 * 1024 * 1024
PROFILE = {
    "schema_version": 1,
    "model": {
        "model_id": "Qwen/Qwen3.8-27B",
        "revision": "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0",
        "architecture": "Qwen3_5ForConditionalGeneration",
    },
    "controller": {"backend": "maaframework", "version": "5.12.3"},
}
MODEL_8B = {
    "model_id": "Qwen/Qwen3-VL-8B-Instruct",
    "revision": "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b",
    "architecture": "Qwen3VLForConditionalGeneration",
}
UNMEASURED = [
    "gpu_identity", "gpu_memory", "model_snapshot", "model_processor",
    "dependency_compatibility", "model_inference", "media_decoding",
    "media_timestamps", "label_quality", "controller_connection",
    "controller_actions", "game_performance",
]
EXECUTION = {
    "training_started": False, "inference_started": False,
    "device_contacted": False, "model_downloaded": False,
    "native_tools_executed": False,
}


class PreflightCLITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.profile = self.base / "private-marker-profile.json"
        self.profile.write_text(json.dumps(PROFILE), encoding="utf-8")

    def run_cli(self, *arguments):
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "arknights_vision_agent", *map(str, arguments)],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=10,
        )

    def arguments(self, output, *, profile=None):
        return ["preflight", "--profile", profile or self.profile, "--output", output]

    def test_preflight_help_has_only_the_two_required_options(self):
        result = self.run_cli("preflight", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--profile PROFILE", result.stdout)
        self.assertIn("--output OUTPUT", result.stdout)
        for absent in ("--model", "--device", "--train", "--live", "--force", "--download"):
            self.assertNotIn(absent, result.stdout)

    def assert_failure(self, result):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("private-marker", result.stdout + result.stderr)
        self.assertNotIn("Preflight report written", result.stdout)

    def read_report(self, output):
        self.assertEqual(sorted(path.name for path in output.iterdir()), ["preflight.json"])
        encoded = (output / "preflight.json").read_bytes()
        report = json.loads(encoded)
        self.assertEqual(encoded, (
            json.dumps(report, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8"))
        self.assertEqual(report["execution"], EXECUTION)
        self.assertTrue(all(value is False for value in report["execution"].values()))
        self.assertEqual(report["unmeasured"], UNMEASURED)
        self.assertNotIn(str(ROOT), encoded.decode("utf-8"))
        self.assertNotIn(str(self.base), encoded.decode("utf-8"))
        self.assertNotIn("ready", report)
        self.assertNotIn("compatible", report)
        return report

    def assert_local_only_message(self, result, output):
        self.assertIn(
            f"Preflight report written to {output}; local facts only; "
            "no training, inference, or device contact occurred.",
            result.stdout,
        )
        self.assertNotIn("ready", result.stdout.lower())
        self.assertNotIn("compatible", result.stdout.lower())

    def test_profile_creates_canonical_report_with_actual_current_host_values(self):
        output = self.base / "report"
        before = self.profile.read_bytes()
        result = self.run_cli(*self.arguments(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        report = self.read_report(output)
        self.assertEqual(report["declared"], PROFILE)
        self.assertEqual(report["scope"], "offline_setup_preflight")
        self.assertEqual(report["research_snapshot_id"], "repository-research-2026-09-07-v1")
        facts = report["observed_local"]
        self.assertEqual(facts["python"], {
            "implementation": sys.implementation.name,
            "version": ".".join(map(str, sys.version_info[:3])),
        })
        self.assertEqual(facts["platform"], sys.platform)
        self.assertEqual(facts["os_name"], os.name)
        self.assertEqual(facts["machine"], os.uname().machine if hasattr(os, "uname") else None)
        features = {
            "posix": os.name == "posix", "open_dir_fd": os.open in os.supports_dir_fd,
            "o_directory": hasattr(os, "O_DIRECTORY"),
            "o_nofollow": hasattr(os, "O_NOFOLLOW"), "o_nonblock": hasattr(os, "O_NONBLOCK"),
        }
        self.assertEqual(facts["inventory_features"], {
            **features, "required_features_present": all(features.values()),
        })
        self.assertEqual(facts["executables_on_path"], {
            name: shutil.which(name) is not None for name in ("ffmpeg", "ffprobe", "adb", "nvidia-smi")
        })
        self.assert_local_only_message(result, output)
        self.assertNotIn("Warning:", result.stdout)
        self.assertEqual(self.profile.read_bytes(), before)

    def test_both_committed_examples_use_their_own_snapshot(self):
        for name, model in (("setup_qwen38.json", PROFILE["model"]),
                            ("setup_qwen3vl8b.json", MODEL_8B)):
            with self.subTest(name=name):
                output = self.base / name
                result = self.run_cli(*self.arguments(output, profile=ROOT / "examples" / name))
                self.assertEqual(result.returncode, 0, result.stderr)
                report = self.read_report(output)
                self.assertEqual(report["declared"], {**PROFILE, "model": model})
                self.assertEqual(report["comparison"], {
                    "model": {"status": "matches_research_snapshot",
                              "expected_architecture": model["architecture"]},
                    "controller": {"status": "matches_research_snapshot"},
                })
                self.assert_local_only_message(result, output)

    def test_strict_json_failures_are_private_and_do_not_create_parents(self):
        payloads = {
            "malformed": b'{"private-marker":',
            "duplicate": b'{"private-marker":1,"private-marker":2}',
            "nan": b'{"private-marker":NaN}',
            "infinity": b'{"private-marker":Infinity}',
            "negative-infinity": b'{"private-marker":-Infinity}',
            "overflow": b'{"private-marker":1e999}',
            "surrogate": b'{"private-marker":"\\ud800"}',
            "array": b'[]',
            "null": b'null',
            "deep": b'{"private-marker":' + b'[' * 101 + b'0' + b']' * 101 + b'}',
        }
        for name, payload in payloads.items():
            with self.subTest(name=name):
                self.profile.write_bytes(payload)
                parent = self.base / "absent" / name
                result = self.run_cli(*self.arguments(parent / "report"))
                self.assert_failure(result)
                self.assertIn("error: invalid setup profile JSON:", result.stderr)
                self.assertFalse(parent.parent.exists())

    def test_invalid_utf8_is_private_and_creates_no_output_parents(self):
        self.profile.write_bytes(b"\xff")
        result = self.run_cli(*self.arguments(self.base / "absent/report"))
        self.assert_failure(result)
        self.assertEqual(result.stderr, "error: setup profile is not valid UTF-8\n")
        self.assertFalse((self.base / "absent").exists())

    def test_malformed_profiles_are_field_only_errors_before_output_creation(self):
        profiles = [
            {}, {**PROFILE, "schema_version": True},
            {**PROFILE, "model": {**PROFILE["model"], "revision": "private-marker"}},
            {**PROFILE, "controller": {**PROFILE["controller"], "version": "private-marker"}},
            {**PROFILE, "controller": {**PROFILE["controller"], "endpoint": "private-marker"}},
            {**PROFILE, "private-marker": "private-marker"},
        ]
        for profile in profiles:
            with self.subTest(profile=profile):
                self.profile.write_text(json.dumps(profile), encoding="utf-8")
                result = self.run_cli(*self.arguments(self.base / "absent/report"))
                self.assert_failure(result)
                self.assertIn("error: invalid setup profile or local facts:", result.stderr)
                self.assertFalse((self.base / "absent").exists())

    def test_exact_two_mib_is_accepted_and_one_extra_byte_is_refused(self):
        original = self.profile.read_bytes()
        for size, expected in ((LIMIT, 0), (LIMIT + 1, 2)):
            with self.subTest(size=size):
                self.profile.write_bytes(original + b" " * (size - len(original)))
                parent = self.base / f"parent-{size}"
                result = self.run_cli(*self.arguments(parent / "report"))
                self.assertEqual(result.returncode, expected, result.stderr)
                if expected == 0:
                    self.assertEqual(self.read_report(parent / "report")["declared"], PROFILE)
                else:
                    self.assert_failure(result)
                    self.assertEqual(result.stderr, "error: setup profile exceeds the 2 MiB size limit\n")
                    self.assertFalse(parent.exists())

    def test_missing_and_directory_profile_are_private_failures(self):
        for profile in (self.base / "private-marker-missing", self.base):
            with self.subTest(profile=profile.name):
                result = self.run_cli(*self.arguments(self.base / "absent/report", profile=profile))
                self.assert_failure(result)
                self.assertIn("setup profile", result.stderr)
                self.assertFalse((self.base / "absent").exists())

    def test_profile_fifo_is_refused_in_a_bounded_subprocess(self):
        fifo = self.base / "private-marker-fifo"
        os.mkfifo(fifo)
        result = self.run_cli(*self.arguments(self.base / "absent/report", profile=fifo))
        self.assert_failure(result)
        self.assertIn("setup profile must be a regular file", result.stderr)
        self.assertFalse((self.base / "absent").exists())

    def test_explicitly_selected_profile_symlink_is_allowed(self):
        link = self.base / "selected-link"
        link.symlink_to(self.profile)
        output = self.base / "report"
        result = self.run_cli(*self.arguments(output, profile=link))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_report(output)["declared"], PROFILE)
        self.assertTrue(link.is_symlink())

    def test_required_flags_are_enforced_without_side_effects(self):
        arguments = self.arguments(self.base / "absent/report")
        for flag in ("--profile", "--output"):
            with self.subTest(flag=flag):
                index = arguments.index(flag)
                result = self.run_cli(*(arguments[:index] + arguments[index + 2:]))
                self.assert_failure(result)
                self.assertIn(flag, result.stderr)
                self.assertFalse((self.base / "absent").exists())

    def test_existing_outputs_are_refused_before_a_missing_profile_is_read(self):
        existing_file, existing_directory = self.base / "file", self.base / "directory"
        existing_file.write_bytes(b"keep")
        existing_directory.mkdir()
        (existing_directory / "sentinel").write_bytes(b"keep")
        file_link, directory_link, dangling = (self.base / name for name in ("file-link", "directory-link", "dangling"))
        file_link.symlink_to(existing_file)
        directory_link.symlink_to(existing_directory, target_is_directory=True)
        dangling.symlink_to(self.base / "missing-target")
        for output in (existing_file, existing_directory, file_link, directory_link, dangling):
            with self.subTest(output=output.name):
                result = self.run_cli(*self.arguments(output, profile=self.base / "private-marker-missing"))
                self.assert_failure(result)
                self.assertIn("output path already exists", result.stderr)
                self.assertNotIn("cannot read", result.stderr)
        self.assertEqual(existing_file.read_bytes(), b"keep")
        self.assertEqual((existing_directory / "sentinel").read_bytes(), b"keep")
        self.assertTrue(all(path.is_symlink() for path in (file_link, directory_link, dangling)))
        self.assertFalse((self.base / "missing-target").exists())

    def test_repeated_output_preserves_existing_report_bytes(self):
        output = self.base / "report"
        first = self.run_cli(*self.arguments(output))
        self.assertEqual(first.returncode, 0, first.stderr)
        before = (output / "preflight.json").read_bytes()
        self.profile.unlink()
        second = self.run_cli(*self.arguments(output))
        self.assert_failure(second)
        self.assertIn("output path already exists", second.stderr)
        self.assertEqual((output / "preflight.json").read_bytes(), before)

    def test_existing_output_prevents_both_input_open_and_local_collection(self):
        output = self.base / "existing"
        output.mkdir()
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(os, "open", side_effect=AssertionError("must not open")) as opened, \
                mock.patch.object(shutil, "which", side_effect=AssertionError("must not observe")) as which, \
                redirect_stdout(stdout), redirect_stderr(stderr):
            status = cli.main(list(map(str, self.arguments(output))))
        self.assertEqual(status, 2)
        opened.assert_not_called()
        which.assert_not_called()
        self.assertIn("output path already exists", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(list(output.iterdir()), [])

    def test_each_unknown_or_null_integration_warns_independently_and_exits_zero(self):
        cases = [
            (None, PROFILE["controller"], "not_configured", "matches_research_snapshot"),
            (PROFILE["model"], None, "matches_research_snapshot", "not_configured"),
            (None, None, "not_configured", "not_configured"),
            ({**PROFILE["model"], "model_id": "Other/Model"},
             {"backend": "maaframework", "version": "99.0.0"}, "unreviewed_contract", "unreviewed_contract"),
            ({**PROFILE["model"], "revision": "0" * 40, "architecture": "WrongLoader"},
             None, "unreviewed_contract", "not_configured"),
            (PROFILE["model"], {"backend": "maa", "version": "5.12.3"},
             "matches_research_snapshot", "unreviewed_contract"),
        ]
        for index, (model, controller, model_status, controller_status) in enumerate(cases):
            with self.subTest(index=index):
                self.profile.write_text(json.dumps({
                    "schema_version": 1, "model": model, "controller": controller,
                }), encoding="utf-8")
                output = self.base / f"report-{index}"
                result = self.run_cli(*self.arguments(output))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                report = self.read_report(output)
                for name, status in (("model", model_status), ("controller", controller_status)):
                    self.assertEqual(report["comparison"][name]["status"], status)
                    warning = f"{name} is {status}; no compatibility established."
                    if status in ("not_configured", "unreviewed_contract"):
                        self.assertIn(warning, result.stdout)
                    else:
                        self.assertNotIn(warning, result.stdout)
                if model_status in ("not_configured", "unreviewed_contract"):
                    self.assertIsNone(report["comparison"]["model"]["expected_architecture"])
                self.assert_local_only_message(result, output)

    def test_contradictions_keep_reports_and_exit_two_even_with_controller_warnings(self):
        for index, controller in enumerate((PROFILE["controller"], None,
                                           {"backend": "maaframework", "version": "99.0.0"})):
            with self.subTest(controller=controller):
                self.profile.write_text(json.dumps({
                    **PROFILE, "model": {**PROFILE["model"], "architecture": "WrongLoader"},
                    "controller": controller,
                }), encoding="utf-8")
                before = self.profile.read_bytes()
                output = self.base / f"report-{index}"
                result = self.run_cli(*self.arguments(output))
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("WrongLoader", result.stderr)
                self.assertIn("architecture contradicts the research snapshot", result.stderr)
                self.assertIn("diagnostic report retained", result.stderr)
                report = self.read_report(output)
                self.assertEqual(report["comparison"]["model"], {
                    "status": "contradicts_research_snapshot",
                    "expected_architecture": PROFILE["model"]["architecture"],
                })
                status = report["comparison"]["controller"]["status"]
                if status != "matches_research_snapshot":
                    self.assertIn(f"controller is {status}; no compatibility established.", result.stdout)
                else:
                    self.assertNotIn("Warning:", result.stdout)
                self.assert_local_only_message(result, output)
                self.assertEqual(self.profile.read_bytes(), before)

    def test_local_observation_os_errors_create_no_parents_or_private_diagnostics(self):
        for owner, name in ((os, "uname"), (shutil, "which")):
            with self.subTest(name=name):
                stdout, stderr = io.StringIO(), io.StringIO()
                with mock.patch.object(owner, name, side_effect=OSError("/private-marker/secret"), create=True), \
                        redirect_stdout(stdout), redirect_stderr(stderr):
                    status = cli.main(list(map(str, self.arguments(self.base / "absent/report"))))
                self.assertEqual(status, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertEqual(stderr.getvalue(),
                                 "error: invalid setup profile or local facts: cannot collect local capability facts\n")
                self.assertFalse((self.base / "absent").exists())

    def test_invalid_profile_prevents_local_observation_in_real_command_handler(self):
        self.profile.write_text(json.dumps({
            **PROFILE, "controller": {"backend": "maaframework", "version": "private-marker"},
        }), encoding="utf-8")
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(shutil, "which", side_effect=AssertionError("must not observe")) as which, \
                redirect_stdout(stdout), redirect_stderr(stderr):
            status = cli.main(list(map(str, self.arguments(self.base / "absent/report"))))
        self.assertEqual(status, 2)
        which.assert_not_called()
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("controller version", stderr.getvalue())
        self.assertNotIn("private-marker", stderr.getvalue())
        self.assertFalse((self.base / "absent").exists())

    def test_cli_requires_nonblock_before_open_but_not_other_inventory_features(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.__dict__), \
                mock.patch.object(os, "open", side_effect=AssertionError("must not open")) as opened, \
                redirect_stdout(stdout), redirect_stderr(stderr):
            os.__dict__.pop("O_NONBLOCK", None)
            status = cli.main(list(map(str, self.arguments(self.base / "absent/report"))))
            opened.assert_not_called()
        self.assertEqual(status, 2)
        self.assertIn("requires nonblocking", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")
        self.assertFalse((self.base / "absent").exists())

        output = self.base / "report"
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.__dict__), redirect_stdout(stdout), redirect_stderr(stderr):
            os.supports_dir_fd = set()
            os.__dict__.pop("O_DIRECTORY", None)
            os.__dict__.pop("O_NOFOLLOW", None)
            status = cli.main(list(map(str, self.arguments(output))))
            with self.assertRaises(InventoryError):
                cli._load_inventory_request(self.profile)
        self.assertEqual(status, 0, stderr.getvalue())
        features = self.read_report(output)["observed_local"]["inventory_features"]
        for name in ("open_dir_fd", "o_directory", "o_nofollow", "required_features_present"):
            self.assertIs(features[name], False)
        self.assertIs(features["o_nonblock"], True)

    def test_output_write_failure_keeps_partial_report_without_success_message(self):
        output = self.base / "report"
        real_open = Path.open

        class FailingWriter:
            def __init__(self, actual):
                self.actual = actual

            def __enter__(self):
                self.actual.__enter__()
                return self

            def write(self, content):
                self.actual.write(content[:20])
                self.actual.flush()
                raise OSError("injected output write failure")

            def __exit__(self, *arguments):
                return self.actual.__exit__(*arguments)

        def failing_open(path, *arguments, **kwargs):
            actual = real_open(path, *arguments, **kwargs)
            return FailingWriter(actual) if path == output / "preflight.json" else actual

        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(Path, "open", new=failing_open), redirect_stdout(stdout), redirect_stderr(stderr):
            status = cli.main(list(map(str, self.arguments(output))))
        self.assertEqual(status, 2)
        self.assertIn("injected output write failure", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(len((output / "preflight.json").read_bytes()), 20)


class InventoryReaderRegressionTests(unittest.TestCase):
    """Lock the existing reader contract before sharing its file mechanics."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.request = self.base / "private-marker.json"
        self.request.write_bytes(b'{}')

    def test_existing_inventory_errors_keep_their_exact_labels(self):
        for payload, message in (
            (b"\xff", "inventory request is not valid UTF-8"),
            (b" " * (LIMIT + 1), "inventory request exceeds the 2 MiB size limit"),
        ):
            with self.subTest(message=message):
                self.request.write_bytes(payload)
                with self.assertRaises(InventoryError) as caught:
                    cli._load_inventory_request(self.request)
                self.assertEqual(str(caught.exception), message)
        with self.assertRaises(InventoryError) as caught:
            cli._load_inventory_request(self.base / "private-marker-missing")
        self.assertEqual(str(caught.exception), "cannot read the inventory request")
        with self.assertRaises(InventoryError) as caught:
            cli._load_inventory_request(self.base)
        self.assertEqual(str(caught.exception), "cannot read the inventory request")
        with mock.patch.object(os, "fstat", return_value=SimpleNamespace(st_mode=stat.S_IFIFO)), \
                self.assertRaises(InventoryError) as caught:
            cli._load_inventory_request(self.request)
        self.assertEqual(str(caught.exception), "inventory request must be a regular file")

    def test_inventory_strict_json_error_type_is_not_wrapped(self):
        self.request.write_bytes(b'{"private-marker":0,"private-marker":1}')
        with self.assertRaises(StrictJSONError) as caught:
            cli._load_inventory_request(self.request)
        self.assertEqual(str(caught.exception), "JSON contains a duplicate object key")

    def test_inventory_platform_gate_runs_before_open(self):
        for missing in ("open_dir_fd", "O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"):
            with self.subTest(missing=missing):
                with mock.patch.dict(os.__dict__), \
                        mock.patch.object(os, "open", side_effect=AssertionError("must not open")) as opened:
                    os.supports_dir_fd = {opened}
                    if missing == "open_dir_fd":
                        os.supports_dir_fd = set()
                    else:
                        os.__dict__.pop(missing, None)
                    with self.assertRaises(InventoryError) as caught:
                        cli._load_inventory_request(self.request)
                    opened.assert_not_called()
                self.assertEqual(str(caught.exception),
                                 "inventory requires POSIX descriptor-relative no-follow file access")

    def test_inventory_reads_no_more_than_limit_plus_one_and_closes_on_failure(self):
        real_fdopen = os.fdopen
        files, reads = [], []

        class Reader:
            def __init__(self, actual):
                self.actual = actual

            def __enter__(self):
                self.actual.__enter__()
                return self

            def fileno(self):
                return self.actual.fileno()

            def read(self, size):
                reads.append(size)
                return self.actual.read(size)

            def __exit__(self, *arguments):
                return self.actual.__exit__(*arguments)

        def tracked_fdopen(*arguments, **kwargs):
            actual = real_fdopen(*arguments, **kwargs)
            files.append(actual)
            return Reader(actual)

        for payload, error_type in ((b'{}', None), (b'\xff', InventoryError),
                                    (b'{}' + b' ' * LIMIT, InventoryError),
                                    (b'{', StrictJSONError)):
            self.request.write_bytes(payload)
            with mock.patch.object(os, "fdopen", side_effect=tracked_fdopen):
                if error_type is None:
                    self.assertEqual(cli._load_inventory_request(self.request), {})
                else:
                    with self.assertRaises(error_type):
                        cli._load_inventory_request(self.request)
        self.assertEqual(reads, [LIMIT + 1] * 4)
        self.assertTrue(all(opened.closed for opened in files))

    def test_inventory_failed_descriptor_wrapping_still_closes_descriptor(self):
        real_open = os.open
        descriptors = []

        def track_open(*arguments, **kwargs):
            descriptor = real_open(*arguments, **kwargs)
            descriptors.append(descriptor)
            return descriptor

        for failure in (OSError("private-marker"), KeyboardInterrupt()):
            with self.subTest(failure=type(failure)):
                with mock.patch.object(os, "open", side_effect=track_open) as opened, \
                        mock.patch.object(os, "supports_dir_fd", os.supports_dir_fd | {opened}), \
                        mock.patch.object(os, "fdopen", side_effect=failure):
                    error_type = InventoryError if isinstance(failure, OSError) else KeyboardInterrupt
                    with self.assertRaises(error_type) as caught:
                        cli._load_inventory_request(self.request)
                if isinstance(failure, OSError):
                    self.assertEqual(str(caught.exception), "cannot read the inventory request")
                with self.assertRaises(OSError):
                    os.fstat(descriptors[-1])
        self.assertEqual(len(descriptors), 2)


class RegularObjectReaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.profile = self.base / "private-marker-profile.json"
        self.profile.write_bytes(b'{}')

    def load_profile(self):
        return cli._load_regular_object(self.profile, max_bytes=LIMIT, kind="setup profile")

    def test_shared_reader_accepts_strict_objects_with_only_nonblock_available(self):
        with mock.patch.dict(os.__dict__):
            os.supports_dir_fd = set()
            os.__dict__.pop("O_DIRECTORY", None)
            os.__dict__.pop("O_NOFOLLOW", None)
            self.assertEqual(self.load_profile(), {})

    def test_shared_reader_missing_nonblock_refuses_before_open(self):
        with mock.patch.dict(os.__dict__), \
                mock.patch.object(os, "open", side_effect=AssertionError("must not open")) as opened:
            os.__dict__.pop("O_NONBLOCK", None)
            with self.assertRaisesRegex(cli._CLIError, "requires nonblocking") as caught:
                self.load_profile()
            opened.assert_not_called()
        self.assertNotIn("private-marker", str(caught.exception))

    def test_shared_reader_errors_use_internal_setup_profile_label(self):
        for payload, message in (
            (b"\xff", "setup profile is not valid UTF-8"),
            (b" " * (LIMIT + 1), "setup profile exceeds the 2 MiB size limit"),
        ):
            self.profile.write_bytes(payload)
            with self.assertRaises(cli._CLIError) as caught:
                self.load_profile()
            self.assertEqual(str(caught.exception), message)
        self.profile.unlink()
        with self.assertRaises(cli._CLIError) as caught:
            self.load_profile()
        self.assertEqual(str(caught.exception), "cannot read the setup profile")
        self.profile.mkdir()
        with self.assertRaises(cli._CLIError) as caught:
            self.load_profile()
        self.assertEqual(str(caught.exception), "cannot read the setup profile")
        regular = self.base / "regular.json"
        regular.write_bytes(b'{}')
        with mock.patch.object(os, "fstat", return_value=SimpleNamespace(st_mode=stat.S_IFIFO)), \
                self.assertRaises(cli._CLIError) as caught:
            cli._load_regular_object(regular, max_bytes=LIMIT, kind="setup profile")
        self.assertEqual(str(caught.exception), "setup profile must be a regular file")


class SetupDocumentationTests(unittest.TestCase):
    def test_readme_describes_the_exact_command_and_honest_boundaries(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "PYTHONPATH=src python3 -m arknights_vision_agent preflight \\\n"
            "  --profile examples/setup_qwen38.json --output work/setup-report",
            readme,
        )
        start = readme.index("## Offline setup preflight")
        end = readme.index("## Development")
        self.assertLess(start, end)
        section = readme[start:end]
        for statement in (
            "preflight.json", "--profile examples/setup_qwen3vl8b.json",
            "examples declare only", "not a final model/controller choice",
            "research snapshot", "latest releases", "compatibility locks",
            "matches_research_snapshot", "not ready", "not_configured",
            "unreviewed_contract", "contradicts_research_snapshot", "exit 2",
            "diagnostic report", "Keep real reports private", "fresh output path",
            "2 MiB", "O_NONBLOCK", "reporting API", "H20", "GPU memory",
            "native tools", "training", "inference", "device", "follow-on jobs",
            "media timestamps", "controller integration",
            "docs/superpowers/specs/2026-09-07-setup-preflight-design.md",
            "docs/setup-preflight-notes.md",
        ):
            with self.subTest(statement=statement):
                self.assertIn(statement, section)

    def test_offline_runtime_dependency_list_remains_empty(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["dependencies"], [])
        source = (ROOT / "src/arknights_vision_agent/preflight.py").read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                modules = [name.name for name in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module]
            else:
                continue
            for module in modules:
                self.assertIn(module.split(".")[0], sys.stdlib_module_names)


if __name__ == "__main__":
    unittest.main()
