import copy
import unittest

from arknights_vision_agent.replay import ReplayValidationError, replay_trace

_DEFAULT_ACTION_JSON = object()


def make_observation(
    observation_id="frame-1",
    *,
    run_id="demo",
    source="synthetic",
    screen="recruitment",
    available_options=None,
    captured_at_ms=1000,
):
    if available_options is None:
        available_options = ["option-a"]
    return {
        "run_id": run_id,
        "observation_id": observation_id,
        "screen": screen,
        "available_options": available_options,
        "captured_at_ms": captured_at_ms,
        "source": source,
    }


def select_action(observation_id="frame-1", *, run_id="demo", option_id="option-a"):
    return (
        f'{{"run_id":"{run_id}","observation_id":"{observation_id}",'
        f'"kind":"select","option_id":"{option_id}"}}'
    )


def stop_action(observation_id="frame-1", *, run_id="demo"):
    return (
        f'{{"run_id":"{run_id}","observation_id":"{observation_id}",'
        '"kind":"stop"}'
    )


def make_step(
    observation=None,
    *,
    action_json=_DEFAULT_ACTION_JSON,
    decision_at_ms=1100,
):
    if observation is None:
        observation = make_observation()
    if action_json is _DEFAULT_ACTION_JSON:
        action_json = select_action(observation["observation_id"])
    return {
        "observation": observation,
        "action_json": action_json,
        "decision_at_ms": decision_at_ms,
    }


def make_trace(steps=None, *, run_id="demo", source="synthetic"):
    if steps is None:
        steps = [make_step()]
    return {
        "schema_version": 1,
        "run_id": run_id,
        "source": source,
        "steps": steps,
    }


class ReplayTests(unittest.TestCase):
    def test_valid_select_is_allowed_only_as_dry_run(self):
        result = replay_trace(make_trace())

        self.assertEqual(
            result,
            {
                "schema_version": 1,
                "mode": "dry_run",
                "source": "synthetic",
                "run_id": "demo",
                "events": [
                    {
                        "step_index": 1,
                        "observation_id": "frame-1",
                        "proposed_action": {
                            "run_id": "demo",
                            "observation_id": "frame-1",
                            "kind": "select",
                            "option_id": "option-a",
                        },
                        "status": "allowed_dry_run",
                        "executed": False,
                    }
                ],
                "summary": {
                    "steps_available": 1,
                    "steps_processed": 1,
                    "allowed_actions": 1,
                    "blocked_actions": 0,
                    "stopped": False,
                    "trace_exhausted": True,
                    "game_clear_verified": False,
                    "mode": "dry_run",
                },
            },
        )
        self.assertNotIn("success", result)
        self.assertNotIn("success", result["summary"])

    def test_valid_wait_is_allowed_without_execution(self):
        observation = make_observation(
            screen="unknown", available_options=[], captured_at_ms=2000
        )
        step = make_step(
            observation,
            action_json=(
                '{"run_id":"demo","observation_id":"frame-1",'
                '"kind":"wait","wait_ms":25}'
            ),
            decision_at_ms=2000,
        )

        result = replay_trace(make_trace([step]))

        self.assertEqual(result["events"][0]["status"], "allowed_dry_run")
        self.assertIs(result["events"][0]["executed"], False)

    def test_rejects_non_plain_trace_dictionary(self):
        class DictionarySubclass(dict):
            pass

        with self.assertRaisesRegex(ReplayValidationError, "trace.*dictionary"):
            replay_trace(DictionarySubclass(make_trace()))

    def test_rejects_missing_or_additional_trace_fields(self):
        missing = make_trace()
        del missing["source"]
        additional = make_trace()
        additional["unexpected"] = None

        for trace in (missing, additional):
            with self.subTest(trace=trace):
                with self.assertRaisesRegex(ReplayValidationError, "trace fields"):
                    replay_trace(trace)

    def test_rejects_invalid_schema_versions(self):
        for version in (True, 1.0, "1", 2):
            with self.subTest(version=version):
                trace = make_trace()
                trace["schema_version"] = version
                with self.assertRaisesRegex(ReplayValidationError, "schema_version"):
                    replay_trace(trace)

    def test_rejects_invalid_trace_run_identifier_using_shared_boundary(self):
        for run_id in (" ", "x" * 129, 7):
            with self.subTest(run_id=run_id):
                observation = make_observation(run_id=run_id)
                trace = make_trace([make_step(observation)], run_id=run_id)
                with self.assertRaisesRegex(ReplayValidationError, "run_id"):
                    replay_trace(trace)

    def test_rejects_non_plain_or_unsupported_sources(self):
        class StringSubclass(str):
            pass

        for source in ("live", "unknown", 7, StringSubclass("synthetic")):
            with self.subTest(source=source):
                observation = make_observation(source=source)
                trace = make_trace([make_step(observation)], source=source)
                with self.assertRaisesRegex(ReplayValidationError, "source"):
                    replay_trace(trace)

    def test_rejects_non_plain_steps_list(self):
        class ListSubclass(list):
            pass

        for steps in ((make_step(),), ListSubclass([make_step()])):
            with self.subTest(type=type(steps)):
                with self.assertRaisesRegex(ReplayValidationError, "steps.*list"):
                    replay_trace(make_trace(steps))

    def test_rejects_empty_steps(self):
        with self.assertRaisesRegex(ReplayValidationError, "steps.*empty"):
            replay_trace(make_trace([]))

    def test_rejects_more_than_one_thousand_steps(self):
        steps = []
        for index in range(1001):
            observation_id = f"frame-{index}"
            observation = make_observation(
                observation_id,
                captured_at_ms=index,
            )
            steps.append(
                make_step(
                    observation,
                    action_json=stop_action(observation_id),
                    decision_at_ms=index,
                )
            )

        with self.assertRaisesRegex(ReplayValidationError, "1000"):
            replay_trace(make_trace(steps))

    def test_rejects_non_plain_step_dictionary(self):
        class DictionarySubclass(dict):
            pass

        step = DictionarySubclass(make_step())
        with self.assertRaisesRegex(ReplayValidationError, "step 1.*dictionary"):
            replay_trace(make_trace([step]))

    def test_rejects_missing_or_additional_step_fields(self):
        missing = make_step()
        del missing["action_json"]
        additional = make_step()
        additional["unexpected"] = None

        for step in (missing, additional):
            with self.subTest(step=step):
                with self.assertRaisesRegex(ReplayValidationError, "step 1 fields"):
                    replay_trace(make_trace([step]))

    def test_rejects_non_plain_action_json_text(self):
        class StringSubclass(str):
            pass

        for action_json in (b"{}", StringSubclass("{}"), None):
            with self.subTest(type=type(action_json)):
                step = make_step(action_json=action_json)
                with self.assertRaisesRegex(ReplayValidationError, "action_json"):
                    replay_trace(make_trace([step]))

    def test_rejects_invalid_decision_timestamps(self):
        for decision_at_ms in (True, -1, 1.0, "1100"):
            with self.subTest(decision_at_ms=decision_at_ms):
                step = make_step(decision_at_ms=decision_at_ms)
                with self.assertRaisesRegex(ReplayValidationError, "decision_at_ms"):
                    replay_trace(make_trace([step]))

    def test_wraps_shared_observation_schema_errors(self):
        observation = make_observation(screen="unsupported")

        with self.assertRaisesRegex(ReplayValidationError, "observation.*screen"):
            replay_trace(make_trace([make_step(observation)]))

    def test_rejects_non_plain_observation_dictionary(self):
        class DictionarySubclass(dict):
            pass

        observation = DictionarySubclass(make_observation())
        with self.assertRaisesRegex(ReplayValidationError, "observation.*dictionary"):
            replay_trace(make_trace([make_step(observation)]))

    def test_rejects_mismatched_run_provenance(self):
        observation = make_observation(run_id="other-run")

        with self.assertRaisesRegex(ReplayValidationError, "run_id.*trace"):
            replay_trace(make_trace([make_step(observation)]))

    def test_rejects_mismatched_source_provenance(self):
        observation = make_observation(source="recorded")

        with self.assertRaisesRegex(ReplayValidationError, "source.*trace"):
            replay_trace(make_trace([make_step(observation)]))

    def test_rejects_duplicate_observation_identifiers(self):
        first = make_step()
        second_observation = make_observation(captured_at_ms=1200)
        second = make_step(
            second_observation,
            action_json=stop_action(),
            decision_at_ms=1200,
        )

        with self.assertRaisesRegex(ReplayValidationError, "observation_id.*duplicate"):
            replay_trace(make_trace([first, second]))

    def test_rejects_backward_capture_clock(self):
        first_observation = make_observation("frame-1", captured_at_ms=1001)
        second_observation = make_observation("frame-2", captured_at_ms=1000)
        steps = [
            make_step(first_observation, decision_at_ms=1100),
            make_step(
                second_observation,
                action_json=stop_action("frame-2"),
                decision_at_ms=1200,
            ),
        ]

        with self.assertRaisesRegex(ReplayValidationError, "captured_at_ms.*backward"):
            replay_trace(make_trace(steps))

    def test_rejects_backward_decision_clock(self):
        first_observation = make_observation("frame-1", captured_at_ms=1000)
        second_observation = make_observation("frame-2", captured_at_ms=1100)
        steps = [
            make_step(first_observation, decision_at_ms=1200),
            make_step(
                second_observation,
                action_json=stop_action("frame-2"),
                decision_at_ms=1199,
            ),
        ]

        with self.assertRaisesRegex(ReplayValidationError, "decision_at_ms.*backward"):
            replay_trace(make_trace(steps))

    def test_validates_later_observation_before_an_earlier_stop(self):
        stop_step = make_step(action_json=stop_action())
        malformed_observation = make_observation("frame-2")
        del malformed_observation["screen"]
        later_step = make_step(
            malformed_observation,
            action_json="not processed",
            decision_at_ms=1200,
        )

        with self.assertRaisesRegex(ReplayValidationError, "observation"):
            replay_trace(make_trace([stop_step, later_step]))

    def test_stale_action_is_blocked_and_halts_before_later_actions(self):
        stale_step = make_step(decision_at_ms=6001)
        later_observation = make_observation("frame-2", captured_at_ms=6001)
        later_step = make_step(
            later_observation,
            action_json="malformed action is never processed",
            decision_at_ms=6001,
        )

        result = replay_trace(make_trace([stale_step, later_step]))

        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events"][0]["status"], "blocked")
        self.assertIn("stale", result["events"][0]["error"])
        self.assertIs(result["events"][0]["executed"], False)
        self.assertEqual(result["summary"]["steps_processed"], 1)
        self.assertEqual(result["summary"]["allowed_actions"], 0)
        self.assertEqual(result["summary"]["blocked_actions"], 1)
        self.assertIs(result["summary"]["trace_exhausted"], False)
        self.assertIs(result["summary"]["game_clear_verified"], False)

    def test_future_action_is_blocked(self):
        observation = make_observation(captured_at_ms=1101)

        result = replay_trace(
            make_trace([make_step(observation, decision_at_ms=1100)])
        )

        self.assertEqual(result["events"][0]["status"], "blocked")
        self.assertIn("future", result["events"][0]["error"])

    def test_invalid_parsed_action_is_logged_and_blocked(self):
        invalid_action = {
            "run_id": "demo",
            "observation_id": "frame-1",
            "kind": "select",
            "option_id": "unavailable",
        }
        action_json = (
            '{"run_id":"demo","observation_id":"frame-1",'
            '"kind":"select","option_id":"unavailable"}'
        )

        result = replay_trace(make_trace([make_step(action_json=action_json)]))

        self.assertEqual(
            result["events"],
            [
                {
                    "step_index": 1,
                    "observation_id": "frame-1",
                    "proposed_action": invalid_action,
                    "status": "blocked",
                    "executed": False,
                    "error": "selected option is not available",
                }
            ],
        )
        self.assertIs(result["summary"]["trace_exhausted"], True)

    def test_malformed_action_is_blocked_without_echoing_raw_payload(self):
        marker = "PRIVATE-RAW-MARKER"
        step = make_step(action_json=f"not-json-{marker}")

        result = replay_trace(make_trace([step]))

        event = result["events"][0]
        self.assertEqual(
            set(event),
            {"step_index", "observation_id", "parse_error", "status", "executed"},
        )
        self.assertEqual(event["status"], "blocked")
        self.assertIs(event["executed"], False)
        self.assertNotIn(marker, event["parse_error"])
        self.assertEqual(result["summary"]["blocked_actions"], 1)

    def test_oversized_action_is_blocked_without_echoing_raw_payload(self):
        marker = "PRIVATE-RAW-MARKER"
        step = make_step(action_json=marker + "x" * 16384)

        result = replay_trace(make_trace([step]))

        event = result["events"][0]
        self.assertEqual(event["status"], "blocked")
        self.assertIn("size limit", event["parse_error"])
        self.assertNotIn(marker, event["parse_error"])

    def test_stop_short_circuits_and_is_not_counted_as_allowed(self):
        first = make_step(action_json=stop_action())
        second_observation = make_observation("frame-2", captured_at_ms=1200)
        second = make_step(
            second_observation,
            action_json=select_action("frame-2"),
            decision_at_ms=1200,
        )

        result = replay_trace(make_trace([first, second]))

        self.assertEqual(result["events"][0]["status"], "stopped")
        self.assertIs(result["events"][0]["executed"], False)
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["summary"]["steps_processed"], 1)
        self.assertEqual(result["summary"]["allowed_actions"], 0)
        self.assertEqual(result["summary"]["blocked_actions"], 0)
        self.assertIs(result["summary"]["stopped"], True)
        self.assertIs(result["summary"]["trace_exhausted"], False)

    def test_final_stop_counts_as_trace_exhaustion(self):
        result = replay_trace(make_trace([make_step(action_json=stop_action())]))

        self.assertIs(result["summary"]["stopped"], True)
        self.assertIs(result["summary"]["trace_exhausted"], True)

    def test_stop_is_allowed_for_stale_observation(self):
        step = make_step(action_json=stop_action(), decision_at_ms=10000)

        result = replay_trace(make_trace([step]))

        self.assertEqual(result["events"][0]["status"], "stopped")

    def test_stop_is_allowed_for_future_observation(self):
        observation = make_observation(captured_at_ms=1200)
        step = make_step(
            observation,
            action_json=stop_action(),
            decision_at_ms=1100,
        )

        result = replay_trace(make_trace([step]))

        self.assertEqual(result["events"][0]["status"], "stopped")

    def test_does_not_mutate_trace_or_return_input_nested_objects(self):
        trace = make_trace()
        original = copy.deepcopy(trace)

        result = replay_trace(trace)
        result["events"][0]["proposed_action"]["run_id"] = "changed"

        self.assertEqual(trace, original)
        self.assertEqual(trace["run_id"], "demo")
        self.assertEqual(trace["steps"][0]["observation"]["run_id"], "demo")


if __name__ == "__main__":
    unittest.main()
