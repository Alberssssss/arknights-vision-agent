# Explicit Byte Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inventory explicitly selected local bytes without decoding media, modifying source files, or starting training.

**Architecture:** A pure request validator and shared lexical path predicate precede a bounded descriptor-based POSIX reader. A separate CLI input boundary reads strict regular-file JSON and reuses exclusive report writing. Deterministic content fingerprints remain separate from demonstration metadata, rights, label evidence, and future decoding.

**Tech Stack:** Python 3.11+ standard library; `unittest`, temporary synthetic files, real subprocess CLI checks; no new dependencies.

---

**Execution record (2026-09-07):** Task 1 implemented in `8ef2c25`; all 246 tests, compilation, and diff checks passed. Separate specification and final quality/integration reviews passed without findings. Coordinator verified all three real installed commands using a fresh offline wheel and confirmed repeat-output refusal without modification. The step checkboxes below preserve the original plan; this task is not pending reimplementation. See `STATUS.md` for evidence and remaining boundaries.

## Task 1: Inventory API, command, synthetic example, and documentation

This is one integrated small boundary, implemented by one worker and reviewed before publication. The coordinator provides the complete `2026-09-07-byte-inventory-design.md` specification as task context. Preserve the development branch and unrelated changes. Do not run the command against anything except committed/project-authored synthetic assets or test-owned temporary files.

**Files:**

- Create `src/arknights_vision_agent/media_paths.py`: shared literal relative path predicate only.
- Modify `src/arknights_vision_agent/demonstrations.py`: delegate lexical path validation, retaining all prior accepted/rejected values.
- Create `src/arknights_vision_agent/inventory.py`: pure request validation, file boundary, hash/report API.
- Modify `src/arknights_vision_agent/cli.py`: inventory parser, request-file reader, dispatch/error handling.
- Create `tests/test_inventory.py`, `tests/test_inventory_cli.py`.
- Create `examples/synthetic_inventory.json`, `examples/synthetic_inventory_assets/a.txt`, `b.txt`, `c.txt`.
- Modify `README.md`: runnable example and honest limits. Do not modify `STATUS.md` or broader collection docs; coordinator owns those.

### Step 1: Establish red tests and shared path semantics

- [ ] Start with this API test, run it, and confirm the new API is missing before implementing:

```python
import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from arknights_vision_agent.inventory import (
    InventoryError, build_inventory, validate_inventory_request,
)


def request_for(*pairs):
    return {"schema_version": 1,
            "assets": [{"asset_id": identifier, "path": path}
                       for identifier, path in pairs]}


class InventoryTests(unittest.TestCase):
    def test_known_bytes_and_detached_validation(self):
        request = request_for(("asset-a", "source.bin"))
        validated = validate_inventory_request(request)
        self.assertEqual(request, validated)
        self.assertIsNot(request, validated)
        self.assertIsNot(request["assets"][0], validated["assets"][0])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.bin").write_bytes(b"abc")
            report = build_inventory(request, media_root=root,
                                     max_file_bytes=3, max_total_bytes=3)
            self.assertEqual(report["assets"], [{
                "asset_id": "asset-a", "path": "source.bin", "size_bytes": 3,
                "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            }])
            self.assertEqual(report["summary"], {
                "asset_count": 1, "total_bytes": 3, "duplicate_group_count": 0,
            })
            self.assertEqual((root / "source.bin").read_bytes(), b"abc")
```

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -p test_inventory.py -v`. Record the expected missing-module/API failure. Add rejection cases before their validation branches.
- [ ] Extract the lexical predicate with this full implementation. The manifest wrapper calls it and raises its own index/field-specific `ManifestValidationError` on false. Remove the now-unused manifest import of `unicodedata`.

```python
import unicodedata


def is_valid_media_path(value: object) -> bool:
    if type(value) is not str or not 1 <= len(value) <= 1024:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return not (
        value.startswith(("/", "~"))
        or "\\" in value or ":" in value
        or any(unicodedata.category(c) == "Cc" for c in value)
        or any(part in ("", ".", "..") for part in value.split("/"))
    )
```

```python
def _require_media_path(value, where):
    if not is_valid_media_path(value):
        raise ManifestValidationError(
            f"{where} is not a literal relative media reference"
        )
```

- [ ] Run all existing demonstration/action tests after this extraction. Add invalid/valid path cases to inventory tests, including literal dollar signs, percent sequences, Unicode, controls, surrogate text, and all traversal/URL/absolute variants.

### Step 2: Implement the detached validator under tests

- [ ] Use constants `MAX_ASSETS = 1000`, `READ_CHUNK_BYTES = 1048576`, `DEFAULT_MAX_FILE_BYTES = 1073741824`, `DEFAULT_MAX_TOTAL_BYTES = 4294967296`. The following specifies the exact request validator implementation:

```python
class InventoryError(ValueError):
    """Invalid inventory configuration or an unavailable selected file."""


def validate_inventory_request(request: dict) -> dict:
    if type(request) is not dict or set(request) != {"schema_version", "assets"}:
        raise InventoryError("inventory request fields do not match the schema")
    if type(request["schema_version"]) is not int or request["schema_version"] != 1:
        raise InventoryError("inventory schema_version must be integer 1")
    assets = request["assets"]
    if type(assets) is not list or not 1 <= len(assets) <= MAX_ASSETS:
        raise InventoryError("inventory assets must be a plain list of 1..1000 entries")
    ids, paths = set(), set()
    for index, asset in enumerate(assets, 1):
        if type(asset) is not dict or set(asset) != {"asset_id", "path"}:
            raise InventoryError(f"asset {index} fields do not match the schema")
        if not is_valid_identifier(asset["asset_id"]):
            raise InventoryError(f"asset {index} asset_id is invalid")
        if not is_valid_media_path(asset["path"]):
            raise InventoryError(f"asset {index} path is not a literal relative reference")
        if asset["asset_id"] in ids or asset["path"] in paths:
            raise InventoryError(f"asset {index} repeats an ID or literal path")
        ids.add(asset["asset_id"])
        paths.add(asset["path"])
    return copy.deepcopy(request)


def _validate_cap(value, name):
    if type(value) is not int or not 1 <= value <= 2**63 - 1:
        raise InventoryError(f"{name} must be an integer in 1..2**63-1")
```

- [ ] Test exact schema keys/types, duplicate IDs/paths, zero/1000/1001 assets, invalid late entries and invalid caps. For the no-open assertion patch only the root-opening helper (not the high-level public API); also pass a nonexistent root so a validation failure is distinguishable from file-access failure. No public test-only hooks.

### Step 3: Implement the bounded reader under real-file tests

- [ ] Add real nested, empty, arbitrary binary, multi-chunk, hard-link, symlink, directory, FIFO, missing-source, and root-symlink tests before implementing each corresponding behavior. Keep FIFO CLI tests in subprocesses with a timeout so regressions cannot hang the suite.
- [ ] Implement a capability guard, root-opening context manager, descriptor-relative asset-opening context manager, and `_hash_file` function. This full code gives their interfaces/behavior; internal helper names may differ while preserving the spec:

```python
def require_inventory_platform():
    if (os.name != "posix" or os.open not in os.supports_dir_fd
            or any(not hasattr(os, flag) for flag in
                   ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"))):
        raise InventoryError("inventory requires POSIX descriptor-relative no-follow file access")


@contextmanager
def _open_root(media_root):
    try:
        resolved = Path(media_root).resolve(strict=True)
        descriptor = os.open(resolved, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise InventoryError("cannot open the configured media root") from error
    try:
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def _open_asset(root_descriptor, path):
    current = os.dup(root_descriptor)
    try:
        parts = path.split("/")
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW
            flags |= os.O_NONBLOCK if index == len(parts) - 1 else os.O_DIRECTORY
            child = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = child
        yield current
    finally:
        os.close(current)


def _stat_identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


def _hash_file(descriptor, allowance):
    before = os.fstat(descriptor)
    if not stat.S_ISREG(before.st_mode):
        raise InventoryError("selected asset is not a regular file")
    if not 0 <= before.st_size <= allowance:
        raise InventoryError("selected asset exceeds the byte limit")
    digest, count = hashlib.sha256(), 0
    while True:
        block = os.read(descriptor, min(READ_CHUNK_BYTES, allowance - count + 1))
        if not block:
            break
        count += len(block)
        if count > allowance:
            raise InventoryError("selected asset exceeds the byte limit")
        digest.update(block)
    after = os.fstat(descriptor)
    if count != before.st_size or _stat_identity(before) != _stat_identity(after):
        raise InventoryError("selected asset changed while hashing")
    return count, digest.hexdigest()
```

- [ ] Add the necessary imports (`copy`, `hashlib`, `os`, `stat`, `contextmanager`, `Path`, shared identifier/path predicates). No imports from model/controller packages.
- [ ] `build_inventory` first calls the detached validator, validates both caps, then the capability guard. In one root context it iterates validated assets, opens each selected file, and calls `_hash_file` with `min(max_file_bytes, max_total_bytes - total_bytes)`. Wrap file errors as `InventoryError` with the original request's 1-based asset index, a fixed stage message, and no source values. Preserve specific safe `InventoryError` reasons; never interpolate raw `OSError`. Reject all failures, not skip-and-continue. Update totals only after successful hashing.
- [ ] Build exactly the report shape in the spec. Sort assets by ID; group equal `(size_bytes, sha256)` rows; emit groups with at least two IDs, ordered by `(sha256, size_bytes)`. Set only `file_bytes_hashed` true; all six other verification fields false. Never serialize root paths, inode/times, or source bytes.
- [ ] Write deterministic tests for inclusive file/total caps, one-byte overflow, growth, truncation, same-size mutation, read failure, capability rejection, and descriptor cleanup. Fault injection wraps low-level `os.read`/`fstat` operations while still using real files; assert the resulting public error/report, not merely that a mock was called. Check all requested reads are bounded by `READ_CHUNK_BYTES` and total-limit sentinel behavior is bounded. Verify that reorderings produce equal reports and multiple duplicate groups sort correctly.

### Step 4: Wire the real command under failing subprocess tests

- [ ] Create a CLI test helper that invokes `[sys.executable, "-m", "arknights_vision_agent", *arguments]` with source `PYTHONPATH`, no stdin, captured output, and `timeout=10`. Add help and synthetic-example tests, then run them to confirm the missing command.
- [ ] Add an `inventory` subparser with required `--request`, `--media-root`, `--output` paths and optional integer byte-cap flags with the API defaults. No other new flags. Add inventory imports and `stat` to the CLI. Preserve every replay/preparation option and error label.
- [ ] Implement the following request and command boundaries after their red tests:

```python
def _load_inventory_request(path):
    require_inventory_platform()
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as input_file:
            if not stat.S_ISREG(os.fstat(input_file.fileno()).st_mode):
                raise InventoryError("inventory request must be a regular file")
            payload = input_file.read(_TRACE_MAX_BYTES + 1)
    except OSError as error:
        raise InventoryError("cannot read the inventory request") from error
    if len(payload) > _TRACE_MAX_BYTES:
        raise InventoryError("inventory request exceeds the 2 MiB size limit")
    try:
        decoded = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise InventoryError("inventory request is not valid UTF-8") from error
    return load_json_object(decoded, max_bytes=_TRACE_MAX_BYTES)


def _inventory_command(arguments):
    if os.path.lexists(arguments.output):
        raise _CLIError(f"output path already exists: {arguments.output}")
    request = _load_inventory_request(arguments.request)
    report = build_inventory(request, media_root=arguments.media_root,
                             max_file_bytes=arguments.max_file_bytes,
                             max_total_bytes=arguments.max_total_bytes)
    rendered = json.dumps(report, allow_nan=False, sort_keys=True,
                          separators=(",", ":")) + "\n"
    _write_report_files(arguments.output, {"inventory.json": rendered})
    print(f"Inventory written to {arguments.output}; "
          f"{report['summary']['asset_count']} selected assets hashed; "
          "no media decoded and no training started.")
    print("Keep real reports private; duplicate candidates require review.")
    return 0
```

- [ ] Add dispatch for inventory; catch `InventoryError` with `error: invalid inventory: ...` and exit 2. In `StrictJSONError` handling choose the label from `{"replay":"trace", "prepare":"manifest", "inventory":"inventory request"}`. Existing raw output-path errors may name the user-selected output; media/read failures must not name source paths/roots.
- [ ] Cover request regular-only/FIFO rejection, UTF-8/duplicate JSON keys/nonfinite numbers/surrogates/top-level arrays, exact 2 MiB/+1 limits, missing required flags, invalid caps, unsupported platform (direct boundary test), privacy, no new output parents on failure, and old commands unchanged. Existing file/directory/live and dangling output symlinks must be refused before opening even a missing request. Repeat after success and assert unchanged report bytes. Inject write failure and assert no success text; retain any newly created partial output as documented.

### Step 5: Synthetic fixture and user documentation

- [ ] Create request with three IDs `synthetic-a`, `synthetic-b`, `synthetic-c` and paths `synthetic_inventory_assets/a.txt`, `b.txt`, `c.txt`. The files contain respectively `synthetic inventory alpha\n`, `synthetic inventory alpha\n`, and `synthetic inventory beta\n`. Use `apply_patch`; they are plain text, not pretend video.
- [ ] Add the exact runnable inventory command from the spec to README before Development. Explain `inventory.json`, 1 GiB/file and 4 GiB total defaults with integer-byte overrides, 1000-asset/request/1-MiB-chunk caps, POSIX-only reader, regular files, no descendant symlinks, owner-trusted root/output, sources not intentionally modified, potential access-time effects, no scanning/copying/decoding/training, private reports, duplicate-candidate review, no immutable snapshot guarantee, and remaining timestamp/label work. Link the spec. Keep explanations concise and existing boundaries intact.
- [ ] Test the fixture's one two-asset duplicate candidate, distinct third file, exact serialized JSON, report flags, private/source-root omission, and documentation's key command/boundary statements.

### Step 6: Verify, commit, and independent reviews

- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `python3 -m compileall -q src tests`, and `git diff --check`. Inspect the complete diff. Commit only task-owned files with `feat: inventory explicitly selected local assets`.
- [ ] Implementer reports red/green evidence, exact checks/counts, limitations, commit, and any concerns; do not push or update coordinator docs.
- [ ] Coordinator obtains a specification review, then independent quality/final integration review. Return findings to the original implementer with regression tests before re-review. No implementation-specific approval is inferred from a passing suite alone.
- [ ] Coordinator freshly verifies all tests, builds/installs a wheel without index/dependencies into a new ignored environment, and runs installed inventory, preparation, and replay commands under isolated Python mode. Inspect output and repeat-output refusal. Use only synthetic fixtures.
- [ ] Update status and collection docs with observed evidence and limits, publish the reviewed branch without force, verify remote/local equality, and preserve the active overall goal and deferred-training instruction.
