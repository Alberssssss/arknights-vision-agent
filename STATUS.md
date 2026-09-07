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

## Completed boundary: demonstration metadata

- [x] Strict v1 manifest validation implemented as a pure standard-library API.
- [x] Shared identifier rules preserved without changing the action boundary.
- [x] Causal media-clock declarations, review metadata, and whole-manifest recording/run relationships checked.
- [x] Synthetic and otherwise ineligible records still receive structural validation; none are silently promoted to real training data.
- [x] Independent specification and quality review completed; targeted regression tests strengthened after review.

This boundary validates declarations only. It does not open referenced images/videos, authenticate evidence or reviewers, establish media rights, split/export a dataset, or train a model.

## Completed boundary: metadata eligibility and group partitions

- [x] Pure preparation-report API implemented and independently reviewed.
- [x] Every exclusion reason retained; accepted recorded/permission-attested declarations distinguished from synthetic and unreviewed records.
- [x] Versioned whole-group assignments stay stable under row order, unrelated added groups, and eligibility changes.
- [x] Assigned and eligible records/groups counted separately, including empty evaluation partitions.
- [x] Canonical declaration digest and explicit unverified-evidence flags included without opening media.

The report is not a media export, rights verification, label audit, or training-readiness certificate.

## Completed boundary: offline preparation command

- [x] Bounded, strict manifest loading and optional seed/partition weights exposed through `prepare`.
- [x] A new output directory is required; existing files, directories, and symlinks are never overwritten.
- [x] Synthetic example reports three assigned groups and zero metadata-eligible records, with explicit empty-eligible-partition warnings.
- [x] Specification review and final integrated quality review passed without findings.
- [x] Fresh installed-wheel preparation and replay commands verified in isolated Python mode.

## Evidence so far

- Initial remote commit: `626efdade7ec6296214d6bc549662be61c2ca7f5`.
- Baseline contains only `README.md`; no pre-existing code tests exist.
- Local Python interpreter: 3.13.7. The planned package targets Python 3.11+.
- Action-boundary commit `57bfd9f`: 56 tests passed with `PYTHONPATH=src python3 -m unittest discover -s tests -q`; compilation and diff checks passed. Independent specification and code-quality re-reviews passed with no remaining findings.
- CLI/final milestone commit `15799d4`: all 116 tests passed with `PYTHONPATH=src python3 -m unittest discover -s tests -q`; compilation and diff checks passed. Separate specification, quality, and final integrated reviews passed with no blocking findings.
- A wheel built with `python3 -m pip wheel --no-deps --no-build-isolation --no-index --wheel-dir work/cli-package-check .`. It installed with no index/dependencies into a fresh ignored virtual environment. Isolated Python mode ran module help, the real CLI demo, and all 116 tests successfully. This verified Python 3.13 only; Python 3.11/3.12 execution remains unverified.
- Installed-wheel demo `work/wheel-demo-15799d4`: three finite events (two allowed dry-run actions and one stop), all `executed: false`, with `game_clear_verified: false`. No model or controller packages were installed for this check.
- Reviewed code through `15799d4` was pushed to `origin/codex/offline-foundation`. The development branch and local checkout are preserved for continuing preparation work.
- Future MaaFramework and pinned model/hardware contracts are documented; these are not implemented integrations.
- Replay commit `fdf4cea`: the coordinator ran all 88 tests, compilation, and diff checks successfully. Independent specification and quality reviews passed with no findings.
- Manifest implementation `60169c3` and test-strengthening commit `dd75ccb`: coordinator freshly ran all 157 tests, compilation, and diff checks successfully. The two strengthened tests isolate run-provenance enforcement and the 10,000-record upper bound; each caught its deliberately faulty version before real production was restored. The manifest/action implementation was unchanged during that test-only follow-up.
- A fresh wheel containing the manifest implementation built without an index, dependencies, or build isolation. It installed into `work/manifest-package-WWPZen/environment`; isolated Python ran the strengthened 157-test suite and the real replay command successfully. The demo kept `game_clear_verified: false`; no GPU/model/controller packages were installed. This is Python 3.13.7 evidence only, not Python 3.11/3.12 or H20 validation.
- Preparation-report implementation `5928f5c`: coordinator freshly ran all 176 tests, compilation, and diff checks successfully. Specification and quality reviews passed without defects. Tests include exact hash buckets, cross-process determinism, eligibility combinations, ordering/digest stability, and detached outputs. Independent review also checked 10,000 records/groups; this is not evidence of real-media quality or adequate dataset coverage.
- Preparation CLI `5f004a3`: all 190 tests, compilation, and diff checks passed. Specification review and a final integrated report/CLI quality review passed with no findings. Tests preserve replay behavior and cover exact input limits, failure privacy, no-overwrite behavior, and multiple eligible records counting as one eligible group.
- A fresh wheel built and installed offline without index/dependencies into `work/preparation-package-hqn3Hw/environment`. Isolated installed preparation and replay demos passed; the 190-test suite also passed in that environment (CLI subprocess tests explicitly select source code). The preparation demo assigned three groups across three partitions but had zero eligible records/groups and all verification flags false. A repeated-output attempt exited 2 without changing the report's SHA-256. Independent final review repeated installation and both real command checks. This is Python 3.13.7 evidence only; Python 3.11/3.12, real media, H20 readiness, and game performance remain unverified.
- Video-input research is recorded in `docs/media-preparation-notes.md`: byte inventory, native timestamp indexing, and verified frame extraction remain separate future boundaries. Neither `ffmpeg` nor `ffprobe` was found on the task's current PATH; no decoder was installed or run against media.

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
- [x] Implement strict demonstration-manifest validation with synthetic metadata tests.
- [x] Implement label-eligibility reporting and deterministic leakage-group partitions.
- [x] Add non-overwriting data-preparation commands and synthetic fixtures.
- [ ] Implement explicitly selected private-media byte inventory, followed separately by native timestamp indexing and verified frame extraction.
- [ ] Prepare gated environment, model, and controller configuration checks without launching training.
- [ ] Prepare offline policy/evaluation interfaces and reports; do not claim real performance from fixtures.

The exact v1 manifest, metadata-report, and preparation-command boundaries are implemented and reviewed. They do not yet constitute an implemented media pipeline. The next preparation work starts from `docs/media-preparation-notes.md`. See `HUMAN_HELP.md` for real recordings, target scope, and environment access. No actual training job should start automatically.
