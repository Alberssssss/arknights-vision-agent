import copy
from pathlib import Path
import sys
import tomllib
import unittest

import arknights_vision_agent
from arknights_vision_agent.actions import (
    ActionValidationError,
    parse_action,
    validate_action,
)


class ActionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.observation = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "screen": "recruitment",
            "available_options": ["option-a", "option-b"],
            "captured_at_ms": 1000,
            "source": "synthetic",
        }

    def test_parses_and_validates_select_without_reusing_input(self):
        action = parse_action(
            '{"run_id":"synthetic-run","observation_id":"frame-1",'
            '"kind":"select","option_id":"option-a"}'
        )

        result = validate_action(action, self.observation, now_ms=1100)

        self.assertEqual(action, result)
        self.assertIsNot(action, result)

    def test_validation_error_is_a_value_error(self):
        self.assertTrue(issubclass(ActionValidationError, ValueError))


class ParseActionTests(unittest.TestCase):
    def test_rejects_malformed_json_without_echoing_payload(self):
        payload = '{"private-marker":"do-not-echo"'

        with self.assertRaises(ActionValidationError) as caught:
            parse_action(payload)

        self.assertNotIn(payload, str(caught.exception))

    def test_rejects_duplicate_object_keys(self):
        with self.assertRaises(ActionValidationError):
            parse_action('{"kind":"stop","kind":"wait"}')

    def test_rejects_nonfinite_numbers(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                with self.assertRaises(ActionValidationError):
                    parse_action('{"wait_ms":' + constant + "}")

    def test_rejects_non_object_top_level_values(self):
        for payload in ('[]', '"stop"', "1", "true", "null"):
            with self.subTest(payload=payload):
                with self.assertRaises(ActionValidationError):
                    parse_action(payload)

    def test_rejects_non_string_payload(self):
        for payload in (b"{}", {}, None):
            with self.subTest(payload=payload):
                with self.assertRaises(ActionValidationError):
                    parse_action(payload)  # type: ignore[arg-type]

    def test_rejects_payload_over_utf8_byte_limit(self):
        payload = '{"value":"' + ("\N{SNOWMAN}" * 5460) + '"}'
        self.assertGreater(len(payload.encode("utf-8")), 16384)

        with self.assertRaises(ActionValidationError):
            parse_action(payload)

    def test_rejects_lone_unicode_surrogate(self):
        with self.assertRaises(ActionValidationError):
            parse_action('{"value":"\ud800"}')

    def test_rejects_escaped_lone_unicode_surrogate(self):
        for payload in ('{"value":"\\ud800"}', '{"\\ud800":"value"}'):
            with self.subTest(payload=payload):
                with self.assertRaises(ActionValidationError):
                    parse_action(payload)

    def test_accepts_payload_at_utf8_byte_limit(self):
        payload = '{"kind":"stop"}'
        payload += " " * (16384 - len(payload.encode("utf-8")))

        self.assertEqual({"kind": "stop"}, parse_action(payload))

    def test_deep_nesting_fails_with_validation_error(self):
        payload = '{"value":' + ("[" * 1200) + "0" + ("]" * 1200) + "}"

        with self.assertRaises(ActionValidationError):
            parse_action(payload)

    def test_integer_conversion_limit_error_is_normalized(self):
        get_limit = getattr(sys, "get_int_max_str_digits", None)
        set_limit = getattr(sys, "set_int_max_str_digits", None)
        if get_limit is None or set_limit is None:
            self.skipTest("interpreter has no integer string conversion limit")

        payload = '{"wait_ms":' + ("1" * 5000) + "}"
        original_limit = get_limit()
        changed_limit = original_limit == 0 or original_limit >= 5000
        if changed_limit:
            set_limit(4300)
        try:
            with self.assertRaises(ActionValidationError) as caught:
                parse_action(payload)
        finally:
            if changed_limit:
                set_limit(original_limit)

        self.assertNotIn(payload, str(caught.exception))
        self.assertLess(len(str(caught.exception)), 256)


class ObservationValidationTests(unittest.TestCase):
    def setUp(self):
        self.observation = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "screen": "terminal",
            "available_options": [],
            "captured_at_ms": 1000,
            "source": "synthetic",
        }
        self.action = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "kind": "stop",
        }

    def assert_invalid_observation(self, **changes):
        observation = copy.deepcopy(self.observation)
        observation.update(changes)
        with self.assertRaises(ActionValidationError):
            validate_action(self.action, observation, now_ms=1100)

    def test_rejects_each_missing_observation_key(self):
        for key in self.observation:
            with self.subTest(key=key):
                observation = copy.deepcopy(self.observation)
                del observation[key]
                with self.assertRaises(ActionValidationError):
                    validate_action(self.action, observation, now_ms=1100)

    def test_rejects_additional_observation_key(self):
        self.assert_invalid_observation(untrusted_extension=True)

    def test_rejects_invalid_observation_ids(self):
        for field in ("run_id", "observation_id"):
            for value in ("", " \t", "x" * 129, "\ud800", 7, None):
                with self.subTest(field=field, value=value):
                    self.assert_invalid_observation(**{field: value})

    def test_rejects_invalid_screen(self):
        for screen in ("battle", "RECRUITMENT", "", 1, None):
            with self.subTest(screen=screen):
                self.assert_invalid_observation(screen=screen)

    def test_rejects_invalid_source(self):
        for source in ("remote", "SYNTHETIC", "", 1, None):
            with self.subTest(source=source):
                self.assert_invalid_observation(source=source)

    def test_rejects_non_list_option_containers(self):
        for options in ((), {}, {"option-a"}, "option-a", None):
            with self.subTest(options=options):
                self.assert_invalid_observation(available_options=options)

    def test_rejects_duplicate_options(self):
        self.assert_invalid_observation(
            available_options=["option-a", "option-a"]
        )

    def test_rejects_invalid_option_ids(self):
        for option_id in ("", " \n", "x" * 129, "\ud800", 3, None):
            with self.subTest(option_id=option_id):
                self.assert_invalid_observation(available_options=[option_id])

    def test_rejects_invalid_capture_timestamp(self):
        for captured_at_ms in (-1, True, 1.5, "1000", None):
            with self.subTest(captured_at_ms=captured_at_ms):
                self.assert_invalid_observation(captured_at_ms=captured_at_ms)


class ActionSchemaTests(unittest.TestCase):
    def setUp(self):
        self.observation = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "screen": "recruitment",
            "available_options": ["option-a"],
            "captured_at_ms": 1000,
            "source": "synthetic",
        }

    def assert_invalid_action(self, action):
        with self.assertRaises(ActionValidationError):
            validate_action(action, self.observation, now_ms=1100)

    def test_rejects_invalid_kind(self):
        for kind in ("click", "SELECT", "", 1, None):
            with self.subTest(kind=kind):
                self.assert_invalid_action(
                    {
                        "run_id": "synthetic-run",
                        "observation_id": "frame-1",
                        "kind": kind,
                    }
                )

    def test_rejects_each_missing_common_action_field(self):
        action = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "kind": "stop",
        }
        for key in action:
            with self.subTest(key=key):
                missing = dict(action)
                del missing[key]
                self.assert_invalid_action(missing)

    def test_rejects_missing_kind_specific_field(self):
        for kind in ("select", "wait"):
            with self.subTest(kind=kind):
                self.assert_invalid_action(
                    {
                        "run_id": "synthetic-run",
                        "observation_id": "frame-1",
                        "kind": kind,
                    }
                )

    def test_rejects_additional_or_wrong_fields_for_each_kind(self):
        actions = (
            {
                "run_id": "synthetic-run",
                "observation_id": "frame-1",
                "kind": "select",
                "option_id": "option-a",
                "wait_ms": 1,
            },
            {
                "run_id": "synthetic-run",
                "observation_id": "frame-1",
                "kind": "wait",
                "wait_ms": 1,
                "option_id": "option-a",
            },
            {
                "run_id": "synthetic-run",
                "observation_id": "frame-1",
                "kind": "stop",
                "reason": "done",
            },
        )
        for action in actions:
            with self.subTest(kind=action["kind"]):
                self.assert_invalid_action(action)

    def test_rejects_invalid_action_ids(self):
        for field in ("run_id", "observation_id"):
            for value in ("", " \t", "x" * 129, "\ud800", 7, None):
                with self.subTest(field=field, value=value):
                    action = {
                        "run_id": "synthetic-run",
                        "observation_id": "frame-1",
                        "kind": "select",
                        "option_id": "option-a",
                    }
                    action[field] = value
                    self.assert_invalid_action(action)

    def test_rejects_invalid_selected_option_id(self):
        for option_id in ("", " \n", "x" * 129, "\ud800", 3, None):
            with self.subTest(option_id=option_id):
                self.assert_invalid_action(
                    {
                        "run_id": "synthetic-run",
                        "observation_id": "frame-1",
                        "kind": "select",
                        "option_id": option_id,
                    }
                )


class ActionBehaviorTests(unittest.TestCase):
    def make_observation(self, **changes):
        observation = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "screen": "recruitment",
            "available_options": ["option-a", "option-b"],
            "captured_at_ms": 1000,
            "source": "synthetic",
        }
        observation.update(changes)
        return observation

    def make_action(self, kind, **changes):
        action = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "kind": kind,
        }
        if kind == "select":
            action["option_id"] = "option-a"
        elif kind == "wait":
            action["wait_ms"] = 1
        action.update(changes)
        return action

    def test_allows_select_on_each_supported_menu(self):
        for screen in ("recruitment", "route", "event"):
            with self.subTest(screen=screen):
                action = self.make_action("select")
                self.assertEqual(
                    action,
                    validate_action(
                        action,
                        self.make_observation(screen=screen),
                        now_ms=1100,
                    ),
                )

    def test_allows_wait_on_unknown_screen(self):
        action = self.make_action("wait", wait_ms=500)

        self.assertEqual(
            action,
            validate_action(
                action,
                self.make_observation(screen="unknown"),
                now_ms=1100,
            ),
        )

    def test_allows_wait_boundaries(self):
        for wait_ms in (1, 10000):
            with self.subTest(wait_ms=wait_ms):
                action = self.make_action("wait", wait_ms=wait_ms)
                self.assertEqual(
                    action,
                    validate_action(action, self.make_observation(), now_ms=1100),
                )

    def test_rejects_invalid_wait_values(self):
        for wait_ms in (-1, 0, 10001, True, False, 1.5, "1", None):
            with self.subTest(wait_ms=wait_ms):
                with self.assertRaises(ActionValidationError):
                    validate_action(
                        self.make_action("wait", wait_ms=wait_ms),
                        self.make_observation(),
                        now_ms=1100,
                    )

    def test_rejects_unavailable_option(self):
        with self.assertRaises(ActionValidationError):
            validate_action(
                self.make_action("select", option_id="option-c"),
                self.make_observation(),
                now_ms=1100,
            )

    def test_rejects_select_on_unknown_and_terminal_screens(self):
        for screen in ("unknown", "terminal"):
            with self.subTest(screen=screen):
                with self.assertRaises(ActionValidationError):
                    validate_action(
                        self.make_action("select"),
                        self.make_observation(screen=screen),
                        now_ms=1100,
                    )

    def test_terminal_screen_rejects_wait(self):
        with self.assertRaises(ActionValidationError):
            validate_action(
                self.make_action("wait"),
                self.make_observation(screen="terminal"),
                now_ms=1100,
            )

    def test_stop_is_allowed_on_terminal_and_nonterminal_screens(self):
        action = self.make_action("stop")
        for screen in ("terminal", "recruitment"):
            with self.subTest(screen=screen):
                self.assertEqual(
                    action,
                    validate_action(
                        action,
                        self.make_observation(screen=screen),
                        now_ms=1100,
                    ),
                )

    def test_stop_allows_stale_and_future_observations(self):
        action = self.make_action("stop")
        for captured_at_ms, now_ms in ((1000, 10000), (2000, 1000)):
            with self.subTest(captured_at_ms=captured_at_ms, now_ms=now_ms):
                self.assertEqual(
                    action,
                    validate_action(
                        action,
                        self.make_observation(captured_at_ms=captured_at_ms),
                        now_ms=now_ms,
                    ),
                )

    def test_accepts_each_observation_source(self):
        action = self.make_action("stop")
        for source in ("synthetic", "recorded", "live"):
            with self.subTest(source=source):
                self.assertEqual(
                    action,
                    validate_action(
                        action,
                        self.make_observation(source=source),
                        now_ms=1100,
                    ),
                )

    def test_accepts_valid_non_ascii_ids(self):
        action = {
            "run_id": "运行-一",
            "observation_id": "画面-一",
            "kind": "select",
            "option_id": "选项-甲",
        }
        observation = self.make_observation(
            run_id="运行-一",
            observation_id="画面-一",
            available_options=["选项-甲", "选项-乙"],
        )

        self.assertEqual(
            action,
            validate_action(action, observation, now_ms=1100),
        )

    def test_rejects_matching_lone_surrogate_ids(self):
        cases = (
            ({"run_id": "\ud800"}, {"run_id": "\ud800"}),
            (
                {"observation_id": "\ud800"},
                {"observation_id": "\ud800"},
            ),
            (
                {"option_id": "\ud800"},
                {"available_options": ["\ud800"]},
            ),
        )
        for action_changes, observation_changes in cases:
            with self.subTest(action_changes=action_changes):
                with self.assertRaises(ActionValidationError):
                    validate_action(
                        self.make_action("select", **action_changes),
                        self.make_observation(**observation_changes),
                        now_ms=1100,
                    )

    def test_rejects_mismatched_run_or_observation_even_for_stop(self):
        for field, value in (
            ("run_id", "other-run"),
            ("observation_id", "other-frame"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ActionValidationError):
                    validate_action(
                        self.make_action("stop", **{field: value}),
                        self.make_observation(),
                        now_ms=1100,
                    )

    def test_select_and_wait_reject_future_observations(self):
        for kind in ("select", "wait"):
            with self.subTest(kind=kind):
                with self.assertRaises(ActionValidationError):
                    validate_action(
                        self.make_action(kind),
                        self.make_observation(captured_at_ms=1101),
                        now_ms=1100,
                    )

    def test_select_and_wait_allow_exact_age_limit(self):
        for kind in ("select", "wait"):
            with self.subTest(kind=kind):
                action = self.make_action(kind)
                self.assertEqual(
                    action,
                    validate_action(
                        action,
                        self.make_observation(captured_at_ms=1000),
                        now_ms=6000,
                    ),
                )

    def test_select_and_wait_reject_stale_observations(self):
        for kind in ("select", "wait"):
            with self.subTest(kind=kind):
                with self.assertRaises(ActionValidationError):
                    validate_action(
                        self.make_action(kind),
                        self.make_observation(captured_at_ms=1000),
                        now_ms=6001,
                    )

    def test_custom_age_limit_is_inclusive(self):
        action = self.make_action("wait")

        self.assertEqual(
            action,
            validate_action(
                action,
                self.make_observation(captured_at_ms=1000),
                now_ms=1250,
                max_age_ms=250,
            ),
        )
        with self.assertRaises(ActionValidationError):
            validate_action(
                action,
                self.make_observation(captured_at_ms=1000),
                now_ms=1251,
                max_age_ms=250,
            )


class StrictCallBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.action = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "kind": "select",
            "option_id": "option-a",
        }
        self.observation = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "screen": "recruitment",
            "available_options": ["option-a", "option-b"],
            "captured_at_ms": 1000,
            "source": "synthetic",
        }

    def test_rejects_non_dict_action_direct_calls(self):
        for action in ([], (), "stop", None, 1):
            with self.subTest(action=action):
                with self.assertRaises(ActionValidationError):
                    validate_action(action, self.observation, now_ms=1100)

    def test_rejects_non_dict_observation_direct_calls(self):
        for observation in ([], (), "frame-1", None, 1):
            with self.subTest(observation=observation):
                with self.assertRaises(ActionValidationError):
                    validate_action(self.action, observation, now_ms=1100)

    def test_rejects_invalid_now_even_for_stop(self):
        stop = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "kind": "stop",
        }
        for now_ms in (-1, True, 1.5, "1100", None):
            with self.subTest(now_ms=now_ms):
                with self.assertRaises(ActionValidationError):
                    validate_action(stop, self.observation, now_ms=now_ms)

    def test_rejects_invalid_max_age_even_for_stop(self):
        stop = {
            "run_id": "synthetic-run",
            "observation_id": "frame-1",
            "kind": "stop",
        }
        for max_age_ms in (-1, True, 1.5, "5000", None):
            with self.subTest(max_age_ms=max_age_ms):
                with self.assertRaises(ActionValidationError):
                    validate_action(
                        stop,
                        self.observation,
                        now_ms=1100,
                        max_age_ms=max_age_ms,
                    )

    def test_unhashable_enum_like_values_raise_validation_error(self):
        for field, value in (("screen", []), ("source", {})):
            with self.subTest(field=field):
                observation = copy.deepcopy(self.observation)
                observation[field] = value
                with self.assertRaises(ActionValidationError):
                    validate_action(self.action, observation, now_ms=1100)

        action = dict(self.action)
        action["kind"] = []
        with self.assertRaises(ActionValidationError):
            validate_action(action, self.observation, now_ms=1100)

    def test_does_not_mutate_inputs_on_success(self):
        action_before = copy.deepcopy(self.action)
        observation_before = copy.deepcopy(self.observation)

        result = validate_action(self.action, self.observation, now_ms=1100)

        self.assertEqual(action_before, self.action)
        self.assertEqual(observation_before, self.observation)
        self.assertEqual(action_before, result)
        self.assertIsNot(self.action, result)

    def test_does_not_mutate_inputs_on_rejection(self):
        action = dict(self.action, option_id="not-available")
        action_before = copy.deepcopy(action)
        observation_before = copy.deepcopy(self.observation)

        with self.assertRaises(ActionValidationError):
            validate_action(action, self.observation, now_ms=1100)

        self.assertEqual(action_before, action)
        self.assertEqual(observation_before, self.observation)


class PackagingTests(unittest.TestCase):
    def test_package_version(self):
        self.assertEqual("0.1.0", arknights_vision_agent.__version__)

    def test_pyproject_declares_setuptools_src_layout_without_dependencies(self):
        repository_root = Path(__file__).resolve().parents[1]
        with (repository_root / "pyproject.toml").open("rb") as project_file:
            project = tomllib.load(project_file)

        self.assertEqual(
            "setuptools.build_meta",
            project["build-system"]["build-backend"],
        )
        self.assertEqual("0.1.0", project["project"]["version"])
        self.assertEqual(">=3.11", project["project"]["requires-python"])
        self.assertEqual([], project["project"]["dependencies"])
        self.assertEqual(
            ["src"],
            project["tool"]["setuptools"]["packages"]["find"]["where"],
        )


if __name__ == "__main__":
    unittest.main()
