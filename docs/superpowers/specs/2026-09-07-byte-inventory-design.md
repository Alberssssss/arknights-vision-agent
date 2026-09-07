# Explicit local byte inventory

Date: 2026-09-07. Scope: the next reversible preparation boundary under the owner's autonomous-development direction. Actual training remains deferred. Development and acceptance use only project-authored synthetic bytes, never private media or a device.

## Choice and purpose

Build a byte inventory before native decoding. An explicit selection works before action labels exist, so it must not require a demonstration manifest. This supplies content fingerprints for later provenance and duplicate review without guessing video timing or actions.

Alternatives considered: reading assets from demonstration manifests would require labels too early; recursive folder import would broaden access and make resource limits less predictable; decoding videos now would combine byte identity with a separate native-parser/timestamp boundary. Select a small explicit request instead. Native decoding, thumbnail extraction, annotation UI, manifest joins, automatic deduplication, and training exports are outside this milestone.

## Request and public API

`validate_inventory_request(request: dict) -> dict` is pure and returns a detached validated copy. `build_inventory(request: dict, *, media_root: Path, max_file_bytes: int = 1073741824, max_total_bytes: int = 4294967296) -> dict` validates everything before opening media, then reads only the selected files. `InventoryError(ValueError)` represents expected request, configuration, platform, and selected-file failures.

Exact request shape (no extra/missing fields):

```json
{"schema_version":1,"assets":[{"asset_id":"source-a","path":"session-a/original.mp4"}]}
```

- Plain dictionary, integer schema version exactly 1 (not Boolean), plain list of 1..1000 plain asset dictionaries with exactly `asset_id` and `path`.
- IDs use the existing opaque-identifier predicate. IDs and literal paths must each be unique. No normalization or case folding.
- Paths use the existing manifest's lexical contract: plain UTF-8-encodable string, 1..1024 characters, no leading `/` or `~`, backslash, colon, Unicode control character (category Cc), empty segment, `.` segment, or `..` segment. No interpolation, URL decoding, expansion, or globbing.
- Extract this path predicate into `media_paths.py`; retain the manifest's accepted/rejected inputs. Error wording may be unified, but remains index/field-based and must not echo submitted values.
- Byte caps are exact integers in `1..2**63-1`, inclusive. The total cap may be smaller than the file cap. All request entries and both caps must be validated before opening the root. Malformed excluded/late entries are not silently skipped.
- Empty files and arbitrary binary/text files are valid inventory inputs. File extensions do not establish media type. Hard links are allowed; distinct requested paths count separately toward asset count and total bytes.

## Filesystem boundary

This reader supports POSIX systems that provide descriptor-relative `os.open` and `O_DIRECTORY`, `O_NOFOLLOW`, and `O_NONBLOCK`; refuse unsupported platforms rather than silently weakening the boundary. Python core imports, help, replay, and metadata preparation remain portable.

`media_root` is a trusted, explicitly supplied owner configuration, not a request field. Resolve it once (including a user-selected root symlink), open it as a directory with `O_NOFOLLOW`, and pin the descriptor. Its containing directories and filesystem are trusted; this is not a system-wide filesystem sandbox. Do not output its absolute path.

For each validated relative path, walk its components relative to pinned directory descriptors. Open intermediate components with `O_DIRECTORY|O_NOFOLLOW`; open the final component with `O_NOFOLLOW|O_NONBLOCK`. Check the final descriptor with `fstat` and require a regular file before reading. This avoids opening a selected FIFO in blocking mode. Close every descriptor on success and failure. Never enumerate directories, invoke a shell/subprocess, contact a network service, or import a media/model/controller package.

Hash the bytes read using SHA-256, in chunks no larger than 1 MiB. Check the initial size against the per-file and remaining-total caps before reading, enforce both while reading (at most one over-limit sentinel byte before rejection), and require the observed byte count to equal the initial size. Compare `(st_dev, st_ino, st_mode, st_size, st_mtime_ns, st_ctime_ns)` before/after reading to reject detectable changes. Do not compare access time, which reads may change.

These checks are not an immutable snapshot, a hostile-filesystem guarantee, or a wall-clock timeout for stalled filesystems. The owner must supply stable local originals. Hard links, mount points, ancestor replacement, or privileged concurrent changes are not a security boundary. Content can change after hashing. Later decoding must recheck content identity.

On any selected-file failure, return no successful/partial report. Raise a concise index/stage-based error without asset IDs, paths, source contents, absolute roots, or raw OS error messages. No media file is written, copied, renamed, removed, or modified intentionally; ordinary filesystem access-time effects are not prevented.

## Deterministic report

Exact report keys:

```json
{
  "schema_version":1,
  "scope":"local_byte_inventory",
  "hash_algorithm":"sha256-bytes-v1",
  "limits":{"max_assets":1000,"max_file_bytes":1073741824,"max_total_bytes":4294967296,"read_chunk_bytes":1048576},
  "assets":[{"asset_id":"source-a","path":"session-a/original.mp4","size_bytes":3,"sha256":"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}],
  "duplicate_candidates":[],
  "summary":{"asset_count":1,"total_bytes":3,"duplicate_group_count":0},
  "verification":{"file_bytes_hashed":true,"media_decoded":false,"timestamps_verified":false,"label_evidence_verified":false,"permission_verified":false,"training_started":false,"game_clear_verified":false}
}
```

Assets sort by `asset_id` using Python string ordering. Group rows with equal `(size_bytes, sha256)` into `duplicate_candidates` only when at least two assets match. Each group has exactly `size_bytes`, `sha256`, and sorted `asset_ids`; groups sort by `(sha256, size_bytes)`. The hash covers file bytes only, without a prefix or metadata. Reordering the request with unchanged stable files produces the same report.

No absolute root, resolved paths, wall-clock creation time, inode values, or source bytes are serialized. The relative names/IDs and hashes are still potentially sensitive: keep real reports private. A matching size/hash is an exact-byte duplicate candidate, not detection of edited/near-duplicate recordings. Do not delete files, merge leakage groups, or mark examples eligible automatically. No duration, frame count, source type, permission, or label is inferred.

## Command

```sh
PYTHONPATH=src python3 -m arknights_vision_agent inventory \
  --request examples/synthetic_inventory.json \
  --media-root examples --output work/inventory-demo
```

Optional `--max-file-bytes` and `--max-total-bytes` override the recorded caps. Required flags are explicit; there are no discovery/default-private-root/download/force options.

The request file is user-selected and may be a symlink. Open it nonblocking, require a regular file, and read at most 2 MiB + 1 bytes. Reuse strict UTF-8/JSON parsing. This guards request FIFOs without changing existing replay/preparation readers. Refuse an already-existing output file/directory/live or dangling symlink before reading the request or media; still use exclusive output creation after a successful, fully rendered report. Input errors and failed hashing create no output or missing output parents. Expected errors exit exactly 2 without traceback or submitted payloads. No report is claimed after failure.

On success write exactly `inventory.json` in a new output directory, as finite sorted-key compact UTF-8 JSON with a final newline. Reuse the current writer's exclusive creation and partial-new-output-on-write-failure behavior. The user-selected output parent is trusted; report writing is not a secure-storage or hostile-directory guarantee. Success exits 0 and states that bytes were hashed, no media decoded, and no training started. Warn to keep real reports private and that duplicate candidates need review.

The public example selects three committed, explicitly synthetic plain-text assets. Two have identical bytes and one differs. It must not pretend to contain video or verified training examples. README documents command, caps, POSIX limitation, zero real-data/decoding/training claims, source non-modification, private reports, and remaining timestamp/label work.

## Acceptance and limitations

- Real temporary files demonstrate known SHA-256 results, zero-length and multi-chunk input, stable ordering, exact duplicate candidates, hard-link accounting, and no source-content changes.
- Table-driven request validation covers unknown keys/types, Boolean integers, ID/path duplicates, all forbidden path forms, malformed late entries, and exact 1000/1001 asset limits. Invalid requests/caps do not open the root.
- Real nested paths work; missing assets, directories, source symlinks at each path level, dangling symlinks, and FIFOs are rejected promptly. Explicit root symlink resolution is separately tested. The request FIFO test runs in a bounded subprocess.
- Exact per-file/total byte limits pass; over-limit inputs fail, including growth during reading. Deterministic fault injection covers same-size mutation, truncation, mid-read failure, platform rejection, bounded read requests, and descriptor cleanup. Real-file tests accompany injected faults.
- Real CLI tests exercise strict JSON/UTF-8 and exact request-size limits, configuration validation, privacy, fresh output, pre-read existing-output refusal, output failures, canonical report bytes, and all old commands unchanged.
- Tests and reviews establish this software boundary only. No real-media validity, timing alignment, reviewed labels, H20 performance, or game clears are demonstrated.

Python 3.11 OS interface reference: https://docs.python.org/3.11/library/os.html . Local checks on 2026-09-07 confirmed the required flag names and descriptor-relative open on Python 3.13.7/macOS; supported execution elsewhere still requires testing. This is not a claim of decoder readiness.
