"""Command-line entry points for offline replay and preparation tools."""

import argparse
import json
import os
from pathlib import Path
import stat
import sys

from arknights_vision_agent.inventory import (
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_TOTAL_BYTES,
    InventoryError,
    build_inventory,
    require_inventory_platform,
)
from arknights_vision_agent.preparation import (
    PreparationValidationError,
    build_preparation_report,
)
from arknights_vision_agent.replay import ReplayValidationError, replay_trace
from arknights_vision_agent.strict_json import StrictJSONError, load_json_object

_MANIFEST_MAX_BYTES = 16 * 1024 * 1024
_TRACE_MAX_BYTES = 2 * 1024 * 1024


class _CLIError(ValueError):
    pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arknights_vision_agent",
        description="Offline validation and dry-run replay tools.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    replay_parser = commands.add_parser(
        "replay",
        help="validate a trace and write non-executing replay reports",
    )
    replay_parser.add_argument("--trace", required=True, type=Path)
    replay_parser.add_argument("--output", required=True, type=Path)
    prepare_parser = commands.add_parser(
        "prepare",
        help="report metadata eligibility and group splits",
    )
    prepare_parser.add_argument("--manifest", required=True, type=Path)
    prepare_parser.add_argument("--output", required=True, type=Path)
    prepare_parser.add_argument("--seed", type=int, default=0)
    prepare_parser.add_argument(
        "--weights",
        type=int,
        nargs=3,
        metavar=("TRAIN", "VALIDATION", "TEST"),
    )
    inventory_parser = commands.add_parser(
        "inventory",
        help="hash explicitly selected local files without decoding media",
    )
    inventory_parser.add_argument("--request", required=True, type=Path)
    inventory_parser.add_argument("--media-root", required=True, type=Path)
    inventory_parser.add_argument("--output", required=True, type=Path)
    inventory_parser.add_argument(
        "--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES
    )
    inventory_parser.add_argument(
        "--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES
    )
    return parser


def _load_object(path: Path, *, max_bytes: int, kind: str) -> dict:
    with path.open("rb") as input_file:
        payload = input_file.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise _CLIError(
            f"{kind} file exceeds the {max_bytes // (1024 * 1024)} MiB size limit"
        )
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _CLIError(f"{kind} file is not valid UTF-8") from error
    return load_json_object(text, max_bytes=max_bytes)


def _load_trace(path: Path) -> dict:
    return _load_object(path, max_bytes=_TRACE_MAX_BYTES, kind="trace")


def _load_inventory_request(path: Path) -> dict:
    require_inventory_platform()
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            input_file = os.fdopen(descriptor, "rb")
        except BaseException:
            os.close(descriptor)
            raise
        with input_file:
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


def _render_reports(result: dict) -> tuple[str, str]:
    events = "".join(
        json.dumps(event, allow_nan=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for event in result["events"]
    )
    summary = (
        json.dumps(
            result["summary"],
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    return events, summary


def _write_report_files(output: Path, files: dict[str, str]) -> None:
    if os.path.lexists(output):
        raise _CLIError(f"output path already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    for name, content in files.items():
        with (output / name).open("x", encoding="utf-8") as report_file:
            report_file.write(content)


def _write_reports(output: Path, events: str, summary: str) -> None:
    _write_report_files(
        output,
        {"events.jsonl": events, "summary.json": summary},
    )


def _replay_command(trace_path: Path, output: Path) -> int:
    trace = _load_trace(trace_path)
    result = replay_trace(trace)
    events, summary = _render_reports(result)
    _write_reports(output, events, summary)

    if result["summary"]["blocked_actions"]:
        print(
            f"error: replay blocked; diagnostic reports retained in {output}",
            file=sys.stderr,
        )
        return 2

    print(
        f"Dry-run reports written to {output}; no game or device was controlled."
    )
    return 0


def _prepare_command(
    manifest_path: Path,
    output: Path,
    seed: int,
    weights: list[int] | None,
) -> int:
    manifest = _load_object(
        manifest_path,
        max_bytes=_MANIFEST_MAX_BYTES,
        kind="manifest",
    )
    named_weights = (
        None
        if weights is None
        else dict(zip(("train", "validation", "test"), weights))
    )
    report = build_preparation_report(
        manifest,
        seed=seed,
        weights=named_weights,
    )
    rendered = (
        json.dumps(
            report,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    _write_report_files(output, {"preparation.json": rendered})
    summary = report["summary"]
    print(
        f"Metadata-only report written to {output}; "
        f"{summary['eligible_record_count']} of {summary['record_count']} "
        "records metadata-eligible; no media inspected and no training started."
    )
    if summary["eligible_empty_partitions"]:
        print(
            "Warning: no metadata-eligible records in partitions: "
            + ", ".join(summary["eligible_empty_partitions"])
        )
    return 0


def _inventory_command(arguments: argparse.Namespace) -> int:
    if os.path.lexists(arguments.output):
        raise _CLIError(f"output path already exists: {arguments.output}")
    request = _load_inventory_request(arguments.request)
    report = build_inventory(
        request,
        media_root=arguments.media_root,
        max_file_bytes=arguments.max_file_bytes,
        max_total_bytes=arguments.max_total_bytes,
    )
    rendered = json.dumps(
        report, allow_nan=False, sort_keys=True, separators=(",", ":")
    ) + "\n"
    _write_report_files(arguments.output, {"inventory.json": rendered})
    print(
        f"Inventory written to {arguments.output}; "
        f"{report['summary']['asset_count']} selected assets hashed; "
        "no media decoded and no training started."
    )
    print("Keep real reports private; duplicate candidates require review.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the offline command-line interface and return its exit status."""
    arguments = _build_parser().parse_args(argv)
    try:
        if arguments.command == "replay":
            return _replay_command(arguments.trace, arguments.output)
        if arguments.command == "prepare":
            return _prepare_command(
                arguments.manifest,
                arguments.output,
                arguments.seed,
                arguments.weights,
            )
        if arguments.command == "inventory":
            return _inventory_command(arguments)
    except StrictJSONError as error:
        kind = {
            "replay": "trace",
            "prepare": "manifest",
            "inventory": "inventory request",
        }[arguments.command]
        print(f"error: invalid {kind} JSON: {error}", file=sys.stderr)
    except InventoryError as error:
        print(f"error: invalid inventory: {error}", file=sys.stderr)
    except PreparationValidationError as error:
        print(
            f"error: invalid preparation data or configuration: {error}",
            file=sys.stderr,
        )
    except ReplayValidationError as error:
        print(f"error: invalid replay trace: {error}", file=sys.stderr)
    except (_CLIError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
    return 2
