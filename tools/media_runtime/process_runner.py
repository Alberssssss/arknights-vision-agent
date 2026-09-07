"""Local experiment-only process bounds; not an operating-system sandbox."""

import os
import selectors
import signal
import subprocess
import time


def _signal_group(pid, sig):
    # This Mac can report transient EPERM while a just-terminated orphan group
    # disappears. Retry briefly until a signal succeeds or ESRCH confirms its
    # absence. Persistent permission errors are never ignored.
    until = time.monotonic() + 0.1
    while True:
        try:
            os.killpg(pid, sig)
            return
        except ProcessLookupError:
            return
        except PermissionError:
            if time.monotonic() >= until:
                raise
            time.sleep(0.01)


def _cleanup(process, selector):
    errors = []

    def attempt(operation, *args, **kwargs):
        try:
            operation(*args, **kwargs)
        except BaseException as error:
            errors.append(error)

    # No failed cleanup operation may skip the remaining independent attempts.
    # Group failures remain errors even when the leader-only fallback succeeds.
    attempt(_signal_group, process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    except BaseException as error:
        errors.append(error)
    attempt(_signal_group, process.pid, signal.SIGKILL)
    if process.returncode is None:
        attempt(process.kill)
    attempt(process.wait, timeout=2)
    if selector is not None:
        attempt(selector.close)
    attempt(process.stdout.close)
    attempt(process.stderr.close)

    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise BaseExceptionGroup("experiment process cleanup failed", errors)


def run(argv, *, timeout, output_limit=8 * 1024 * 1024, cwd=None, env=None):
    if timeout <= 0 or output_limit <= 0:
        raise ValueError("positive experiment limits required")
    started = time.monotonic()
    channels = {"stdout": bytearray(), "stderr": bytearray()}
    limit_reason = None
    observed = 0
    selector = None
    process = subprocess.Popen(
        argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
    )
    try:
        selector = selectors.DefaultSelector()
        for name in channels:
            selector.register(getattr(process, name), selectors.EVENT_READ, name)
        while selector.get_map() or process.poll() is None:
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                limit_reason = "timeout"
                break
            for key, _ in selector.select(min(0.05, remaining)):
                block = os.read(key.fileobj.fileno(), 65536)
                if not block:
                    selector.unregister(key.fileobj)
                    continue
                allowed = max(0, output_limit - observed)
                channels[key.data].extend(block[:allowed])
                observed += len(block)
                if observed > output_limit:
                    limit_reason = "output_limit"
                    break
            if limit_reason:
                break
    finally:
        # Also close descendants that retain a pipe after their leader exits.
        # These are only members of the new process group started by this call.
        _cleanup(process, selector)
    return {
        "pid": process.pid,
        "returncode": process.returncode,
        "limit_reason": limit_reason,
        "elapsed_seconds": time.monotonic() - started,
        "stdout": bytes(channels["stdout"]),
        "stderr": bytes(channels["stderr"]),
    }
