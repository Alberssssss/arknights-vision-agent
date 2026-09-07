"""Acceptance checks for the local build-experiment supervisor, not product tests."""

import os
import signal
import subprocess
import sys
import time
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import process_runner
from process_runner import run


class ProcessRunnerTests(unittest.TestCase):
    @contextmanager
    def track_real_children(self):
        children = []
        original_popen = subprocess.Popen
        original_signal_group = process_runner._signal_group

        def record_child(*args, **kwargs):
            child = original_popen(*args, **kwargs)
            children.append(child)
            return child

        try:
            with patch("process_runner.subprocess.Popen", side_effect=record_child):
                yield children
        finally:
            # A failing regression must not itself leave a real child behind.
            # Fault-injection contexts have exited before this fallback runs.
            for child in children:
                try:
                    original_signal_group(child.pid, signal.SIGKILL)
                finally:
                    try:
                        child.wait(timeout=2)
                    finally:
                        child.stdout.close()
                        child.stderr.close()

    def assert_reaped_and_closed(self, child):
        # Do not poll or wait here: that could reap a child on the runner's behalf.
        self.assertIsNotNone(child.returncode, "runner left the leader unreaped")
        with self.assertRaises(ChildProcessError):
            os.waitpid(child.pid, os.WNOHANG)
        self.assertTrue(child.stdout.closed, "runner left stdout open")
        self.assertTrue(child.stderr.closed, "runner left stderr open")

    def execute(self, program, timeout=3, output_limit=8192):
        return run([sys.executable, "-c", program], timeout=timeout,
                   output_limit=output_limit)

    def test_separate_stdout_stderr_and_success(self):
        result = self.execute(
            "import os; os.write(1,b'out'); os.write(2,b'err')")
        self.assertEqual(result["returncode"], 0)
        self.assertIsNone(result["limit_reason"])
        self.assertEqual(result["stdout"], b"out")
        self.assertEqual(result["stderr"], b"err")

    def test_nonzero_status_is_preserved(self):
        result = self.execute("raise SystemExit(7)")
        self.assertEqual(result["returncode"], 7)
        self.assertIsNone(result["limit_reason"])

    def test_timeout_terminates_and_reaps_leader(self):
        started = time.monotonic()
        result = self.execute("import time; time.sleep(20)", timeout=0.2)
        self.assertEqual(result["limit_reason"], "timeout")
        self.assertLess(time.monotonic() - started, 5)
        with self.assertRaises(ChildProcessError):
            os.waitpid(result["pid"], os.WNOHANG)

    def test_combined_output_cap(self):
        result = self.execute("import os; os.write(1,b'x'*10000)", output_limit=32)
        self.assertEqual(result["limit_reason"], "output_limit")
        self.assertEqual(len(result["stdout"]) + len(result["stderr"]), 32)

    def test_termination_resistant_leader_is_killed(self):
        started = time.monotonic()
        result = self.execute(
            "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
            "print('installed',flush=True); time.sleep(20)", timeout=0.3)
        self.assertIn(b"installed", result["stdout"])
        self.assertEqual(result["limit_reason"], "timeout")
        self.assertEqual(result["returncode"], -9)
        self.assertLess(time.monotonic() - started, 5)

    def test_inherited_pipe_does_not_outlive_deadline(self):
        for attempt in range(10):
            with self.subTest(attempt=attempt):
                started = time.monotonic()
                result = self.execute(
                    "import os,time; child=os.fork(); "
                    "time.sleep(20) if child == 0 else os._exit(0)", timeout=0.3)
                self.assertEqual(result["limit_reason"], "timeout")
                self.assertLess(time.monotonic() - started, 5)

    def test_term_signal_failure_still_reaps_and_closes(self):
        failure = PermissionError("injected TERM failure")
        original_signal_group = process_runner._signal_group

        def fail_term(pid, sig):
            if sig == signal.SIGTERM:
                raise failure
            return original_signal_group(pid, sig)

        with self.track_real_children() as children:
            with patch("process_runner._signal_group", side_effect=fail_term):
                with self.assertRaises(PermissionError) as caught:
                    self.execute("import time; time.sleep(20)", timeout=0.1)
            self.assertIs(caught.exception, failure)
            self.assertEqual(len(children), 1)
            self.assert_reaped_and_closed(children[0])

    def test_selector_initialization_failure_still_reaps_and_closes(self):
        failure = OSError("injected selector initialization failure")
        with self.track_real_children() as children:
            with patch("process_runner.selectors.DefaultSelector", side_effect=failure):
                with self.assertRaises(OSError) as caught:
                    self.execute("import time; time.sleep(20)", timeout=0.1)
            self.assertIs(caught.exception, failure)
            for child in children:
                self.assert_reaped_and_closed(child)

    def test_group_signal_failures_preserve_errors_and_kill_leader(self):
        term_failure = PermissionError("injected TERM failure")
        kill_failure = PermissionError("injected KILL failure")

        def fail_group(pid, sig):
            raise term_failure if sig == signal.SIGTERM else kill_failure

        with self.track_real_children() as children:
            started = time.monotonic()
            with patch("process_runner._signal_group", side_effect=fail_group):
                with self.assertRaises(BaseException) as caught:
                    self.execute("import time; time.sleep(20)", timeout=0.1)
            self.assertLess(time.monotonic() - started, 5)
            self.assertEqual(len(children), 1)
            self.assert_reaped_and_closed(children[0])
            self.assertIsInstance(caught.exception, BaseExceptionGroup)
            self.assertEqual(caught.exception.exceptions, (term_failure, kill_failure))


if __name__ == "__main__":
    unittest.main()
