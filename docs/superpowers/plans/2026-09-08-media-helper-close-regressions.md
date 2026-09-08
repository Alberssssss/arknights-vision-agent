# Media-helper close-failure regression plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retain the three close-failure checks already identified in the reviewed local-runtime design as permanent, real-child regressions.

**Architecture:** Extend only the developer helper's test module. Exercise the real runner and child processes; inject failures at the real selector/stdout close operations, after those operations perform their real close. Assert cleanup and exception identity before any test fallback. Do not change `process_runner.py`, product code, public APIs or dependency requirements.

**Tech Stack:** Python standard-library unittest, subprocess, selectors, context managers and targeted failure injection; current POSIX/macOS development host.

This is the explicit nonblocking follow-up in the [existing runtime design](../specs/2026-09-07-media-runtime-design.md), not implementation of the newly proposed native index. Work in the existing `codex/offline-foundation` checkout; preserve unrelated documents and the development branch. The coordinator owns exact staging, review and publication.

## Task 1: Preserve close-failure regressions

**Files:**

- Modify: `tools/media_runtime/test_process_runner.py` only.
- Inspect without changing: `tools/media_runtime/process_runner.py`.
- Private diagnostics: a new ignored `work/helper-close-check-XXXXXX/` directory.

- [x] Verify the existing helper's nine-test baseline and record the current runner SHA-256. Read both files completely. The new tests do not justify a runtime modification unless they expose a genuine defect, which must be reported first.

  ```sh
  python3 -m unittest discover -s tools/media_runtime -p 'test_*.py' -v
  shasum -a 256 tools/media_runtime/process_runner.py
  ```

- [x] Add `ExitStack` to the existing contextlib import and a small test-only context manager inside `ProcessRunnerTests`. Preserve real selector behavior and real subprocess creation. The outer child tracker must encompass every fault injection and all assertions; selector fallback runs only after assertions and after patches are removed.

  ```python
  @contextmanager
  def track_close_failures(self, *, selector_failure=None, stdout_failure=None):
      selectors = []
      selector_closers = []
      original_selector = process_runner.selectors.DefaultSelector
      with self.track_real_children() as children:
          try:
              with ExitStack() as patches:
                  tracked_popen = process_runner.subprocess.Popen

                  def create_selector(*args, **kwargs):
                      selector = original_selector(*args, **kwargs)
                      selectors.append(selector)
                      real_close = selector.close
                      selector_closers.append(real_close)
                      if selector_failure is not None:
                          def fail_close():
                              real_close()
                              raise selector_failure
                          patches.enter_context(patch.object(
                              selector, "close", side_effect=fail_close))
                      return selector

                  def create_child(*args, **kwargs):
                      child = tracked_popen(*args, **kwargs)
                      if stdout_failure is not None:
                          real_close = child.stdout.close
                          def fail_close():
                              real_close()
                              raise stdout_failure
                          patches.enter_context(patch.object(
                              child.stdout, "close", side_effect=fail_close))
                      return child

                  patches.enter_context(patch(
                      "process_runner.selectors.DefaultSelector",
                      side_effect=create_selector))
                  patches.enter_context(patch(
                      "process_runner.subprocess.Popen", side_effect=create_child))
                  yield children, selectors
          finally:
              for close in selector_closers:
                  close()
  ```

- [x] Add these three tests. A close-then-raise injection checks that the runner retains the failure and attempts later cleanup; it does not assert that a resource whose real close failed must magically be closed. These tests assert real descriptor state and actual leader reaping, not merely mock call counts.

  ```python
  def test_selector_close_failure_still_closes_pipes(self):
      failure = OSError("injected selector close failure")
      with self.track_close_failures(selector_failure=failure) as (children, selectors):
          with self.assertRaises(BaseException) as caught:
              self.execute("import time; time.sleep(20)", timeout=0.1)
          self.assertEqual(len(children), 1)
          self.assertEqual(len(selectors), 1)
          self.assert_reaped_and_closed(children[0])
          self.assertIsNone(selectors[0].get_map())
          self.assertIs(caught.exception, failure)

  def test_stdout_close_failure_still_closes_stderr(self):
      failure = OSError("injected stdout close failure")
      with self.track_close_failures(stdout_failure=failure) as (children, selectors):
          with self.assertRaises(BaseException) as caught:
              self.execute("import time; time.sleep(20)", timeout=0.1)
          self.assertEqual(len(children), 1)
          self.assertEqual(len(selectors), 1)
          self.assert_reaped_and_closed(children[0])
          self.assertIsNone(selectors[0].get_map())
          self.assertIs(caught.exception, failure)

  def test_combined_close_failures_preserve_errors(self):
      selector_failure = OSError("injected selector close failure")
      stdout_failure = OSError("injected stdout close failure")
      with self.track_close_failures(
          selector_failure=selector_failure, stdout_failure=stdout_failure,
      ) as (children, selectors):
          with self.assertRaises(BaseException) as caught:
              self.execute("import time; time.sleep(20)", timeout=0.1)
          self.assertEqual(len(children), 1)
          self.assertEqual(len(selectors), 1)
          self.assert_reaped_and_closed(children[0])
          self.assertIsNone(selectors[0].get_map())
          self.assertIsInstance(caught.exception, BaseExceptionGroup)
          self.assertEqual(caught.exception.exceptions,
                           (selector_failure, stdout_failure))
  ```

- [x] Prove regression sensitivity without editing the tracked runner. In a bounded ignored diagnostic, import the real tests and temporarily replace only the module's `_cleanup` function using `patch.object` or the equivalent string-target `patch`. Run the three named tests against each of the following deliberately faulty variants; restore the real function when each context exits. Retain exact outputs and runner identity before/after.

  ```python
  def fail_fast_cleanup(process, selector):
      process_runner._signal_group(process.pid, signal.SIGTERM)
      try:
          process.wait(timeout=2)
      except subprocess.TimeoutExpired:
          pass
      process_runner._signal_group(process.pid, signal.SIGKILL)
      if process.returncode is None:
          process.kill()
      process.wait(timeout=2)
      if selector is not None:
          selector.close()
      process.stdout.close()
      process.stderr.close()

  real_cleanup = process_runner._cleanup

  def discard_later_error(process, selector):
      try:
          real_cleanup(process, selector)
      except BaseExceptionGroup as error:
          raise error.exceptions[0]
  ```

  Use `unittest.TestSuite` with these exact names and `TextTestRunner`:

  ```python
  names = [
      "test_selector_close_failure_still_closes_pipes",
      "test_stdout_close_failure_still_closes_stderr",
      "test_combined_close_failures_preserve_errors",
  ]
  suite = unittest.TestSuite(ProcessRunnerTests(name) for name in names)
  ```

  Expected: fail-fast variant has three assertion failures and zero errors; dropped-error variant has exactly one assertion failure in the combined-error test and zero errors. Each test's own fallback must clean up its children after assertions even on deliberate failure. These are intentionally failing diagnostics, not a claim of a defect in the unchanged real runner.

- [x] Run all three new tests against the real runner and then the full helper suite. Expect three and twelve passing tests respectively. Run the 307-test application suite, compilation and diff checks; confirm the runner hash and all product blobs are unchanged. No native decoder, model, private media or device is involved.

  ```sh
  PYTHONPATH=tools/media_runtime python3 -m unittest -v \
    test_process_runner.ProcessRunnerTests.test_selector_close_failure_still_closes_pipes \
    test_process_runner.ProcessRunnerTests.test_stdout_close_failure_still_closes_stderr \
    test_process_runner.ProcessRunnerTests.test_combined_close_failures_preserve_errors
  python3 -m unittest discover -s tools/media_runtime -p 'test_*.py' -v
  PYTHONPATH=src python3 -m unittest discover -s tests -q
  python3 -m compileall -q src tests tools/media_runtime
  git diff --check
  ```

- [x] Obtain independent specification review, then a separate quality review. Inspect actual code/results, not just the implementer's report. Fix any real review finding and rerun the relevant checks before publishing.

## Task 2: Record the reviewed evidence

**Files:** this plan; `tools/media_runtime/README.md`; current-test-count references in `AGENTS.md`, `HANDOFF.md` and `docs/continuation-guide.md`; dated results in `STATUS.md`. Preserve the original nine-test evidence in the runtime receipt/design as history, adding a dated follow-up link where needed.

- [x] Record exact results, platform, regression diagnostic outcomes, unchanged runner/product identity and the helper-only scope. Distinguish permanent twelve-test coverage from the original nine-test experiment. Retain raw local logs in ignored `work/` only.
- [x] Independently review the documentation delta and local links. Inspect the exact staged files for private paths, credentials and unrelated changes.

**Publication gate, after the reviewed files are committed:** Push normally
within the established main/development-branch scope, using the configured
GitHub no-reply identity for commits. Verify real remote refs after publishing;
a pre-push checklist cannot attest to a later remote result. Preserve the branch
and local checkout; do not force-push or alter repository permissions. The test
checkpoint is `5e5abf8bf28f0fa1a1da1bbc0945976c8255ada5`; use actual Git history
and remote state to establish which documentation closeout includes it.

This follow-up does not unblock private recordings, target H20 access, a native
indexing implementation, extraction, training or live gameplay. Keep the next
handoff and any separate design-review dependency explicit.
