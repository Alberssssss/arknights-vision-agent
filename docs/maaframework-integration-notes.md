# MaaFramework integration notes

Inspected on 2026-09-07 against the version-pinned `v5.12.3` source. This is a future integration contract, not an implemented or live-tested backend. MAA and MaaFramework are distinct projects; the first offline milestone imports neither.

## Verified interfaces

The Python `AdbController` accepts an ADB path and device address, plus capture/input methods, configuration, and an agent path. Its methods include `post_connection`, `post_screencap`, `post_click`, and `post_swipe`. Clicks and swipes return jobs; swipe duration is in milliseconds. Screenshot dimensions may be scaled relative to the raw `resolution` property. The capture result getter returns the latest cached image rather than a job-specific immutable frame: capture, completion check, and retrieval therefore need serial coordination.

Source: <https://raw.githubusercontent.com/MaaXYZ/MaaFramework/v5.12.3/source/binding/Python/maa/controller.py>

The Python job wrapper's `wait()` has no timeout argument and returns the job. Returning from it is not a success Boolean. A future adapter must inspect status and retrieve results only after success. The project should provide its own bounded deadline and stop dispatching further operations when the outcome is uncertain.

Source: <https://raw.githubusercontent.com/MaaXYZ/MaaFramework/v5.12.3/source/binding/Python/maa/job.py>

Native ADB screenshot recovery can kill the ADB server and reconnect. Consequently, even a future capture-only experiment can affect a shared ADB environment; it must not be described as inherently side-effect-free.

Source: <https://raw.githubusercontent.com/MaaXYZ/MaaFramework/v5.12.3/source/MaaAdbControlUnit/Manager/AdbControlUnitMgr.cpp>

## Proposed project gates

These are project design decisions, not guarantees provided by the SDK:

1. Replay and dry-run never import MaaFramework or connect to a device.
2. A later live adapter requires an explicit configuration and approved test device. Never discover and operate on an arbitrary connected device by default.
3. Capture must complete and produce a validated image before any location-dependent action is considered.
4. Coordinates remain in one documented pixel space; a real calibration test must rule out double scaling and changed dimensions.
5. Submit one action at a time. After timeout or uncertain completion, latch the session stopped rather than retrying a potentially completed input.
6. A wrapper deadline is not proof that an already-submitted native action was cancelled.
7. API success and observed game-state success are separate events. Confirm effects from a fresh observation.
8. App installation, shell commands, account entry, purchases, app start/stop, and unrestricted text input are outside the initial action vocabulary.

## Deferred verification

`HUMAN_HELP.md` items H04 and H07 cover the real device, permission, capture/resolution checks, harmless input calibration, and supervised stop conditions. Until then, SDK-contract tests can use an injected boundary double, but such tests must not be reported as real-device validation.
