"""Inventory explicitly selected local file bytes without decoding them."""

from contextlib import contextmanager
import copy
import hashlib
import os
from pathlib import Path
import stat

from arknights_vision_agent.identifiers import is_valid_identifier
from arknights_vision_agent.media_paths import is_valid_media_path

MAX_ASSETS = 1000
READ_CHUNK_BYTES = 1048576
DEFAULT_MAX_FILE_BYTES = 1073741824
DEFAULT_MAX_TOTAL_BYTES = 4294967296


class InventoryError(ValueError):
    """Invalid inventory configuration or an unavailable selected file."""


def validate_inventory_request(request: dict) -> dict:
    """Validate declarations without file I/O and return a detached copy."""
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


def require_inventory_platform() -> None:
    """Refuse platforms without the required descriptor-relative boundary."""
    if (
        os.name != "posix"
        or os.open not in os.supports_dir_fd
        or any(
            not hasattr(os, flag)
            for flag in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")
        )
    ):
        raise InventoryError(
            "inventory requires POSIX descriptor-relative no-follow file access"
        )


@contextmanager
def _open_root(media_root):
    # This explicitly selected root (including its ancestors) is owner-trusted.
    try:
        resolved = Path(media_root).resolve(strict=True)
        descriptor = os.open(resolved, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise InventoryError("cannot open the configured media root") from error
    try:
        yield descriptor
    finally:
        try:
            os.close(descriptor)
        except OSError as error:
            raise InventoryError("cannot close the configured media root") from error


@contextmanager
def _open_asset(root_descriptor, path):
    current = os.dup(root_descriptor)
    try:
        parts = path.split("/")
        for index, part in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW
            flags |= os.O_NONBLOCK if index == len(parts) - 1 else os.O_DIRECTORY
            child = os.open(part, flags, dir_fd=current)
            previous, current = current, child
            os.close(previous)
        yield current
    finally:
        os.close(current)


def _stat_identity(value):
    return (
        value.st_dev, value.st_ino, value.st_mode, value.st_size,
        value.st_mtime_ns, value.st_ctime_ns,
    )


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


def build_inventory(
    request: dict,
    *,
    media_root: Path,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> dict:
    """Hash stable selected bytes; this is neither decoding nor a snapshot."""
    validated = validate_inventory_request(request)
    _validate_cap(max_file_bytes, "max_file_bytes")
    _validate_cap(max_total_bytes, "max_total_bytes")
    require_inventory_platform()
    assets, total_bytes = [], 0
    with _open_root(media_root) as root_descriptor:
        for index, asset in enumerate(validated["assets"], 1):
            stage = "open"
            try:
                with _open_asset(root_descriptor, asset["path"]) as descriptor:
                    stage = "hash"
                    size_bytes, sha256 = _hash_file(
                        descriptor, min(max_file_bytes, max_total_bytes - total_bytes)
                    )
            except InventoryError as error:
                raise InventoryError(f"asset {index}: {error}") from error
            except OSError as error:
                raise InventoryError(
                    f"asset {index}: cannot {stage} selected file"
                ) from error
            assets.append({**asset, "size_bytes": size_bytes, "sha256": sha256})
            total_bytes += size_bytes

    assets.sort(key=lambda asset: asset["asset_id"])
    groups = {}
    for asset in assets:
        key = (asset["size_bytes"], asset["sha256"])
        groups.setdefault(key, []).append(asset["asset_id"])
    duplicates = [
        {"size_bytes": size, "sha256": sha256, "asset_ids": identifiers}
        for (size, sha256), identifiers in groups.items()
        if len(identifiers) >= 2
    ]
    duplicates.sort(key=lambda group: (group["sha256"], group["size_bytes"]))
    return {
        "schema_version": 1,
        "scope": "local_byte_inventory",
        "hash_algorithm": "sha256-bytes-v1",
        "limits": {
            "max_assets": MAX_ASSETS,
            "max_file_bytes": max_file_bytes,
            "max_total_bytes": max_total_bytes,
            "read_chunk_bytes": READ_CHUNK_BYTES,
        },
        "assets": assets,
        "duplicate_candidates": duplicates,
        "summary": {
            "asset_count": len(assets),
            "total_bytes": total_bytes,
            "duplicate_group_count": len(duplicates),
        },
        "verification": {
            "file_bytes_hashed": True,
            "media_decoded": False,
            "timestamps_verified": False,
            "label_evidence_verified": False,
            "permission_verified": False,
            "training_started": False,
            "game_clear_verified": False,
        },
    }
