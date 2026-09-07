"""Command-line entry points for offline replay reporting."""

import argparse
import json
import os
from pathlib import Path
import sys

from arknights_vision_agent.replay import ReplayValidationError, replay_trace
from arknights_vision_agent.strict_json import StrictJSONError, load_json_object

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
    return parser


def _load_trace(path: Path) -> dict:
    with path.open("rb") as trace_file:
        payload = trace_file.read(_TRACE_MAX_BYTES + 1)
    if len(payload) > _TRACE_MAX_BYTES:
        raise _CLIError("trace file exceeds the 2 MiB size limit")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _CLIError("trace file is not valid UTF-8") from error
    return load_json_object(text, max_bytes=_TRACE_MAX_BYTES)


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


def _write_reports(output: Path, events: str, summary: str) -> None:
    if os.path.lexists(output):
        raise _CLIError(f"output path already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    with (output / "events.jsonl").open("x", encoding="utf-8") as events_file:
        events_file.write(events)
    with (output / "summary.json").open("x", encoding="utf-8") as summary_file:
        summary_file.write(summary)


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


def main(argv: list[str] | None = None) -> int:
    """Run the offline command-line interface and return its exit status."""
    arguments = _build_parser().parse_args(argv)
    try:
        if arguments.command == "replay":
            return _replay_command(arguments.trace, arguments.output)
    except StrictJSONError as error:
        print(f"error: invalid trace JSON: {error}", file=sys.stderr)
    except ReplayValidationError as error:
        print(f"error: invalid replay trace: {error}", file=sys.stderr)
    except (_CLIError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
    return 2
