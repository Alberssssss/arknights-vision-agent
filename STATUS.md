# Project status

Updated: 2026-09-07

## Overall goal

Develop a validated Arknights Integrated Strategies learning agent. The goal is not complete merely because an offline demo, test suite, or training script exists.

## Current milestone: offline foundation

- [x] Public repository initialized with an introductory README.
- [x] Dedicated local checkout created; unrelated `ideas` work is untouched.
- [x] Development branch `codex/offline-foundation` created.
- [x] Existing write authentication passed a Git dry-run; no account permissions were changed.
- [x] Human-help queue recorded.
- [ ] Strict observation/action boundary implemented and reviewed.
- [ ] Deterministic replay/dry-run loop implemented and reviewed.
- [ ] Command-line synthetic demo and machine-readable logs verified.
- [ ] README and configuration instructions match the implementation.
- [ ] Reviewed milestone published to the development branch.

## Evidence so far

- Initial remote commit: `626efdade7ec6296214d6bc549662be61c2ca7f5`.
- Baseline contains only `README.md`; no pre-existing code tests exist.
- Local Python interpreter: 3.13.7. The planned package targets Python 3.11+.
- Action-boundary commit `0e3fa08`: 54 tests passed with `PYTHONPATH=src python3 -m unittest discover -s tests -v`; compilation and diff checks passed. Independent specification re-review passed; final quality review is in progress.
- A wheel built with `python3 -m pip wheel --no-deps --no-build-isolation --no-index --wheel-dir work/package-check .`. The wheel installed with no index/dependencies into a fresh ignored virtual environment and passed the same 54 tests using isolated Python mode. This verified Python 3.13 only, not every supported Python version.
- Future data, MaaFramework, and pinned model/hardware contracts are documented; these are not implemented integrations.

## Not demonstrated

- No model has been trained or evaluated.
- No real game screen has been processed by this project.
- No device has been connected or controlled.
- No game clear or improvement over MAA has been established.
- No H20 memory or latency measurements have been taken.

## Next independent work

Implement the offline foundation plan. After its reviews pass, prepare separate plans for demonstration-data validation and a gated controller integration. See `HUMAN_HELP.md` for input-dependent work.
