"""Strict setup declarations and non-executing, current-process observations."""

import copy
import os
import re
import shutil
import sys

# Saved research declarations, not latest-release claims or compatibility locks.
_MODEL_SNAPSHOTS = {
    ("Qwen/Qwen3.8-27B", "1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0"):
        "Qwen3_5ForConditionalGeneration",
    ("Qwen/Qwen3-VL-8B-Instruct", "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b"):
        "Qwen3VLForConditionalGeneration",
}
_CONTROLLER_SNAPSHOTS = {("maa", "6.17.2"), ("maaframework", "5.12.3")}


class PreflightError(ValueError):
    """A setup declaration or limited local observation could not be accepted."""


def _fields(value, keys, where):
    if type(value) is not dict or set(value) != keys:
        raise PreflightError(f"{where} fields do not match the schema")


def _string(value, pattern, where):
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        raise PreflightError(f"{where} is invalid")


def validate_setup_profile(profile: dict) -> dict:
    """Validate the full declaration without observing the host, then detach it."""
    _fields(profile, {"schema_version", "model", "controller"}, "setup profile")
    if type(profile["schema_version"]) is not int or profile["schema_version"] != 1:
        raise PreflightError("setup profile schema_version must be integer 1")
    model = profile["model"]
    if model is not None:
        _fields(model, {"model_id", "revision", "architecture"}, "model")
        _string(
            model["model_id"],
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}/[A-Za-z0-9][A-Za-z0-9._-]{0,127}",
            "model model_id",
        )
        _string(model["revision"], r"[0-9a-f]{40}", "model revision")
        _string(model["architecture"], r"[A-Za-z][A-Za-z0-9_]{0,127}",
                "model architecture")
    controller = profile["controller"]
    if controller is not None:
        _fields(controller, {"backend", "version"}, "controller")
        _string(controller["backend"], r"maa|maaframework", "controller backend")
        _string(controller["version"], r"[0-9]{1,5}\.[0-9]{1,5}\.[0-9]{1,5}",
                "controller version")
    return copy.deepcopy(profile)


def collect_local_facts() -> dict:
    """Observe fixed local capabilities; never run a discovered executable."""
    features = {
        "posix": os.name == "posix",
        "open_dir_fd": os.open in os.supports_dir_fd,
        "o_directory": hasattr(os, "O_DIRECTORY"),
        "o_nofollow": hasattr(os, "O_NOFOLLOW"),
        "o_nonblock": hasattr(os, "O_NONBLOCK"),
    }
    features["required_features_present"] = all(features.values())
    try:
        machine = os.uname().machine if hasattr(os, "uname") else None
        executables = {
            name: shutil.which(name) is not None
            for name in ("ffmpeg", "ffprobe", "adb", "nvidia-smi")
        }
    except OSError as error:
        raise PreflightError("cannot collect local capability facts") from error
    return {
        "python": {
            "implementation": sys.implementation.name,
            "version": (
                f"{sys.version_info.major}.{sys.version_info.minor}."
                f"{sys.version_info.micro}"
            ),
        },
        "platform": sys.platform,
        "os_name": os.name,
        "machine": machine,
        "inventory_features": features,
        "executables_on_path": executables,
    }


def _compare_model(model):
    if model is None:
        return {"status": "not_configured", "expected_architecture": None}
    expected = _MODEL_SNAPSHOTS.get((model["model_id"], model["revision"]))
    if expected is None:
        return {"status": "unreviewed_contract", "expected_architecture": None}
    status = (
        "matches_research_snapshot" if model["architecture"] == expected
        else "contradicts_research_snapshot"
    )
    return {"status": status, "expected_architecture": expected}


def _compare_controller(controller):
    if controller is None:
        return {"status": "not_configured"}
    known = (controller["backend"], controller["version"]) in _CONTROLLER_SNAPSHOTS
    return {"status": "matches_research_snapshot" if known else "unreviewed_contract"}


def build_preflight_report(profile: dict) -> dict:
    """Validate declarations before gathering limited local facts."""
    declared = validate_setup_profile(profile)
    observed = collect_local_facts()
    return {
        "schema_version": 1,
        "scope": "offline_setup_preflight",
        "research_snapshot_id": "repository-research-2026-09-07-v1",
        "declared": declared,
        "comparison": {
            "model": _compare_model(declared["model"]),
            "controller": _compare_controller(declared["controller"]),
        },
        "observed_local": observed,
        "unmeasured": [
            "gpu_identity", "gpu_memory", "model_snapshot", "model_processor",
            "dependency_compatibility", "model_inference", "media_decoding",
            "media_timestamps", "label_quality", "controller_connection",
            "controller_actions", "game_performance",
        ],
        "execution": {
            "training_started": False,
            "inference_started": False,
            "device_contacted": False,
            "model_downloaded": False,
            "native_tools_executed": False,
        },
    }
