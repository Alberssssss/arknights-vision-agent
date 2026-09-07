import sys
import unittest

from arknights_vision_agent.strict_json import StrictJSONError, load_json_object


class StrictJSONTests(unittest.TestCase):
    def test_error_is_a_value_error(self):
        self.assertTrue(issubclass(StrictJSONError, ValueError))

    def test_accepts_object_larger_than_action_limit_with_larger_limit(self):
        payload = '{"value":"' + ("x" * 17000) + '"}'

        self.assertEqual({"value": "x" * 17000}, load_json_object(payload, max_bytes=20000))

    def test_enforces_exact_utf8_byte_limit(self):
        payload = '{"value":"☃"}'
        size = len(payload.encode("utf-8"))

        self.assertEqual({"value": "☃"}, load_json_object(payload, max_bytes=size))
        with self.assertRaisesRegex(StrictJSONError, "size limit"):
            load_json_object(payload, max_bytes=size - 1)

    def test_rejects_invalid_max_bytes(self):
        for value in (True, False, 0, -1, 1.0, "10", None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(StrictJSONError, "max_bytes"):
                    load_json_object("{}", max_bytes=value)  # type: ignore[arg-type]

    def test_rejects_non_plain_text(self):
        class TextSubclass(str):
            pass

        for payload in (b"{}", {}, None, TextSubclass("{}")):
            with self.subTest(type=type(payload)):
                with self.assertRaisesRegex(StrictJSONError, "payload.*text"):
                    load_json_object(payload, max_bytes=100)  # type: ignore[arg-type]

    def test_rejects_duplicate_keys_at_any_depth(self):
        for payload in ('{"a":1,"a":2}', '{"outer":{"a":1,"a":2}}'):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(StrictJSONError, "duplicate"):
                    load_json_object(payload, max_bytes=100)

    def test_rejects_nonfinite_literals_and_float_overflow(self):
        for payload in (
            '{"value":NaN}',
            '{"value":Infinity}',
            '{"value":-Infinity}',
            '{"value":1e999}',
            '{"nested":[-1e999]}',
        ):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(StrictJSONError, "non-finite|finite range"):
                    load_json_object(payload, max_bytes=100)

    def test_accepts_large_finite_float(self):
        self.assertEqual({"value": 1e300}, load_json_object('{"value":1e300}', max_bytes=100))

    def test_requires_top_level_object(self):
        for payload in ("[]", '"text"', "1", "true", "null"):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(StrictJSONError, "JSON object"):
                    load_json_object(payload, max_bytes=100)

    def test_rejects_literal_and_decoded_invalid_unicode(self):
        for payload in ('{"value":"\ud800"}', '{"value":"\\ud800"}', '{"\\ud800":"value"}'):
            with self.subTest(payload=repr(payload)):
                with self.assertRaisesRegex(StrictJSONError, "Unicode"):
                    load_json_object(payload, max_bytes=100)

    def test_rejects_nesting_beyond_one_hundred_levels(self):
        payload = '{"value":' + ("[" * 100) + "0" + ("]" * 100) + "}"

        with self.assertRaisesRegex(StrictJSONError, "nested too deeply"):
            load_json_object(payload, max_bytes=1000)

    def test_normalizes_malformed_json_without_echoing_input(self):
        payload = '{"PRIVATE-MARKER":"unterminated"'

        with self.assertRaises(StrictJSONError) as caught:
            load_json_object(payload, max_bytes=100)

        self.assertNotIn("PRIVATE-MARKER", str(caught.exception))

    def test_normalizes_integer_conversion_limit_errors(self):
        get_limit = getattr(sys, "get_int_max_str_digits", None)
        set_limit = getattr(sys, "set_int_max_str_digits", None)
        if get_limit is None or set_limit is None:
            self.skipTest("interpreter has no integer string conversion limit")

        payload = '{"value":' + ("1" * 5000) + "}"
        original_limit = get_limit()
        changed_limit = original_limit == 0 or original_limit >= 5000
        if changed_limit:
            set_limit(4300)
        try:
            with self.assertRaisesRegex(StrictJSONError, "valid JSON") as caught:
                load_json_object(payload, max_bytes=6000)
        finally:
            if changed_limit:
                set_limit(original_limit)

        self.assertNotIn(payload, str(caught.exception))


class ActionWrapperTests(unittest.TestCase):
    def test_action_wrapper_keeps_smaller_limit(self):
        from arknights_vision_agent.actions import ActionValidationError, parse_action

        payload = '{"value":"' + ("x" * 17000) + '"}'
        self.assertEqual({"value": "x" * 17000}, load_json_object(payload, max_bytes=20000))

        with self.assertRaisesRegex(ActionValidationError, "size limit"):
            parse_action(payload)
