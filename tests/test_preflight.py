import builtins
from contextlib import ExitStack
import copy
import importlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from arknights_vision_agent.preflight import (
    PreflightError,
    build_preflight_report,
    collect_local_facts,
    validate_setup_profile,
)


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
PROGRAMS = ("ffmpeg", "ffprobe", "adb", "nvidia-smi")


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
        self.assertTrue(all(value is False for value in report["execution"].values()))
        self.assertIn("gpu_memory", report["unmeasured"])
        report["declared"]["model"]["architecture"] = "Changed"
        self.assertEqual(profile, PROFILE)

    def test_validation_returns_a_full_deep_copy(self):
        profile = copy.deepcopy(PROFILE)
        result = validate_setup_profile(profile)
        self.assertIsNot(result, profile)
        self.assertIsNot(result["model"], profile["model"])
        self.assertIsNot(result["controller"], profile["controller"])
        result["controller"]["version"] = "1.2.3"
        result["model"]["revision"] = "0" * 40
        self.assertEqual(profile, PROFILE)

    def test_known_profile_records_the_calling_interpreter(self):
        report = build_preflight_report(PROFILE)
        self.assertEqual(report["observed_local"]["python"], {
            "implementation": sys.implementation.name,
            "version": ".".join(str(part) for part in sys.version_info[:3]),
        })

    def test_model_and_controller_may_independently_be_null(self):
        for model in (None, PROFILE["model"]):
            for controller in (None, PROFILE["controller"]):
                with self.subTest(model=model, controller=controller):
                    profile = {"schema_version": 1, "model": model,
                               "controller": controller}
                    self.assertEqual(validate_setup_profile(profile), profile)

    def test_plain_dictionary_is_required_at_each_object_boundary(self):
        class Dictionary(dict):
            pass

        class Sequence(list):
            pass

        for candidate in (None, [], Sequence(), (), "private-marker", 1, True,
                          Dictionary(PROFILE)):
            with self.subTest(candidate_type=type(candidate)):
                with self.assertRaises(PreflightError):
                    validate_setup_profile(candidate)
        for field in ("model", "controller"):
            for candidate in ([], Sequence(), (), "private-marker", False, 1,
                              Dictionary(PROFILE[field])):
                with self.subTest(field=field, candidate_type=type(candidate)):
                    profile = copy.deepcopy(PROFILE)
                    profile[field] = candidate
                    with self.assertRaises(PreflightError):
                        validate_setup_profile(profile)

    def test_each_object_rejects_missing_or_additional_keys_privately(self):
        for field in (None, "model", "controller"):
            source = PROFILE if field is None else PROFILE[field]
            for missing in source:
                with self.subTest(field=field, missing=missing):
                    profile = copy.deepcopy(PROFILE)
                    target = profile if field is None else profile[field]
                    del target[missing]
                    with self.assertRaises(PreflightError):
                        validate_setup_profile(profile)
            for extra in ("private-marker", "endpoint", "token", "path", "train",
                          "live", "command", "environment", 1):
                with self.subTest(field=field, extra=extra):
                    profile = copy.deepcopy(PROFILE)
                    target = profile if field is None else profile[field]
                    target[extra] = "private-marker"
                    with self.assertRaises(PreflightError) as caught:
                        validate_setup_profile(profile)
                    self.assertNotIn("private-marker", str(caught.exception))
                    self.assertNotIn(str(extra), str(caught.exception))

    def test_schema_version_is_exact_integer_one(self):
        class Integer(int):
            pass

        for version in (True, False, 1.0, "1", None, 0, 2, Integer(1)):
            with self.subTest(version=version):
                profile = copy.deepcopy(PROFILE)
                profile["schema_version"] = version
                with self.assertRaisesRegex(PreflightError, "schema_version"):
                    validate_setup_profile(profile)

    def test_string_fields_reject_nonplain_strings_and_nonstrings(self):
        class String(str):
            pass

        for section, field in (("model", "model_id"), ("model", "revision"),
                               ("model", "architecture"), ("controller", "backend"),
                               ("controller", "version")):
            for value in (None, True, 1, 1.0, [], {},
                          String(PROFILE[section][field])):
                with self.subTest(section=section, field=field, value_type=type(value)):
                    profile = copy.deepcopy(PROFILE)
                    profile[section][field] = value
                    with self.assertRaisesRegex(PreflightError, field):
                        validate_setup_profile(profile)

    def test_ascii_syntax_accepts_exact_upper_bounds(self):
        profile = copy.deepcopy(PROFILE)
        profile["model"] = {
            "model_id": "A" + "._-0" * 31 + "._-/" + "9" * 128,
            "revision": "0123456789abcdef" * 2 + "01234567",
            "architecture": "A" + "_9" * 63 + "z",
        }
        self.assertEqual(len(profile["model"]["model_id"].split("/")[0]), 128)
        self.assertEqual(len(profile["model"]["architecture"]), 128)
        profile["controller"] = {"backend": "maa", "version": "00001.99999.12345"}
        self.assertEqual(validate_setup_profile(profile), profile)
        profile["model"]["model_id"] = "0/a"
        profile["model"]["architecture"] = "A"
        profile["controller"]["version"] = "0.0.0"
        self.assertEqual(validate_setup_profile(profile), profile)

    def test_model_identifier_rejects_invalid_syntax(self):
        for value in ("", "A", "/A", "A/", "A/B/C", "https://A/B", "../B",
                      ".A/B", "A/_B", "A/../B", "A" * 129 + "/B",
                      "A/" + "B" * 129, " A/B", "A/B ", "A/B\n", "A/\x00B",
                      "A/B\t", "A/B\ud800", "A/中文", "A/é", "Ａ/B"):
            with self.subTest(value=ascii(value)):
                profile = copy.deepcopy(PROFILE)
                profile["model"]["model_id"] = value
                with self.assertRaisesRegex(PreflightError, "model_id"):
                    validate_setup_profile(profile)

    def test_revision_rejects_mutable_names_and_non_lowercase_hashes(self):
        for value in ("main", "latest", "v1.0", "HEAD", "a" * 39, "a" * 41,
                      "a" * 39 + "g", "A" * 40, "a" * 40 + "\n",
                      " " + "a" * 39, "０" * 40, "a" * 39 + "\ud800"):
            with self.subTest(value=ascii(value)):
                profile = copy.deepcopy(PROFILE)
                profile["model"]["revision"] = value
                with self.assertRaisesRegex(PreflightError, "revision"):
                    validate_setup_profile(profile)

    def test_architecture_rejects_invalid_syntax(self):
        for value in ("", "_A", "0A", "A" * 129, "A.B", "A-B", " A", "A ",
                      "A\n", "A\x00", "A\ud800", "é", "模型"):
            with self.subTest(value=ascii(value)):
                profile = copy.deepcopy(PROFILE)
                profile["model"]["architecture"] = value
                with self.assertRaisesRegex(PreflightError, "architecture"):
                    validate_setup_profile(profile)

    def test_controller_backend_and_version_reject_invalid_syntax(self):
        invalid_values = {
            "backend": ("", "MAA", "MaaFramework", "other", "maa ", "maa\n",
                        "maaframework\x00", "maa\ud800", "ｍaa"),
            "version": ("", "v5.12.3", "latest", "main", "1.2", "1.2.3.4",
                        "1..3", "1.2.-3", "1.2.3-beta", "1.2.3+build",
                        "100000.1.1", "1.100000.1", "1.1.100000", " 1.2.3",
                        "1.2.3 ", "1.2.3\n", "1.2.\x00", "1.2.\ud800", "１.2.3"),
        }
        for field, values in invalid_values.items():
            for value in values:
                with self.subTest(field=field, value=ascii(value)):
                    profile = copy.deepcopy(PROFILE)
                    profile["controller"][field] = value
                    with self.assertRaisesRegex(PreflightError, field):
                        validate_setup_profile(profile)

    def test_rejected_values_are_never_in_errors(self):
        for section, field in (("model", "model_id"), ("model", "revision"),
                               ("model", "architecture"), ("controller", "backend"),
                               ("controller", "version")):
            profile = copy.deepcopy(PROFILE)
            profile[section][field] = "private-marker@secret"
            with self.assertRaisesRegex(PreflightError, field) as caught:
                validate_setup_profile(profile)
            self.assertNotIn("private-marker", str(caught.exception))
            self.assertNotIn("secret", str(caught.exception))

    def test_invalid_late_controller_prevents_all_collection(self):
        profile = copy.deepcopy(PROFILE)
        profile["controller"]["version"] = "private-marker"
        with patch("arknights_vision_agent.preflight.collect_local_facts",
                   side_effect=AssertionError("collector must not run")) as collector:
            with self.assertRaisesRegex(PreflightError, "controller version") as caught:
                build_preflight_report(profile)
        collector.assert_not_called()
        self.assertNotIn("private-marker", str(caught.exception))


class ResearchComparisonTests(unittest.TestCase):
    def test_both_exact_model_snapshots_match_their_own_architecture(self):
        for model in (PROFILE["model"], MODEL_8B):
            with self.subTest(model_id=model["model_id"]):
                report = build_preflight_report({**PROFILE, "model": model})
                self.assertEqual(report["comparison"]["model"], {
                    "status": "matches_research_snapshot",
                    "expected_architecture": model["architecture"],
                })

    def test_exact_known_revisions_with_wrong_architecture_contradict(self):
        for known in (PROFILE["model"], MODEL_8B):
            with self.subTest(model_id=known["model_id"]):
                report = build_preflight_report({
                    **PROFILE, "model": {**known, "architecture": "WrongLoader"},
                })
                self.assertEqual(report["comparison"]["model"], {
                    "status": "contradicts_research_snapshot",
                    "expected_architecture": known["architecture"],
                })

    def test_unknown_id_or_revision_never_inherits_a_known_architecture(self):
        models = [
            {**PROFILE["model"], "model_id": "Other/Model"},
            {**PROFILE["model"], "model_id": "Qwen/Qwen3.8-27B-Other"},
            {**PROFILE["model"], "revision": "0" * 40},
            {**PROFILE["model"], "revision": "0" * 40, "architecture": "WrongLoader"},
            {**MODEL_8B, "revision": PROFILE["model"]["revision"]},
        ]
        for model in models:
            with self.subTest(model=model):
                report = build_preflight_report({**PROFILE, "model": model})
                self.assertEqual(report["comparison"]["model"], {
                    "status": "unreviewed_contract", "expected_architecture": None,
                })

    def test_controller_comparison_uses_backend_and_release_together(self):
        cases = [
            ("maa", "6.17.2", "matches_research_snapshot"),
            ("maaframework", "5.12.3", "matches_research_snapshot"),
            ("maa", "5.12.3", "unreviewed_contract"),
            ("maaframework", "6.17.2", "unreviewed_contract"),
            ("maa", "6.17.3", "unreviewed_contract"),
            ("maaframework", "99.0.0", "unreviewed_contract"),
        ]
        for backend, version, status in cases:
            with self.subTest(backend=backend, version=version):
                report = build_preflight_report({
                    **PROFILE, "controller": {"backend": backend, "version": version},
                })
                self.assertEqual(report["comparison"]["controller"], {"status": status})

    def test_null_integrations_are_independently_not_configured(self):
        for field in ("model", "controller"):
            report = build_preflight_report({**PROFILE, field: None})
            expected = {"status": "not_configured"}
            if field == "model":
                expected["expected_architecture"] = None
            self.assertEqual(report["comparison"][field], expected)
            other = "model" if field == "controller" else "controller"
            self.assertEqual(report["comparison"][other]["status"],
                             "matches_research_snapshot")

    def test_report_has_exact_keys_and_research_only_scope(self):
        report = build_preflight_report(PROFILE)
        self.assertEqual(set(report), {
            "schema_version", "scope", "research_snapshot_id", "declared",
            "comparison", "observed_local", "unmeasured", "execution",
        })
        self.assertIs(type(report["schema_version"]), int)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["scope"], "offline_setup_preflight")
        self.assertEqual(report["research_snapshot_id"], "repository-research-2026-09-07-v1")
        self.assertEqual(set(report["comparison"]), {"model", "controller"})
        self.assertEqual(report["unmeasured"], UNMEASURED)
        self.assertEqual(report["execution"], EXECUTION)
        self.assertTrue(all(value is False for value in report["execution"].values()))

    def test_execution_and_unmeasured_never_change_with_status_or_presence(self):
        models = [
            PROFILE["model"], MODEL_8B, None,
            {**PROFILE["model"], "architecture": "WrongLoader"},
            {**PROFILE["model"], "model_id": "Other/Model"},
            {**PROFILE["model"], "revision": "0" * 40, "architecture": "WrongLoader"},
        ]
        controllers = [PROFILE["controller"], None,
                       {"backend": "maa", "version": "6.17.2"},
                       {"backend": "maaframework", "version": "99.0.0"}]
        for model in models:
            for controller in controllers:
                for present in (None, "/private-marker/program"):
                    with self.subTest(model=model, controller=controller, present=bool(present)):
                        with patch.object(shutil, "which", return_value=present):
                            report = build_preflight_report({
                                "schema_version": 1, "model": model, "controller": controller,
                            })
                        self.assertEqual(report["unmeasured"], UNMEASURED)
                        self.assertEqual(report["execution"], EXECUTION)
                        self.assertTrue(all(value is False for value in report["execution"].values()))

    def test_report_containers_are_detached_across_calls_and_from_input(self):
        profile = copy.deepcopy(PROFILE)
        first = build_preflight_report(profile)
        second = build_preflight_report(profile)
        first["declared"]["controller"]["version"] = "1.2.3"
        first["comparison"]["model"]["expected_architecture"] = "Changed"
        first["observed_local"]["python"].clear()
        first["observed_local"]["inventory_features"].clear()
        first["observed_local"]["executables_on_path"].clear()
        first["unmeasured"].clear()
        first["execution"]["training_started"] = True
        self.assertEqual(profile, PROFILE)
        self.assertEqual(second, build_preflight_report(PROFILE))


class LocalFactsTests(unittest.TestCase):
    def test_real_collector_reports_current_host_and_exact_feature_names(self):
        facts = collect_local_facts()
        self.assertEqual(set(facts), {
            "python", "platform", "os_name", "machine", "inventory_features",
            "executables_on_path",
        })
        self.assertEqual(facts["python"], {
            "implementation": sys.implementation.name,
            "version": ".".join(str(part) for part in sys.version_info[:3]),
        })
        self.assertEqual(facts["platform"], sys.platform)
        self.assertEqual(facts["os_name"], os.name)
        self.assertEqual(facts["machine"], os.uname().machine if hasattr(os, "uname") else None)
        features = {
            "posix": os.name == "posix", "open_dir_fd": os.open in os.supports_dir_fd,
            "o_directory": hasattr(os, "O_DIRECTORY"),
            "o_nofollow": hasattr(os, "O_NOFOLLOW"),
            "o_nonblock": hasattr(os, "O_NONBLOCK"),
        }
        self.assertEqual(facts["inventory_features"], {
            **features, "required_features_present": all(features.values()),
        })
        self.assertEqual(facts["executables_on_path"], {
            name: shutil.which(name) is not None for name in PROGRAMS
        })

    def test_low_level_observations_are_preserved_but_discovered_paths_are_not(self):
        with patch.object(sys, "implementation", SimpleNamespace(name="otherpython")), \
                patch.object(sys, "version_info", SimpleNamespace(major=9, minor=8, micro=7)), \
                patch.object(sys, "platform", "otheros"), \
                patch.object(os, "uname", return_value=SimpleNamespace(machine="othercpu"), create=True), \
                patch.object(shutil, "which", side_effect=lambda name: f"/private-marker/{name}") as which:
            facts = collect_local_facts()
        self.assertEqual(facts["python"], {"implementation": "otherpython", "version": "9.8.7"})
        self.assertEqual(facts["platform"], "otheros")
        self.assertEqual(facts["machine"], "othercpu")
        self.assertEqual(facts["executables_on_path"], dict.fromkeys(PROGRAMS, True))
        self.assertEqual(which.call_args_list, [unittest.mock.call(name) for name in PROGRAMS])
        self.assertNotIn("private-marker", json.dumps(facts))

    def test_path_presence_uses_none_not_truthiness(self):
        with patch.object(shutil, "which", return_value=""):
            facts = collect_local_facts()
        self.assertEqual(facts["executables_on_path"], dict.fromkeys(PROGRAMS, True))

    def test_api_reports_all_absent_features_without_requiring_posix_or_uname(self):
        with patch.dict(os.__dict__), patch.object(shutil, "which", return_value=None):
            os.name = "nt"
            os.supports_dir_fd = set()
            for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK", "uname"):
                os.__dict__.pop(name, None)
            report = build_preflight_report(PROFILE)
        facts = report["observed_local"]
        self.assertEqual(facts["os_name"], "nt")
        self.assertIsNone(facts["machine"])
        self.assertEqual(facts["inventory_features"], dict.fromkeys((
            "posix", "open_dir_fd", "o_directory", "o_nofollow", "o_nonblock",
            "required_features_present",
        ), False))
        self.assertEqual(facts["executables_on_path"], dict.fromkeys(PROGRAMS, False))
        self.assertEqual(report["execution"], EXECUTION)

    def test_inventory_conjunction_requires_each_of_the_five_features(self):
        for missing in (None, "posix", "open_dir_fd", "o_directory", "o_nofollow", "o_nonblock"):
            with self.subTest(missing=missing):
                with patch.dict(os.__dict__), patch.object(shutil, "which", return_value=None):
                    os.name = "posix"
                    os.supports_dir_fd = {os.open}
                    for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"):
                        os.__dict__.setdefault(flag, 1)
                    if missing == "posix":
                        os.name = "nt"
                    elif missing == "open_dir_fd":
                        os.supports_dir_fd = set()
                    elif missing is not None:
                        del os.__dict__[missing.upper()]
                    features = collect_local_facts()["inventory_features"]
                self.assertIs(features["required_features_present"], missing is None)
                for feature in set(features) - {"required_features_present"}:
                    self.assertIs(features[feature], feature != missing)

    def test_uname_and_path_os_errors_have_only_generic_diagnostics(self):
        for owner, name in ((os, "uname"), (shutil, "which")):
            for operation in (collect_local_facts, lambda: build_preflight_report(PROFILE)):
                with self.subTest(name=name, operation=operation):
                    with patch.object(owner, name, side_effect=OSError("/private-marker/secret"), create=True):
                        with self.assertRaises(PreflightError) as caught:
                            operation()
                    self.assertEqual(str(caught.exception), "cannot collect local capability facts")

    def test_real_report_does_not_launch_connect_scan_or_import_optional_runtimes(self):
        original_import = builtins.__import__
        original_import_module = importlib.import_module
        forbidden = {"torch", "transformers", "vllm", "maa", "MaaFramework", "av", "cv2"}

        def guarded_import(name, *args, **kwargs):
            if name.split(".")[0] in forbidden:
                raise AssertionError("optional runtime import attempted")
            return original_import(name, *args, **kwargs)

        def guarded_import_module(name, *args, **kwargs):
            if name.split(".")[0] in forbidden:
                raise AssertionError("optional runtime import attempted")
            return original_import_module(name, *args, **kwargs)

        with ExitStack() as stack:
            for owner, name in ((subprocess, "Popen"), (socket, "create_connection"),
                                (socket.socket, "connect"), (socket, "gethostname"),
                                (os, "system"), (os, "scandir"), (os, "walk"),
                                (Path, "glob"), (Path, "rglob")):
                stack.enter_context(patch.object(owner, name, side_effect=AssertionError("forbidden operation")))
            stack.enter_context(patch.object(builtins, "__import__", new=guarded_import))
            stack.enter_context(patch.object(importlib, "import_module", new=guarded_import_module))
            for presence in (None, "/private-marker/executable"):
                with patch.object(shutil, "which", return_value=presence):
                    report = build_preflight_report(PROFILE)
                self.assertEqual(report["execution"], EXECUTION)
                self.assertEqual(report["unmeasured"], UNMEASURED)
                self.assertNotIn("private-marker", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
