# Project status

Updated: 2026-09-07

## Overall goal

Develop a validated Arknights Integrated Strategies learning agent. The goal is not complete merely because an offline demo, test suite, or training script exists.

Current owner direction (2026-09-07): leave actual training for later. Continue setup, pre-training preparation, and a practical training-data collection pipeline. No model-weight updates are authorized by this phase.

## Completed milestone: offline foundation

- [x] Public repository initialized with an introductory README.
- [x] Dedicated local checkout created; unrelated `ideas` work is untouched.
- [x] Development branch `codex/offline-foundation` created.
- [x] Existing write authentication passed a Git dry-run; no account permissions were changed.
- [x] Human-help queue recorded.
- [x] Strict observation/action boundary implemented and reviewed.
- [x] Deterministic replay/dry-run loop implemented and reviewed.
- [x] Command-line synthetic demo and machine-readable logs verified.
- [x] README and configuration instructions match the implementation.
- [x] Reviewed milestone published to the development branch.

## Evidence so far

- Initial remote commit: `626efdade7ec6296214d6bc549662be61c2ca7f5`.
- Baseline contains only `README.md`; no pre-existing code tests exist.
- Local Python interpreter: 3.13.7. The planned package targets Python 3.11+.
- Action-boundary commit `57bfd9f`: 56 tests passed with `PYTHONPATH=src python3 -m unittest discover -s tests -q`; compilation and diff checks passed. Independent specification and code-quality re-reviews passed with no remaining findings.
- CLI/final milestone commit `15799d4`: all 116 tests passed with `PYTHONPATH=src python3 -m unittest discover -s tests -q`; compilation and diff checks passed. Separate specification, quality, and final integrated reviews passed with no blocking findings.
- A wheel built with `python3 -m pip wheel --no-deps --no-build-isolation --no-index --wheel-dir work/cli-package-check .`. It installed with no index/dependencies into a fresh ignored virtual environment. Isolated Python mode ran module help, the real CLI demo, and all 116 tests successfully. This verified Python 3.13 only; Python 3.11/3.12 execution remains unverified.
- Installed-wheel demo `work/wheel-demo-15799d4`: three finite events (two allowed dry-run actions and one stop), all `executed: false`, with `game_clear_verified: false`. No model or controller packages were installed for this check.
- Reviewed code through `15799d4` was pushed to `origin/codex/offline-foundation`. The development branch and local checkout are preserved for continuing preparation work.
- Future data, MaaFramework, and pinned model/hardware contracts are documented; these are not implemented integrations.
- Replay commit `fdf4cea`: the coordinator ran all 88 tests, compilation, and diff checks successfully. Independent specification and quality reviews passed with no findings.

## Not demonstrated

- No model has been trained or evaluated.
- No real game screen has been processed by this project.
- No device has been connected or controlled.
- No game clear or improvement over MAA has been established.
- No H20 memory or latency measurements have been taken.

## Next independent work

Current focus: setup and training-data preparation, with actual training deferred.

- [x] Define a practical collection pilot and verify relevant MAA/MaaFramework recording limitations.
- [x] Review the manifest design for causal clocks, label provenance, safe references, and whole-group splits.
- [ ] Implement strict demonstration-manifest validation with synthetic metadata tests.
- [ ] Implement label-eligibility reporting and deterministic leakage-group partitions.
- [ ] Add non-overwriting data-preparation commands and synthetic fixtures.
- [ ] Prepare gated environment, model, and controller configuration checks without launching training.
- [ ] Prepare offline policy/evaluation interfaces and reports; do not claim real performance from fixtures.

The collection and manifest documents describe planned behavior, not an implemented media pipeline. See `HUMAN_HELP.md` for real recordings, target scope, and environment access. No actual training job should start automatically.
