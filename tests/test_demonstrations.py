import copy
import unittest

from arknights_vision_agent.demonstrations import (
    ManifestValidationError,
    validate_manifest,
)
from arknights_vision_agent.identifiers import is_valid_identifier


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


class ManifestTests(unittest.TestCase):
    def test_returns_detached_validated_copy_without_media(self):
        original = make_manifest()
        before = copy.deepcopy(original)

        result = validate_manifest(original)

        self.assertEqual(result, original)
        self.assertIsNot(result, original)
        result["records"][0]["observation"]["available_options"].append("changed")
        result["records"][0]["media"]["path"] = "changed.mp4"
        self.assertEqual(original, before)

    def test_validation_error_is_a_value_error(self):
        self.assertTrue(issubclass(ManifestValidationError, ValueError))


class IdentifierTests(unittest.TestCase):
    def test_accepts_opaque_unicode_without_normalizing_it(self):
        for value in (
            "identifier",
            "  identifier  ",
            "运行-一",
            "e\N{COMBINING ACUTE ACCENT}",
            "x" * 128,
        ):
            with self.subTest(value=value):
                self.assertTrue(is_valid_identifier(value))

    def test_rejects_invalid_identifiers(self):
        class StringSubclass(str):
            pass

        for value in ("", " \t", "x" * 129, "\ud800", 1, True, None, StringSubclass("id")):
            with self.subTest(value_type=type(value).__name__):
                self.assertFalse(is_valid_identifier(value))


class SchemaValidationTests(unittest.TestCase):
    def assert_invalid(self, manifest):
        before = copy.deepcopy(manifest)
        with self.assertRaises(ManifestValidationError):
            validate_manifest(manifest)
        self.assertEqual(manifest, before)

    def test_rejects_missing_and_unknown_fields_at_every_object_level(self):
        locations = (
            (),
            ("records", 0),
            ("records", 0, "observation"),
            ("records", 0, "action"),
            ("records", 0, "media"),
            ("records", 0, "label"),
        )
        for location in locations:
            template = make_manifest()
            target = template
            for component in location:
                target = target[component]
            for key in tuple(target):
                value = make_manifest()
                changed = value
                for component in location:
                    changed = changed[component]
                del changed[key]
                with self.subTest(location=location, case="missing", key=key):
                    self.assert_invalid(value)

            value = make_manifest()
            target = value
            for component in location:
                target = target[component]
            target["untrusted_extension"] = "private-marker"
            with self.subTest(location=location, case="unknown"):
                self.assert_invalid(value)

    def test_rejects_nonplain_objects_and_lists(self):
        class DictSubclass(dict):
            pass

        class ListSubclass(list):
            pass

        cases = []
        value = make_manifest()
        cases.append(DictSubclass(value))
        for field in ("record", "observation", "action", "media", "label"):
            value = make_manifest()
            record = value["records"][0]
            if field == "record":
                value["records"][0] = DictSubclass(record)
            else:
                record[field] = DictSubclass(record[field])
            cases.append(value)
        value = make_manifest()
        value["records"] = ListSubclass(value["records"])
        cases.append(value)
        value = make_manifest()
        options = value["records"][0]["observation"]["available_options"]
        value["records"][0]["observation"]["available_options"] = ListSubclass(options)
        cases.append(value)

        for index, value in enumerate(cases):
            with self.subTest(index=index):
                self.assert_invalid(value)

    def test_rejects_nonplain_strings_for_ids_and_enums(self):
        class StringSubclass(str):
            pass

        fields = (
            ("record_id",),
            ("recording_id",),
            ("leakage_group_id",),
            ("observation", "run_id"),
            ("observation", "screen"),
            ("observation", "source"),
            ("action", "kind"),
            ("media", "kind"),
            ("media", "path"),
            ("label", "origin"),
            ("label", "status"),
            ("label", "evidence_id"),
        )
        for path in fields:
            value = make_manifest()
            target = value["records"][0]
            for component in path[:-1]:
                target = target[component]
            target[path[-1]] = StringSubclass(target[path[-1]])
            with self.subTest(path=path):
                self.assert_invalid(value)

    def test_requires_exact_schema_version_one(self):
        for version in (True, False, 0, 2, 1.0, "1", None):
            value = make_manifest()
            value["schema_version"] = version
            with self.subTest(version=version):
                self.assert_invalid(value)

    def test_requires_one_to_ten_thousand_records(self):
        value = make_manifest()
        value["records"] = []
        self.assert_invalid(value)

        value = make_manifest()
        value["records"] = [value["records"][0]] * 10001
        self.assert_invalid(value)

    def test_rejects_invalid_manifest_specific_identifiers(self):
        fields = (
            ("record_id",),
            ("recording_id",),
            ("leakage_group_id",),
            ("label", "evidence_id"),
            ("label", "review_id"),
        )
        values = ("", " \n", "x" * 129, "\ud800", 7, True, None)
        for path in fields:
            for invalid in values:
                value = make_manifest()
                record = value["records"][0]
                if path == ("label", "review_id"):
                    record["label"]["status"] = "accepted"
                target = record
                for component in path[:-1]:
                    target = target[component]
                target[path[-1]] = invalid
                with self.subTest(path=path, value_type=type(invalid).__name__):
                    self.assert_invalid(value)

    def test_rejects_invalid_media_and_label_enums(self):
        cases = (
            (("media", "kind"), ("audio", "IMAGE", "", 1, None)),
            (("label", "origin"), ("model", "HUMAN", "", 1, None)),
            (("label", "status"), ("approved", "PENDING", "", 1, None)),
        )
        for path, invalid_values in cases:
            for invalid in invalid_values:
                value = make_manifest()
                value["records"][0][path[0]][path[1]] = invalid
                with self.subTest(path=path, value=invalid):
                    self.assert_invalid(value)

    def test_rejects_boolean_noninteger_and_out_of_range_clocks(self):
        unsigned_fields = (
            ("max_action_age_ms",),
            ("records", 0, "decision_at_ms"),
            ("records", 0, "observation", "captured_at_ms"),
            ("records", 0, "media", "start_ms"),
            ("records", 0, "media", "end_ms"),
        )
        for path in unsigned_fields:
            for invalid in (True, False, -1, 2**63, 1.5, "1", None):
                value = make_manifest()
                target = value
                for component in path[:-1]:
                    target = target[component]
                target[path[-1]] = invalid
                with self.subTest(path=path, invalid=invalid):
                    self.assert_invalid(value)

        for invalid in (True, False, -(2**63) - 1, 2**63, 1.5, "0", None):
            value = make_manifest()
            value["records"][0]["media"]["media_to_run_offset_ms"] = invalid
            with self.subTest(offset=invalid):
                self.assert_invalid(value)

    def test_requires_exact_boolean_permission(self):
        for invalid in (0, 1, "false", None, [], {}):
            value = make_manifest()
            value["records"][0]["usage_permitted"] = invalid
            with self.subTest(invalid=invalid):
                self.assert_invalid(value)

    def test_enforces_review_id_status_relationship(self):
        value = make_manifest()
        value["records"][0]["label"]["review_id"] = "review-1"
        self.assert_invalid(value)

        invalid_review_ids = (None, "", " \t", "x" * 129, "\ud800", 1, True)
        for status in ("accepted", "rejected"):
            for review_id in invalid_review_ids:
                value = make_manifest()
                value["records"][0]["label"].update(
                    status=status,
                    review_id=review_id,
                )
                with self.subTest(status=status, review_id=review_id):
                    self.assert_invalid(value)

    def test_accepts_each_label_declaration(self):
        declarations = (
            ("input_log", "pending", None),
            ("human", "accepted", "review-1"),
            ("inferred", "accepted", "review-2"),
            ("inferred", "rejected", "review-3"),
        )
        for origin, status, review_id in declarations:
            value = make_manifest()
            value["records"][0]["label"].update(
                origin=origin,
                status=status,
                review_id=review_id,
            )
            with self.subTest(origin=origin, status=status):
                self.assertEqual(value, validate_manifest(value))


class ActionIntegrationTests(unittest.TestCase):
    def assert_invalid(self, manifest):
        with self.assertRaises(ManifestValidationError):
            validate_manifest(manifest)

    def test_wraps_shared_action_guard_failures_with_record_index(self):
        cases = []
        value = make_manifest()
        value["records"][0]["action"]["option_id"] = "unavailable"
        cases.append(value)
        value = make_manifest()
        value["records"][0]["action"]["run_id"] = "other-run"
        cases.append(value)
        value = make_manifest()
        value["records"][0]["action"]["observation_id"] = "other-frame"
        cases.append(value)
        value = make_manifest()
        value["records"][0]["observation"]["screen"] = "battle"
        cases.append(value)

        for value in cases:
            with self.subTest(case=cases.index(value)):
                with self.assertRaisesRegex(ManifestValidationError, r"record 1"):
                    validate_manifest(value)

    def test_rejects_future_and_stale_select_but_accepts_exact_age_boundary(self):
        future = make_manifest()
        future["records"][0]["decision_at_ms"] = 999
        self.assert_invalid(future)

        stale = make_manifest()
        stale["max_action_age_ms"] = 99
        self.assert_invalid(stale)

        boundary = make_manifest()
        boundary["max_action_age_ms"] = 100
        self.assertEqual(boundary, validate_manifest(boundary))

    def test_rejects_live_observations(self):
        value = make_manifest()
        value["records"][0]["observation"]["source"] = "live"
        self.assert_invalid(value)

    def test_rejects_string_subclasses_through_shared_action_validation(self):
        class StringSubclass(str):
            pass

        cases = (
            ("observation", "observation_id"),
            ("observation", "available_options"),
            ("action", "run_id"),
            ("action", "observation_id"),
            ("action", "option_id"),
        )
        for object_name, field in cases:
            value = make_manifest()
            target = value["records"][0][object_name]
            if field == "available_options":
                target[field][0] = StringSubclass(target[field][0])
            else:
                target[field] = StringSubclass(target[field])
            with self.subTest(object_name=object_name, field=field):
                self.assert_invalid(value)

    def test_rejects_future_stop_but_allows_stale_stop(self):
        future = make_manifest()
        record = future["records"][0]
        record["action"] = {
            "run_id": "run-demo",
            "observation_id": "frame-1",
            "kind": "stop",
        }
        record["decision_at_ms"] = 999
        self.assert_invalid(future)

        stale = make_manifest()
        record = stale["records"][0]
        record["action"] = {
            "run_id": "run-demo",
            "observation_id": "frame-1",
            "kind": "stop",
        }
        record["decision_at_ms"] = 10000
        stale["max_action_age_ms"] = 0
        self.assertEqual(stale, validate_manifest(stale))


class MediaValidationTests(unittest.TestCase):
    def assert_invalid(self, manifest):
        with self.assertRaises(ManifestValidationError):
            validate_manifest(manifest)

    def test_accepts_unicode_length_boundary_and_literal_characters(self):
        paths = (
            "演示/源文件.mp4",
            "assets/$source%20.mp4",
            "a" * 1020 + ".mp4",
        )
        for path in paths:
            value = make_manifest()
            value["records"][0]["media"]["path"] = path
            with self.subTest(path_length=len(path)):
                self.assertEqual(value, validate_manifest(value))

    def test_rejects_invalid_media_paths(self):
        paths = (
            "",
            "a" * 1021 + ".mp4",
            "/absolute/source.mp4",
            "~/source.mp4",
            "https://example.test/source.mp4",
            "C:/source.mp4",
            "dir\\source.mp4",
            "dir//source.mp4",
            "./source.mp4",
            "dir/./source.mp4",
            "../source.mp4",
            "dir/../source.mp4",
            "dir/\nsource.mp4",
            "dir/\x7fsource.mp4",
            "dir/\ud800source.mp4",
        )
        for path in paths:
            value = make_manifest()
            value["records"][0]["media"]["path"] = path
            with self.subTest(path_length=len(path)):
                self.assert_invalid(value)

        for path in (1, True, None, [], {}):
            value = make_manifest()
            value["records"][0]["media"]["path"] = path
            with self.subTest(path_type=type(path).__name__):
                self.assert_invalid(value)

    def test_enforces_media_windows_and_clock_mapping(self):
        cases = []
        value = make_manifest()
        value["records"][0]["media"].update(start_ms=1001, end_ms=1000)
        cases.append(value)
        value = make_manifest()
        value["records"][0]["media"].update(kind="image", start_ms=0, end_ms=1000)
        cases.append(value)
        value = make_manifest()
        value["records"][0]["media"].update(
            start_ms=0,
            end_ms=1000,
            media_to_run_offset_ms=-1,
        )
        value["records"][0]["observation"]["captured_at_ms"] = 999
        cases.append(value)
        value = make_manifest()
        value["records"][0]["media"]["end_ms"] = 999
        cases.append(value)

        for index, value in enumerate(cases):
            with self.subTest(index=index):
                self.assert_invalid(value)

    def test_accepts_image_points_and_nonzero_offsets(self):
        image = make_manifest()
        image["records"][0]["media"].update(kind="image", start_ms=1000)
        self.assertEqual(image, validate_manifest(image))

        positive = make_manifest()
        positive["records"][0]["media"].update(end_ms=900, media_to_run_offset_ms=100)
        self.assertEqual(positive, validate_manifest(positive))

        negative = make_manifest()
        negative["records"][0]["media"].update(
            start_ms=200,
            end_ms=1200,
            media_to_run_offset_ms=-200,
        )
        self.assertEqual(negative, validate_manifest(negative))

    def test_accepts_valid_unsigned_and_signed_limits(self):
        unsigned = make_manifest()
        unsigned["max_action_age_ms"] = 2**63 - 1
        record = unsigned["records"][0]
        record["decision_at_ms"] = 2**63 - 1
        record["observation"]["captured_at_ms"] = 2**63 - 1
        record["media"].update(start_ms=2**63 - 1, end_ms=2**63 - 1)
        self.assertEqual(unsigned, validate_manifest(unsigned))

        positive_offset = make_manifest()
        record = positive_offset["records"][0]
        record["decision_at_ms"] = 2**63 - 1
        record["observation"]["captured_at_ms"] = 2**63 - 1
        record["media"].update(
            kind="image",
            start_ms=0,
            end_ms=0,
            media_to_run_offset_ms=2**63 - 1,
        )
        self.assertEqual(positive_offset, validate_manifest(positive_offset))

        negative_offset = make_manifest()
        record = negative_offset["records"][0]
        record["decision_at_ms"] = 0
        record["observation"]["captured_at_ms"] = 0
        record["media"].update(
            kind="image",
            start_ms=2**63 - 1,
            end_ms=2**63 - 1,
            media_to_run_offset_ms=-(2**63) + 1,
        )
        self.assertEqual(negative_offset, validate_manifest(negative_offset))

    def test_minimum_offset_is_in_range_but_cannot_map_nonnegative_media(self):
        value = make_manifest()
        record = value["records"][0]
        record["decision_at_ms"] = 0
        record["observation"]["captured_at_ms"] = 0
        record["media"].update(
            kind="image",
            start_ms=2**63 - 1,
            end_ms=2**63 - 1,
            media_to_run_offset_ms=-(2**63),
        )
        self.assert_invalid(value)


def add_distinct_record(manifest):
    record = copy.deepcopy(manifest["records"][0])
    record["record_id"] = "record-2"
    record["observation"]["observation_id"] = "frame-2"
    record["action"]["observation_id"] = "frame-2"
    manifest["records"].append(record)
    return record


class WholeManifestValidationTests(unittest.TestCase):
    def assert_second_record_conflict(self, manifest):
        with self.assertRaisesRegex(ManifestValidationError, r"record 2"):
            validate_manifest(manifest)

    def test_rejects_duplicate_record_ids(self):
        value = make_manifest()
        record = add_distinct_record(value)
        record["record_id"] = value["records"][0]["record_id"]
        self.assert_second_record_conflict(value)

    def test_rejects_duplicate_run_observation_pairs(self):
        value = make_manifest()
        record = add_distinct_record(value)
        record["observation"]["observation_id"] = "frame-1"
        record["action"]["observation_id"] = "frame-1"
        self.assert_second_record_conflict(value)

    def test_rejects_run_provenance_conflicts_on_ineligible_rows(self):
        cases = []
        value = make_manifest()
        record = add_distinct_record(value)
        record["leakage_group_id"] = "other-group"
        cases.append(value)

        value = make_manifest()
        record = add_distinct_record(value)
        record["observation"]["source"] = "recorded"
        cases.append(value)

        for index, value in enumerate(cases):
            with self.subTest(index=index):
                self.assertFalse(value["records"][1]["usage_permitted"])
                self.assertEqual("pending", value["records"][1]["label"]["status"])
                self.assert_second_record_conflict(value)

    def test_rejects_recording_provenance_conflicts(self):
        cases = []

        value = make_manifest()
        record = add_distinct_record(value)
        record["observation"]["run_id"] = "run-2"
        record["action"]["run_id"] = "run-2"
        record["leakage_group_id"] = "other-group"
        cases.append(value)

        value = make_manifest()
        record = add_distinct_record(value)
        record["observation"].update(run_id="run-2", source="recorded")
        record["action"]["run_id"] = "run-2"
        cases.append(value)

        value = make_manifest()
        record = add_distinct_record(value)
        record["media"]["path"] = "demo/other-source.mp4"
        cases.append(value)

        value = make_manifest()
        record = add_distinct_record(value)
        record["media"].update(kind="image", start_ms=1000)
        cases.append(value)

        for index, value in enumerate(cases):
            with self.subTest(index=index):
                self.assert_second_record_conflict(value)

    def test_rejects_one_path_assigned_to_multiple_recordings(self):
        value = make_manifest()
        record = add_distinct_record(value)
        record["recording_id"] = "recording-2"
        self.assert_second_record_conflict(value)

    def test_rejects_different_offsets_for_one_run_recording_pair(self):
        value = make_manifest()
        record = add_distinct_record(value)
        record["media"].update(
            start_ms=100,
            end_ms=1100,
            media_to_run_offset_ms=-100,
        )
        self.assert_second_record_conflict(value)

    def test_consistency_rules_include_rejected_rows(self):
        value = make_manifest()
        record = add_distinct_record(value)
        record["record_id"] = "record-1"
        record["label"].update(status="rejected", review_id="review-1")
        self.assert_second_record_conflict(value)

    def test_allows_multiple_runs_per_recording(self):
        value = make_manifest()
        record = add_distinct_record(value)
        record["observation"]["run_id"] = "run-2"
        record["action"]["run_id"] = "run-2"
        self.assertEqual(value, validate_manifest(value))

    def test_allows_multiple_recordings_per_run(self):
        value = make_manifest()
        record = add_distinct_record(value)
        record["recording_id"] = "recording-2"
        record["media"]["path"] = "demo/source-2.mp4"
        self.assertEqual(value, validate_manifest(value))

    def test_allows_repeated_evidence_and_review_ids(self):
        value = make_manifest()
        first = value["records"][0]
        first["label"].update(status="accepted", review_id="review-shared")
        record = add_distinct_record(value)
        record["label"].update(status="accepted", review_id="review-shared")
        self.assertEqual(
            first["label"]["evidence_id"],
            record["label"]["evidence_id"],
        )
        self.assertEqual(value, validate_manifest(value))

    def test_allows_distinct_sources_in_distinct_runs_and_assets(self):
        value = make_manifest()
        record = add_distinct_record(value)
        record["observation"].update(run_id="run-recorded", source="recorded")
        record["action"]["run_id"] = "run-recorded"
        record["recording_id"] = "recording-recorded"
        record["leakage_group_id"] = "group-recorded"
        record["media"]["path"] = "recorded/source.mp4"
        self.assertEqual(value, validate_manifest(value))

    def test_row_order_is_irrelevant(self):
        value = make_manifest()
        record = add_distinct_record(value)
        record["recording_id"] = "recording-2"
        record["media"]["path"] = "demo/source-2.mp4"
        reversed_value = copy.deepcopy(value)
        reversed_value["records"].reverse()

        self.assertEqual(value, validate_manifest(value))
        self.assertEqual(reversed_value, validate_manifest(reversed_value))

    def test_accepts_ten_thousand_consistent_records(self):
        value = make_manifest()
        template = value["records"][0]
        records = []
        for index in range(10000):
            record = copy.deepcopy(template)
            record["record_id"] = f"record-{index}"
            record["observation"]["observation_id"] = f"frame-{index}"
            record["action"]["observation_id"] = f"frame-{index}"
            records.append(record)
        value["records"] = records

        result = validate_manifest(value)

        self.assertEqual(10000, len(result["records"]))
        self.assertEqual(value, result)

    def test_conflict_errors_do_not_echo_identifiers(self):
        value = make_manifest()
        marker = "do-not-echo-conflicting-id"
        value["records"][0]["record_id"] = marker
        record = add_distinct_record(value)
        record["record_id"] = marker

        with self.assertRaises(ManifestValidationError) as caught:
            validate_manifest(value)

        self.assertNotIn(marker, str(caught.exception))


class FailureHygieneTests(unittest.TestCase):
    def test_rejection_does_not_mutate_or_echo_submitted_value(self):
        value = make_manifest()
        marker = "do-not-echo-private-marker"
        value["records"][0]["media"]["path"] = marker + ":bad"
        before = copy.deepcopy(value)

        with self.assertRaises(ManifestValidationError) as caught:
            validate_manifest(value)

        self.assertEqual(before, value)
        self.assertNotIn(marker, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
