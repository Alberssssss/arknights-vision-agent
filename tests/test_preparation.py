import copy
import hashlib
import itertools
import json
import os
import subprocess
import sys
import unittest

from arknights_vision_agent.preparation import (
    PreparationValidationError,
    build_preparation_report,
)


def make_manifest():
    return {
        "schema_version": 1,
        "max_action_age_ms": 5000,
        "records": [
            {
                "record_id": "record-1",
                "recording_id": "recording-demo",
                "leakage_group_id": "group-demo",
                "observation": {
                    "run_id": "run-demo",
                    "observation_id": "frame-1",
                    "screen": "recruitment",
                    "available_options": ["option-a"],
                    "captured_at_ms": 1000,
                    "source": "synthetic",
                },
                "action": {
                    "run_id": "run-demo",
                    "observation_id": "frame-1",
                    "kind": "select",
                    "option_id": "option-a",
                },
                "decision_at_ms": 1100,
                "media": {
                    "kind": "video",
                    "path": "demo/source.mp4",
                    "start_ms": 0,
                    "end_ms": 1000,
                    "media_to_run_offset_ms": 0,
                },
                "label": {
                    "origin": "human",
                    "status": "pending",
                    "evidence_id": "evidence-demo",
                    "review_id": None,
                },
                "usage_permitted": False,
            }
        ],
    }


def add_independent_record(manifest, suffix, group):
    row = copy.deepcopy(manifest["records"][0])
    row["record_id"] = "record-" + suffix
    row["recording_id"] = "recording-" + suffix
    row["leakage_group_id"] = group
    row["observation"]["run_id"] = "run-" + suffix
    row["action"]["run_id"] = "run-" + suffix
    row["media"]["path"] = "demo/" + suffix + ".mp4"
    manifest["records"].append(row)
    return row


def make_eligible(row):
    row["observation"]["source"] = "recorded"
    row["label"].update(status="accepted", review_id="review-1")
    row["usage_permitted"] = True


def reverse_dictionary_order(value):
    if type(value) is dict:
        return {
            key: reverse_dictionary_order(item)
            for key, item in reversed(tuple(value.items()))
        }
    if type(value) is list:
        return [reverse_dictionary_order(item) for item in value]
    return value


class PreparationTests(unittest.TestCase):
    def test_synthetic_report_does_not_claim_eligible_data(self):
        report = build_preparation_report(make_manifest())

        self.assertEqual(report["scope"], "metadata_only")
        self.assertEqual(
            report["records"],
            [
                {
                    "record_id": "record-1",
                    "leakage_group_id": "group-demo",
                    "partition": "train",
                    "metadata_eligible": False,
                    "exclusion_reasons": [
                        "synthetic_source",
                        "label_pending",
                        "usage_not_permitted",
                    ],
                }
            ],
        )
        self.assertEqual(report["summary"]["eligible_record_count"], 0)
        self.assertEqual(
            report["summary"]["empty_partitions"], ["validation", "test"]
        )
        self.assertEqual(
            report["summary"]["eligible_empty_partitions"],
            ["train", "validation", "test"],
        )
        self.assertTrue(
            all(value is False for value in report["verification"].values())
        )

    def test_every_source_status_permission_origin_combination(self):
        for source, status, permission, origin in itertools.product(
            ("synthetic", "recorded"),
            ("pending", "accepted", "rejected"),
            (False, True),
            ("input_log", "human", "inferred"),
        ):
            with self.subTest(
                source=source,
                status=status,
                permission=permission,
                origin=origin,
            ):
                manifest = make_manifest()
                row = manifest["records"][0]
                row["observation"]["source"] = source
                row["label"].update(
                    origin=origin,
                    status=status,
                    review_id=None if status == "pending" else "review-1",
                )
                row["usage_permitted"] = permission

                report = build_preparation_report(manifest)

                expected = []
                if source == "synthetic":
                    expected.append("synthetic_source")
                if status == "pending":
                    expected.append("label_pending")
                if status == "rejected":
                    expected.append("label_rejected")
                if not permission:
                    expected.append("usage_not_permitted")
                actual = report["records"][0]
                self.assertEqual(actual["exclusion_reasons"], expected)
                self.assertIs(actual["metadata_eligible"], not expected)
                self.assertEqual(row["label"]["origin"], origin)

    def test_invalid_configuration_uses_public_error(self):
        class IntSubclass(int):
            pass

        class DictSubclass(dict):
            pass

        for seed in (
            True,
            False,
            -1,
            2**63,
            0.0,
            "0",
            None,
            [],
            {},
            IntSubclass(0),
        ):
            with self.subTest(seed_type=type(seed).__name__):
                with self.assertRaises(PreparationValidationError):
                    build_preparation_report(make_manifest(), seed=seed)

        for weights in (
            {},
            [],
            {"train": 10000, "validation": 0},
            {"train": 8000, "validation": 1000, "test": 1000, "extra": 0},
            {"train": 8000, "validation": 1000, "test": 999},
            {"train": -1, "validation": 1, "test": 10000},
            {"train": 10001, "validation": 0, "test": 0},
            {"train": 9999, "validation": True, "test": 0},
            {"train": 8000.0, "validation": 1000, "test": 1000},
            {
                "train": IntSubclass(8000),
                "validation": 1000,
                "test": 1000,
            },
            DictSubclass(train=8000, validation=1000, test=1000),
        ):
            with self.subTest(weights_type=type(weights).__name__):
                with self.assertRaises(PreparationValidationError):
                    build_preparation_report(make_manifest(), weights=weights)

    def test_valid_seed_endpoints_and_zero_weight_partitions(self):
        for seed in (0, 2**63 - 1):
            with self.subTest(seed=seed):
                report = build_preparation_report(manifest=make_manifest(), seed=seed)
                self.assertEqual(report["split"]["seed"], seed)

        for expected, weights in (
            ("train", {"train": 10000, "validation": 0, "test": 0}),
            ("validation", {"train": 0, "validation": 10000, "test": 0}),
            ("test", {"train": 0, "validation": 0, "test": 10000}),
        ):
            with self.subTest(expected=expected):
                report = build_preparation_report(make_manifest(), weights=weights)
                self.assertEqual(report["groups"][0]["partition"], expected)
                self.assertEqual(report["split"]["weights"], weights)

    def test_invalid_manifest_is_wrapped_even_when_row_is_excluded(self):
        for status, permission in (("rejected", False), ("accepted", False)):
            manifest = make_manifest()
            row = manifest["records"][0]
            row["label"].update(status=status, review_id="review-1")
            row["usage_permitted"] = permission
            row["action"]["kind"] = "private-invalid-action"

            with self.subTest(status=status):
                with self.assertRaises(PreparationValidationError):
                    build_preparation_report(manifest)

    def test_actual_hash_golden_assignments_and_buckets(self):
        vectors = (
            (
                0,
                "group-demo",
                "5bb5c0fb672c1ee08f49264458d957877177266649b0ce2bd57fcddaa59dd806",
                7382,
                "train",
            ),
            (
                0,
                "group-5",
                "214147f80233ca0cc2385e119bc8bf3a51dbefb531d8a31358f854721ee70b1c",
                8940,
                "validation",
            ),
            (
                0,
                "group-4",
                "870e08ef281d703e524f047f944b76842c06c1b6952bb3e2f0ff1708150c2d79",
                9241,
                "test",
            ),
            (
                7,
                "group-demo",
                "db4566e9689ed267263f5fe04178767fd62c4be47f533a49dacac1bc681decb9",
                5545,
                "train",
            ),
            (
                2**63 - 1,
                "组🦊",
                "8d92587705ce8e3ab2169b5f62e1933768836298a871db60b9c1c23ffc70f156",
                7622,
                "train",
            ),
        )
        for seed, group, expected_digest, bucket, expected_partition in vectors:
            with self.subTest(seed=seed, group=group, case="default"):
                manifest = make_manifest()
                manifest["records"][0]["leakage_group_id"] = group
                report = build_preparation_report(manifest, seed=seed)
                self.assertEqual(report["groups"][0]["partition"], expected_partition)

            with self.subTest(seed=seed, group=group, case="exact_bucket"):
                payload = json.dumps(
                    [seed, group],
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
                digest = hashlib.sha256(
                    b"arknights-vision-agent/split/v1\n" + payload
                )
                self.assertEqual(digest.hexdigest(), expected_digest)
                self.assertEqual(int.from_bytes(digest.digest(), "big") % 10000, bucket)
                report = build_preparation_report(
                    manifest,
                    seed=seed,
                    weights={
                        "train": bucket,
                        "validation": 1,
                        "test": 9999 - bucket,
                    },
                )
                self.assertEqual(report["groups"][0]["partition"], "validation")

    def test_actual_hash_half_open_boundaries_and_seed_change(self):
        for train, validation, test, expected in (
            (7382, 1, 2617, "validation"),
            (7382, 0, 2618, "test"),
            (7383, 0, 2617, "train"),
        ):
            with self.subTest(
                train=train, validation=validation, test=test
            ):
                report = build_preparation_report(
                    make_manifest(),
                    weights={
                        "train": train,
                        "validation": validation,
                        "test": test,
                    },
                )
                self.assertEqual(report["groups"][0]["partition"], expected)

        weights = {"train": 6000, "validation": 0, "test": 4000}
        self.assertEqual(
            build_preparation_report(make_manifest(), seed=0, weights=weights)["groups"][
                0
            ]["partition"],
            "test",
        )
        self.assertEqual(
            build_preparation_report(make_manifest(), seed=7, weights=weights)["groups"][
                0
            ]["partition"],
            "train",
        )

    def test_exact_shape_and_aggregation_across_all_partitions(self):
        manifest = make_manifest()
        validation_row = add_independent_record(manifest, "5", "group-5")
        make_eligible(validation_row)
        add_independent_record(manifest, "4", "group-4")

        report = build_preparation_report(manifest)

        self.assertEqual(
            list(report),
            [
                "schema_version",
                "scope",
                "manifest_digest",
                "split",
                "records",
                "groups",
                "summary",
                "verification",
            ],
        )
        self.assertEqual(list(report["manifest_digest"]), ["algorithm", "sha256"])
        self.assertEqual(list(report["split"]), ["algorithm", "seed", "weights"])
        self.assertEqual(
            list(report["split"]["weights"]), ["train", "validation", "test"]
        )
        self.assertEqual(
            list(report["records"][0]),
            [
                "record_id",
                "leakage_group_id",
                "partition",
                "metadata_eligible",
                "exclusion_reasons",
            ],
        )
        self.assertEqual(
            list(report["groups"][0]),
            [
                "leakage_group_id",
                "partition",
                "record_count",
                "eligible_record_count",
            ],
        )
        self.assertEqual(
            list(report["summary"]),
            [
                "record_count",
                "eligible_record_count",
                "excluded_record_count",
                "group_count",
                "eligible_group_count",
                "exclusion_reason_counts",
                "partitions",
                "empty_partitions",
                "eligible_empty_partitions",
            ],
        )
        self.assertEqual(
            report["summary"],
            {
                "record_count": 3,
                "eligible_record_count": 1,
                "excluded_record_count": 2,
                "group_count": 3,
                "eligible_group_count": 1,
                "exclusion_reason_counts": {
                    "synthetic_source": 2,
                    "label_pending": 2,
                    "label_rejected": 0,
                    "usage_not_permitted": 2,
                },
                "partitions": {
                    "train": {
                        "record_count": 1,
                        "eligible_record_count": 0,
                        "group_count": 1,
                        "eligible_group_count": 0,
                    },
                    "validation": {
                        "record_count": 1,
                        "eligible_record_count": 1,
                        "group_count": 1,
                        "eligible_group_count": 1,
                    },
                    "test": {
                        "record_count": 1,
                        "eligible_record_count": 0,
                        "group_count": 1,
                        "eligible_group_count": 0,
                    },
                },
                "empty_partitions": [],
                "eligible_empty_partitions": ["train", "test"],
            },
        )
        self.assertEqual(
            [row["record_id"] for row in report["records"]],
            ["record-1", "record-4", "record-5"],
        )
        self.assertEqual(
            [row["leakage_group_id"] for row in report["groups"]],
            ["group-4", "group-5", "group-demo"],
        )
        self.assertEqual(
            list(report["summary"]["partitions"]),
            ["train", "validation", "test"],
        )
        self.assertEqual(
            list(report["summary"]["exclusion_reason_counts"]),
            [
                "synthetic_source",
                "label_pending",
                "label_rejected",
                "usage_not_permitted",
            ],
        )
        self.assertEqual(
            list(report["summary"]["partitions"]["train"]),
            [
                "record_count",
                "eligible_record_count",
                "group_count",
                "eligible_group_count",
            ],
        )
        self.assertEqual(
            list(report["verification"]),
            [
                "media_inspected",
                "label_evidence_verified",
                "permission_verified",
                "training_started",
                "game_clear_verified",
            ],
        )

    def test_mixed_eligibility_group_stays_together_and_counts_once(self):
        manifest = make_manifest()
        eligible = add_independent_record(manifest, "eligible", "group-demo")
        make_eligible(eligible)

        report = build_preparation_report(manifest)

        self.assertEqual(len(report["groups"]), 1)
        self.assertEqual(report["groups"][0]["record_count"], 2)
        self.assertEqual(report["groups"][0]["eligible_record_count"], 1)
        self.assertEqual(report["summary"]["eligible_group_count"], 1)
        self.assertEqual(
            {row["partition"] for row in report["records"]}, {"train"}
        )
        self.assertEqual(
            {row["leakage_group_id"] for row in report["records"]},
            {"group-demo"},
        )

    def test_record_and_dictionary_order_do_not_change_report(self):
        manifest = make_manifest()
        add_independent_record(manifest, "4", "group-4")
        add_independent_record(manifest, "5", "group-5")
        reordered = reverse_dictionary_order(manifest)
        reordered["records"].reverse()

        self.assertEqual(
            build_preparation_report(manifest), build_preparation_report(reordered)
        )

    def test_assignments_ignore_unrelated_groups_size_and_eligibility(self):
        manifest = make_manifest()
        add_independent_record(manifest, "4", "group-4")
        original = build_preparation_report(manifest)
        original_assignments = {
            row["record_id"]: row["partition"] for row in original["records"]
        }

        extra = add_independent_record(manifest, "extra", "unrelated-group")
        make_eligible(extra)
        changed = build_preparation_report(manifest)
        changed_assignments = {
            row["record_id"]: row["partition"] for row in changed["records"]
        }

        self.assertEqual(
            original_assignments,
            {key: changed_assignments[key] for key in original_assignments},
        )
        self.assertNotEqual(original["summary"], changed["summary"])
        self.assertNotEqual(original["manifest_digest"], changed["manifest_digest"])

        for case in ("permission", "label"):
            candidate = make_manifest()
            row = candidate["records"][0]
            row["observation"]["source"] = "recorded"
            row["label"].update(status="accepted", review_id="review-1")
            row["usage_permitted"] = case == "label"
            if case == "label":
                row["label"]["status"] = "rejected"
            before = build_preparation_report(candidate)
            if case == "permission":
                row["usage_permitted"] = True
            else:
                row["label"]["status"] = "accepted"
            after = build_preparation_report(candidate)
            with self.subTest(case=case):
                self.assertEqual(
                    before["records"][0]["partition"],
                    after["records"][0]["partition"],
                )
                self.assertNotEqual(
                    before["records"][0]["metadata_eligible"],
                    after["records"][0]["metadata_eligible"],
                )
                self.assertNotEqual(
                    before["manifest_digest"], after["manifest_digest"]
                )

    def test_fresh_process_hash_seeds_produce_identical_reports(self):
        manifest = make_manifest()
        add_independent_record(manifest, "4", "group-4")
        add_independent_record(manifest, "5", "group-5")
        program = (
            "import json,sys; "
            "from arknights_vision_agent.preparation import build_preparation_report; "
            "print(json.dumps(build_preparation_report(json.load(sys.stdin)), "
            "sort_keys=True, ensure_ascii=False))"
        )
        outputs = []
        for hash_seed in ("1", "2"):
            environment = os.environ.copy()
            environment["PYTHONHASHSEED"] = hash_seed
            completed = subprocess.run(
                [sys.executable, "-c", program],
                input=json.dumps(manifest, ensure_ascii=False),
                text=True,
                capture_output=True,
                check=True,
                env=environment,
            )
            outputs.append(completed.stdout)

        self.assertEqual(outputs[0], outputs[1])

    def test_manifest_digest_matches_independent_canonical_reference(self):
        manifest = make_manifest()
        add_independent_record(manifest, "4", "group-4")
        expected_manifest = copy.deepcopy(manifest)
        expected_manifest["records"].sort(key=lambda row: row["record_id"])
        canonical = json.dumps(
            expected_manifest,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        expected = hashlib.sha256(
            b"arknights-vision-agent/manifest/v1\n" + canonical
        ).hexdigest()

        digest = build_preparation_report(manifest)["manifest_digest"]

        self.assertEqual(
            digest["algorithm"], "sha256-canonical-manifest-v1"
        )
        self.assertEqual(digest["sha256"], expected)
        self.assertEqual(len(digest["sha256"]), 64)
        self.assertEqual(digest["sha256"], digest["sha256"].lower())

    def test_manifest_digest_invariants_and_sensitive_declarations(self):
        manifest = make_manifest()
        add_independent_record(manifest, "4", "group-4")
        baseline = build_preparation_report(manifest)["manifest_digest"]

        reordered = reverse_dictionary_order(manifest)
        reordered["records"].reverse()
        self.assertEqual(
            baseline, build_preparation_report(reordered)["manifest_digest"]
        )

        with_options = copy.deepcopy(manifest)
        with_options["records"][0]["observation"]["available_options"] = [
            "option-a",
            "option-b",
        ]
        reversed_options = copy.deepcopy(with_options)
        reversed_options["records"][0]["observation"][
            "available_options"
        ].reverse()
        self.assertNotEqual(
            build_preparation_report(with_options)["manifest_digest"],
            build_preparation_report(reversed_options)["manifest_digest"],
        )

        changed_metadata = copy.deepcopy(manifest)
        changed_metadata["max_action_age_ms"] = 5001
        self.assertNotEqual(
            baseline,
            build_preparation_report(changed_metadata)["manifest_digest"],
        )
        self.assertEqual(
            baseline,
            build_preparation_report(manifest, seed=7)["manifest_digest"],
        )
        self.assertEqual(
            baseline,
            build_preparation_report(
                manifest,
                weights={"train": 0, "validation": 0, "test": 10000},
            )["manifest_digest"],
        )

    def test_inputs_and_returned_reports_are_deeply_detached(self):
        manifest = make_manifest()
        manifest_before = copy.deepcopy(manifest)
        weights = {"train": 8000, "validation": 1000, "test": 1000}
        weights_before = copy.deepcopy(weights)

        report = build_preparation_report(manifest, weights=weights)

        self.assertEqual(manifest, manifest_before)
        self.assertEqual(weights, weights_before)
        weights["train"] = 0
        self.assertEqual(report["split"]["weights"]["train"], 8000)
        report["split"]["weights"]["train"] = -1
        report["records"][0]["exclusion_reasons"].append("changed")
        report["groups"][0]["record_count"] = -1
        report["summary"]["partitions"]["train"]["record_count"] = -1
        report["verification"]["training_started"] = True
        fresh = build_preparation_report(manifest)

        self.assertEqual(manifest, manifest_before)
        self.assertEqual(fresh["split"]["weights"]["train"], 8000)
        self.assertNotIn("changed", fresh["records"][0]["exclusion_reasons"])
        self.assertEqual(fresh["groups"][0]["record_count"], 1)
        self.assertEqual(
            fresh["summary"]["partitions"]["train"]["record_count"], 1
        )
        self.assertIs(fresh["verification"]["training_started"], False)

        invalid = make_manifest()
        invalid["action_marker"] = "private-value"
        invalid_before = copy.deepcopy(invalid)
        with self.assertRaises(PreparationValidationError):
            build_preparation_report(invalid)
        self.assertEqual(invalid, invalid_before)

        for status in ("accepted", "rejected"):
            candidate = make_manifest()
            candidate["records"][0]["label"].update(
                status=status, review_id="review-1"
            )
            candidate_before = copy.deepcopy(candidate)
            build_preparation_report(candidate)
            with self.subTest(status=status):
                self.assertEqual(candidate, candidate_before)

    def test_public_errors_do_not_echo_private_configuration_values(self):
        cases = (
            {"seed": "private-seed-value"},
            {
                "weights": {
                    "train": 8000,
                    "validation": 1000,
                    "test": 1000,
                    "private-weight-key": 0,
                }
            },
        )
        for arguments in cases:
            with self.subTest(arguments=tuple(arguments)):
                with self.assertRaises(PreparationValidationError) as caught:
                    build_preparation_report(make_manifest(), **arguments)
                self.assertNotIn("private", str(caught.exception))

        manifest = make_manifest()
        manifest["records"][0]["action"]["kind"] = "private-action-value"
        with self.assertRaises(PreparationValidationError) as caught:
            build_preparation_report(manifest)
        self.assertNotIn("private-action-value", str(caught.exception))

    def test_report_uses_exact_algorithms_and_only_metadata_claims(self):
        report = build_preparation_report(make_manifest())

        self.assertEqual(
            report["split"]["algorithm"], "sha256-json-mod10000-v1"
        )
        self.assertEqual(
            report["verification"],
            {
                "media_inspected": False,
                "label_evidence_verified": False,
                "permission_verified": False,
                "training_started": False,
                "game_clear_verified": False,
            },
        )
        self.assertTrue(
            {
                "media",
                "action",
                "observation",
                "evidence_id",
                "review_id",
                "export",
                "readiness",
            }.isdisjoint(report)
        )
        serialized = json.dumps(report, ensure_ascii=False, sort_keys=True)
        for private_value in (
            "demo/source.mp4",
            "frame-1",
            "option-a",
            "evidence-demo",
            "review-1",
        ):
            with self.subTest(private_value=private_value):
                self.assertNotIn(private_value, serialized)

    def test_opaque_group_ids_are_not_normalized_or_trimmed(self):
        manifest = make_manifest()
        manifest["records"][0]["leakage_group_id"] = " e\N{COMBINING ACUTE ACCENT} "
        second = add_independent_record(manifest, "composed", " é ")
        make_eligible(second)

        report = build_preparation_report(manifest)

        self.assertEqual(
            [group["leakage_group_id"] for group in report["groups"]],
            [" e\N{COMBINING ACUTE ACCENT} ", " é "],
        )
        self.assertEqual(len(report["groups"]), 2)

    def test_validation_error_is_a_value_error(self):
        self.assertTrue(issubclass(PreparationValidationError, ValueError))
