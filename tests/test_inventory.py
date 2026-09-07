from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from arknights_vision_agent import inventory

from arknights_vision_agent.inventory import (
    InventoryError,
    build_inventory,
    validate_inventory_request,
)


def request_for(*pairs):
    return {
        "schema_version": 1,
        "assets": [{"asset_id": identifier, "path": path} for identifier, path in pairs],
    }


class InventoryTests(unittest.TestCase):
    def test_known_bytes_and_detached_validation(self):
        request = request_for(("asset-a", "source.bin"))
        validated = validate_inventory_request(request)
        self.assertEqual(request, validated)
        self.assertIsNot(request, validated)
        self.assertIsNot(request["assets"], validated["assets"])
        self.assertIsNot(request["assets"][0], validated["assets"][0])
        validated["assets"][0]["asset_id"] = "changed"
        self.assertEqual(request["assets"][0]["asset_id"], "asset-a")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.bin").write_bytes(b"abc")
            report = build_inventory(
                request, media_root=root, max_file_bytes=3, max_total_bytes=3
            )
            self.assertEqual(report["assets"], [{
                "asset_id": "asset-a", "path": "source.bin", "size_bytes": 3,
                "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            }])
            self.assertEqual(report["summary"], {
                "asset_count": 1, "total_bytes": 3, "duplicate_group_count": 0,
            })
            self.assertEqual((root / "source.bin").read_bytes(), b"abc")


class InventoryValidationTests(unittest.TestCase):
    def assert_invalid(self, request, message=None):
        with self.assertRaises(InventoryError) as caught:
            validate_inventory_request(request)
        if message:
            self.assertIn(message, str(caught.exception))
        self.assertNotIn("private-marker", str(caught.exception))

    def test_request_requires_exact_plain_object_and_keys(self):
        class DictSubclass(dict):
            pass

        valid = request_for(("asset-a", "source.bin"))
        for request in (None, [], (), DictSubclass(valid), {},
                        {"assets": valid["assets"]},
                        {"schema_version": 1}, {**valid, "private-marker": 1}):
            with self.subTest(request_type=type(request)):
                self.assert_invalid(request, "fields")

    def test_schema_version_is_exact_integer_one(self):
        for version in (True, False, 0, 2, 1.0, "1", None):
            with self.subTest(version=version):
                request = request_for(("asset-a", "source.bin"))
                request["schema_version"] = version
                self.assert_invalid(request, "schema_version")

    def test_asset_list_requires_plain_list_with_one_to_thousand_entries(self):
        class ListSubclass(list):
            pass

        for assets in ([], {}, None, (), ListSubclass([{}])):
            with self.subTest(assets_type=type(assets)):
                self.assert_invalid({"schema_version": 1, "assets": assets}, "assets")
        thousand = request_for(*[(f"asset-{i}", f"file-{i}") for i in range(1000)])
        self.assertEqual(validate_inventory_request(thousand), thousand)
        thousand["assets"].append({"asset_id": "extra", "path": "extra"})
        self.assert_invalid(thousand, "assets")

    def test_asset_requires_exact_plain_object_and_fields(self):
        class DictSubclass(dict):
            pass

        for asset in (None, [], {}, {"asset_id": "private-marker"},
                      {"path": "private-marker"},
                      {"asset_id": "a", "path": "a", "private-marker": 1},
                      DictSubclass(asset_id="a", path="a")):
            with self.subTest(asset_type=type(asset)):
                self.assert_invalid({"schema_version": 1, "assets": [asset]}, "asset 1")

    def test_identifiers_preserve_existing_opaque_identifier_contract(self):
        class StringSubclass(str):
            pass

        for identifier in (None, 1, True, "", " \t", "x" * 129, "\ud800", StringSubclass("a")):
            with self.subTest(identifier=repr(identifier)):
                self.assert_invalid(request_for((identifier, "source.bin")), "asset_id")
        for identifier in ("x" * 128, "a/b", " 空格 ", "a\n"):
            request = request_for((identifier, "source.bin"))
            self.assertEqual(validate_inventory_request(request), request)

    def test_duplicate_ids_or_literal_paths_fail_at_original_index(self):
        for pairs in ((("same", "a"), ("same", "b")),
                      (("first", "same"), ("second", "same"))):
            with self.subTest(pairs=pairs):
                self.assert_invalid(request_for(*pairs), "asset 2 repeats")

    def test_forbidden_path_forms_are_rejected(self):
        class StringSubclass(str):
            pass

        forbidden = [None, True, 1, "", "x" * 1025, StringSubclass("a"),
                     "/absolute", "~owner/file", "~/file", "a\\b", "C:/a", "a:b",
                     "https://example/a", "a//b", "a/", "./a", "a/./b", ".", "..",
                     "../a", "a/../b", "a/..", "a/.", "\ud800"]
        forbidden.extend(f"a{chr(value)}b" for value in (*range(32), *range(127, 160)))
        for path in forbidden:
            with self.subTest(path=repr(path)):
                self.assert_invalid(request_for(("private-marker", path)), "path")

    def test_paths_are_literal_not_normalized_or_expanded(self):
        pairs = [(str(i), path) for i, path in enumerate(
            ("a", "x" * 1024, "嵌套/媒体.txt", "$HOME/file", "a%2fb", "a%2F..",
             "space name/a", "a/~name", "a*.bin", "a?.bin", "é", "e\u0301", "A", "a\u200b")
        )]
        request = request_for(*pairs)
        self.assertEqual(validate_inventory_request(request), request)

    def test_validation_does_no_filesystem_io(self):
        request = request_for(("asset-a", "unavailable.bin"))
        with mock.patch.object(Path, "resolve", side_effect=AssertionError("I/O")), \
                mock.patch.object(os, "open", side_effect=AssertionError("I/O")):
            self.assertEqual(validate_inventory_request(request), request)

    def test_invalid_late_asset_and_caps_precede_root_access(self):
        late = request_for(("first", "first.bin"), ("private-marker", "../bad"))
        cases = [(late, {}, "asset 2")]
        for name in ("max_file_bytes", "max_total_bytes"):
            for cap in (0, -1, True, False, 1.0, "1", None, 2**63):
                cases.append((request_for(("first", "first.bin")), {name: cap}, name))
        for request, caps, expected in cases:
            with self.subTest(caps=caps, expected=expected):
                # The missing root distinguishes validation from file-access errors.
                with self.assertRaises(InventoryError) as caught:
                    build_inventory(request, media_root=Path("/not-a-real-inventory-root"), **caps)
                self.assertIn(expected, str(caught.exception))
                with mock.patch.object(inventory, "_open_root", side_effect=AssertionError("root opened")):
                    with self.assertRaisesRegex(InventoryError, expected):
                        build_inventory(request, media_root=Path("/not-a-real-inventory-root"), **caps)


class InventoryFileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write(self, path, content):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return destination

    def build(self, *pairs, **caps):
        return build_inventory(request_for(*pairs), media_root=self.root, **caps)

    @contextmanager
    def tracked_descriptors(self):
        real_open, real_dup = os.open, os.dup
        descriptors, openings = [], []

        def tracked_open(path, flags, **kwargs):
            descriptor = real_open(path, flags, **kwargs)
            descriptors.append(descriptor)
            openings.append((path, flags, kwargs))
            return descriptor

        def tracked_dup(descriptor):
            duplicate = real_dup(descriptor)
            descriptors.append(duplicate)
            return duplicate

        with mock.patch.object(os, "open", side_effect=tracked_open) as patched_open, \
                mock.patch.object(os, "dup", side_effect=tracked_dup), \
                mock.patch.object(os, "supports_dir_fd", os.supports_dir_fd | {patched_open}):
            try:
                yield openings
            finally:
                for descriptor in set(descriptors):
                    with self.assertRaises(OSError):
                        os.fstat(descriptor)

    def assert_failure(self, path, reason=None):
        with self.assertRaises(InventoryError) as caught:
            self.build(("private-marker-id", path))
        message = str(caught.exception)
        self.assertIn("asset 1", message)
        self.assertNotIn("private-marker", message)
        self.assertNotIn(str(self.root), message)
        if reason:
            self.assertIn(reason, message)

    def test_exact_report_contract_default_caps_and_no_source_metadata(self):
        self.write("source.bin", b"abc")
        report = self.build(("source-a", "source.bin"))
        self.assertEqual(report, {
            "schema_version": 1,
            "scope": "local_byte_inventory",
            "hash_algorithm": "sha256-bytes-v1",
            "limits": {
                "max_assets": 1000, "max_file_bytes": 1073741824,
                "max_total_bytes": 4294967296, "read_chunk_bytes": 1048576,
            },
            "assets": [{
                "asset_id": "source-a", "path": "source.bin", "size_bytes": 3,
                "sha256": hashlib.sha256(b"abc").hexdigest(),
            }],
            "duplicate_candidates": [],
            "summary": {"asset_count": 1, "total_bytes": 3, "duplicate_group_count": 0},
            "verification": {
                "file_bytes_hashed": True, "media_decoded": False,
                "timestamps_verified": False, "label_evidence_verified": False,
                "permission_verified": False, "training_started": False,
                "game_clear_verified": False,
            },
        })
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_nested_empty_binary_and_multiple_chunks_preserve_source_bytes(self):
        contents = {"nested/empty": b"", "binary": bytes(range(256)),
                    "large": b"x" * (1048576 * 2 + 19),
                    "字面/$not-expanded%20.txt": b"literal"}
        for name, content in contents.items():
            self.write(name, content)
        report = self.build(*[(str(i), path) for i, path in enumerate(contents)])
        for asset in report["assets"]:
            expected = contents[asset["path"]]
            self.assertEqual(asset["sha256"], hashlib.sha256(expected).hexdigest())
            self.assertEqual(asset["size_bytes"], len(expected))
            self.assertEqual((self.root / asset["path"]).read_bytes(), expected)
        self.assertEqual(report["summary"]["total_bytes"], sum(map(len, contents.values())))

    def test_duplicate_groups_sort_and_request_order_has_no_effect(self):
        contents = {"first": b"abc", "second": b"abc", "third": b"xyz",
                    "fourth": b"xyz", "fifth": b"def"}
        pairs = [(identifier, path) for identifier, path in zip(
            ("z", "A", "é", "a", "!"), contents)]
        for path, content in contents.items():
            self.write(path, content)
        report = self.build(*pairs)
        self.assertEqual(report, self.build(*reversed(pairs)))
        self.assertEqual([row["asset_id"] for row in report["assets"]], sorted(p[0] for p in pairs))
        expected = [
            {"size_bytes": 3, "sha256": hashlib.sha256(b"abc").hexdigest(), "asset_ids": ["A", "z"]},
            {"size_bytes": 3, "sha256": hashlib.sha256(b"xyz").hexdigest(), "asset_ids": ["a", "é"]},
        ]
        self.assertEqual(report["duplicate_candidates"], sorted(expected, key=lambda row: (row["sha256"], row["size_bytes"])))
        self.assertEqual(report["summary"], {"asset_count": 5, "total_bytes": 15, "duplicate_group_count": 2})

    def test_hard_links_count_as_separate_requested_assets(self):
        original = self.write("original", b"abc")
        os.link(original, self.root / "hard-link")
        report = self.build(("first", "original"), ("second", "hard-link"))
        self.assertEqual(report["summary"]["total_bytes"], 6)
        self.assertEqual(report["duplicate_candidates"][0]["asset_ids"], ["first", "second"])

    def test_descendant_symlinks_are_rejected_at_every_level(self):
        original = self.write("real/source", b"private-marker-bytes")
        (self.root / "private-marker-leaf").symlink_to(original)
        (self.root / "private-marker-parent").symlink_to(original.parent, target_is_directory=True)
        (self.root / "private-marker-dangling").symlink_to(self.root / "missing")
        for path in ("private-marker-leaf", "private-marker-parent/source", "private-marker-dangling"):
            with self.subTest(path=path):
                self.assert_failure(path)

    def test_missing_directory_and_intermediate_file_fail_privately(self):
        self.write("private-marker-file", b"abc")
        (self.root / "private-marker-directory").mkdir()
        for path in ("private-marker-missing", "private-marker-directory", "private-marker-file/child"):
            with self.subTest(path=path):
                self.assert_failure(path)

    def test_explicit_owner_selected_root_symlink_is_allowed(self):
        self.write("real/source", b"abc")
        root_link = self.root / "chosen-root"
        root_link.symlink_to(self.root / "real", target_is_directory=True)
        report = build_inventory(request_for(("a", "source")), media_root=root_link)
        self.assertEqual(report["assets"][0]["sha256"], hashlib.sha256(b"abc").hexdigest())

    def test_root_errors_do_not_include_configuration_or_os_values(self):
        self.write("private-marker-file", b"abc")
        for root in (self.root / "private-marker-missing", self.root / "private-marker-file"):
            with self.subTest(root=root.name), self.assertRaises(InventoryError) as caught:
                build_inventory(request_for(("a", "source")), media_root=root)
            self.assertEqual(str(caught.exception), "cannot open the configured media root")

    def test_file_and_total_caps_are_inclusive_with_no_required_order(self):
        self.write("a", b"abc")
        self.write("b", b"def")
        self.write("empty", b"")
        for caps in ({"max_file_bytes": 3, "max_total_bytes": 6},
                     {"max_file_bytes": 2**63 - 1, "max_total_bytes": 6},
                     {"max_file_bytes": 3, "max_total_bytes": 2**63 - 1}):
            report = self.build(("a", "a"), ("b", "b"), ("c", "empty"), **caps)
            self.assertEqual(report["summary"]["total_bytes"], 6)
            self.assertEqual(report["limits"]["max_file_bytes"], caps["max_file_bytes"])
            self.assertEqual(report["limits"]["max_total_bytes"], caps["max_total_bytes"])
        for pairs, caps in (
            ((("a", "a"),), {"max_file_bytes": 2}),
            ((("a", "a"),), {"max_file_bytes": 9, "max_total_bytes": 2}),
            ((("a", "a"), ("b", "b")), {"max_total_bytes": 5}),
        ):
            with self.subTest(caps=caps), self.assertRaisesRegex(InventoryError, "byte limit"):
                self.build(*pairs, **caps)

    def test_one_byte_caps_and_zero_remaining_total_allow_empty_files(self):
        self.write("one", b"x")
        self.write("empty", b"")
        report = self.build(("a", "one"), ("b", "empty"), max_file_bytes=1, max_total_bytes=1)
        self.assertEqual(report["summary"]["total_bytes"], 1)
        self.assertEqual(report["assets"][1]["sha256"], hashlib.sha256(b"").hexdigest())

    def test_file_error_uses_original_request_index_before_report_sorting(self):
        self.write("source", b"abc")
        with self.assertRaisesRegex(InventoryError, "asset 2: cannot open selected file"):
            self.build(("z", "source"), ("A", "private-marker-missing"))

    def test_initial_oversize_fails_without_reading(self):
        self.write("source", b"abcd")
        with mock.patch.object(os, "read", side_effect=AssertionError("must not read")):
            with self.assertRaisesRegex(InventoryError, "byte limit"):
                self.build(("a", "source"), max_file_bytes=3)

    def test_no_inventory_capability_fails_closed(self):
        self.write("source", b"abc")
        for target, value in (("name", "nt"), ("supports_dir_fd", set())):
            with self.subTest(target=target), mock.patch.object(os, target, value):
                with self.assertRaisesRegex(InventoryError, "requires POSIX"):
                    self.build(("a", "source"))
        for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"):
            value = getattr(os, flag)
            try:
                delattr(os, flag)
                with self.subTest(flag=flag), self.assertRaisesRegex(InventoryError, "requires POSIX"):
                    self.build(("a", "source"))
            finally:
                setattr(os, flag, value)

    def test_read_requests_are_bounded_and_eof_gets_only_one_sentinel_byte(self):
        content = b"a" * (1048576 + 3)
        self.write("source", content)
        real_read = os.read
        sizes = []

        def checked_read(descriptor, size):
            sizes.append(size)
            return real_read(descriptor, size)

        with mock.patch.object(os, "read", side_effect=checked_read):
            report = self.build(("a", "source"), max_total_bytes=len(content))
        self.assertEqual(report["assets"][0]["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(sizes, [1048576, 4, 1])

    def test_detectable_growth_truncation_and_same_size_mutation_fail(self):
        real_read = os.read
        for changed in (b"abcdef", b"ab", b"xyz"):
            with self.subTest(changed=changed):
                source = self.write("source", b"abc")
                changed_once = False

                def mutating_read(descriptor, size):
                    nonlocal changed_once
                    block = real_read(descriptor, size)
                    if not changed_once:
                        changed_once = True
                        source.write_bytes(changed)
                    return block

                with mock.patch.object(os, "read", side_effect=mutating_read):
                    with self.assertRaisesRegex(InventoryError, "asset 1.*changed while hashing"):
                        self.build(("private-marker-id", "source"))

    def test_growth_rejects_after_at_most_one_total_limit_sentinel_byte(self):
        source = self.write("source", b"abc")
        real_read = os.read
        read_sizes = []
        observed = []

        def growing_read(descriptor, size):
            if not read_sizes:
                source.write_bytes(b"abcdefgh")
            read_sizes.append(size)
            block = real_read(descriptor, size)
            observed.append(len(block))
            return block

        with mock.patch.object(os, "read", side_effect=growing_read):
            with self.assertRaisesRegex(InventoryError, "byte limit"):
                self.build(("a", "source"), max_total_bytes=3)
        self.assertEqual(read_sizes, [4])
        self.assertEqual(sum(observed), 4)

    def test_os_read_and_stat_failures_are_sanitized(self):
        self.write("private-marker-source", b"a" * (1048576 + 1))
        real_read, real_stat = os.read, os.fstat
        for operation, fail_at in (("read", 1), ("read", 2), ("fstat", 1), ("fstat", 2)):
            calls = 0

            def failing(*args):
                nonlocal calls
                calls += 1
                if calls == fail_at:
                    raise OSError("private-marker raw OS failure")
                return (real_read if operation == "read" else real_stat)(*args)

            with self.subTest(operation=operation, fail_at=fail_at), \
                    mock.patch.object(os, operation, side_effect=failing):
                self.assert_failure("private-marker-source")

    def test_every_identity_field_is_checked_but_atime_is_ignored(self):
        self.write("source", b"abc")
        real_stat = os.fstat
        fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns", "st_atime_ns")
        for changed_field in fields:
            calls = 0

            def changed_stat(descriptor):
                nonlocal calls
                calls += 1
                actual = real_stat(descriptor)
                values = {field: getattr(actual, field) for field in fields}
                if calls == 2:
                    values[changed_field] += 1
                return SimpleNamespace(**values)

            with self.subTest(field=changed_field), mock.patch.object(os, "fstat", side_effect=changed_stat):
                if changed_field == "st_atime_ns":
                    self.assertEqual(self.build(("a", "source"))["summary"]["total_bytes"], 3)
                else:
                    with self.assertRaisesRegex(InventoryError, "changed while hashing"):
                        self.build(("a", "source"))

    def test_descriptor_flags_and_cleanup_on_success_and_file_failures(self):
        self.write("nested/source", b"abc")
        (self.root / "nested/link").symlink_to(self.root / "nested/source")
        with self.tracked_descriptors() as openings:
            report = self.build(("a", "nested/source"))
        self.assertEqual(report["summary"]["total_bytes"], 3)
        self.assertEqual(openings[0][1:], (os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, {}))
        self.assertEqual(openings[1][0:2], ("nested", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
        self.assertEqual(openings[2][0:2], ("source", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK))
        self.assertTrue(all(type(opening[2]["dir_fd"]) is int for opening in openings[1:]))
        for path in ("nested", "nested/missing", "nested/link", "missing/source"):
            with self.subTest(path=path), self.tracked_descriptors():
                self.assert_failure(path)
        for operation in ("read", "fstat"):
            with self.subTest(operation=operation), self.tracked_descriptors():
                with mock.patch.object(os, operation, side_effect=OSError("private-marker")):
                    self.assert_failure("nested/source")
        with self.tracked_descriptors():
            with self.assertRaisesRegex(InventoryError, "byte limit"):
                self.build(("a", "nested/source"), max_file_bytes=2)

    def test_close_failures_are_private_and_do_not_leave_other_descriptors_open(self):
        self.write("source", b"abc")
        real_close = os.close
        for fail_at in (1, 2, 3):
            closes = 0

            def failed_close(descriptor):
                nonlocal closes
                real_close(descriptor)
                closes += 1
                if closes == fail_at:
                    raise OSError("private-marker close failure")

            with self.subTest(fail_at=fail_at), self.tracked_descriptors():
                with mock.patch.object(os, "close", side_effect=failed_close):
                    with self.assertRaises(InventoryError) as caught:
                        self.build(("private-marker-id", "source"))
                self.assertNotIn("private-marker", str(caught.exception))

    def test_dup_failure_closes_the_root_and_is_private(self):
        self.write("source", b"abc")
        with self.tracked_descriptors():
            with mock.patch.object(os, "dup", side_effect=OSError("private-marker")):
                self.assert_failure("source", "cannot open")

    def test_observed_size_must_equal_initial_size_even_with_unchanged_stat(self):
        self.write("source", b"abc")
        real_read = os.read

        def truncated_read(descriptor, size):
            return real_read(descriptor, size)[:-1]

        with self.tracked_descriptors(), mock.patch.object(os, "read", side_effect=truncated_read):
            with self.assertRaisesRegex(InventoryError, "changed while hashing"):
                self.build(("a", "source"))

    def test_initial_negative_size_is_rejected_without_reading(self):
        self.write("source", b"abc")
        actual = (self.root / "source").stat()
        with mock.patch.object(os, "fstat", return_value=SimpleNamespace(st_mode=actual.st_mode, st_size=-1)), \
                mock.patch.object(os, "read", side_effect=AssertionError("read")):
            with self.assertRaisesRegex(InventoryError, "byte limit"):
                self.build(("a", "source"))

    def test_original_request_and_report_are_fully_detached(self):
        self.write("source", b"abc")
        request = request_for(("a", "source"))
        before = copy.deepcopy(request)
        report = build_inventory(request, media_root=self.root)
        self.assertEqual(request, before)
        report["assets"][0]["path"] = "changed"
        self.assertEqual(request, before)

    def test_root_descriptor_remains_pinned_if_configured_name_is_replaced(self):
        self.write("chosen/first", b"abc")
        self.write("chosen/second", b"def")
        real_read = os.read
        replaced = False

        def replacing_read(descriptor, size):
            nonlocal replaced
            if not replaced:
                replaced = True
                (self.root / "chosen").rename(self.root / "moved")
                self.write("chosen/second", b"wrong replacement")
            return real_read(descriptor, size)

        with mock.patch.object(os, "read", side_effect=replacing_read):
            report = build_inventory(request_for(("a", "first"), ("b", "second")), media_root=self.root / "chosen")
        self.assertEqual(report["assets"][1]["sha256"], hashlib.sha256(b"def").hexdigest())


if __name__ == "__main__":
    unittest.main()
