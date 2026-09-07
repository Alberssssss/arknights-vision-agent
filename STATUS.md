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

## Completed boundary: explicitly selected byte inventory

- [x] Separate strict request and detached validation work before demonstration labels exist.
- [x] POSIX descriptor-relative reads reject descendant links and nonregular files, enforce byte caps, and detect observed source changes.
- [x] Deterministic SHA-256/byte-count report flags duplicate candidates without decoding media or promoting examples to training eligibility.
- [x] Nonblocking regular-file request loading and pre-read existing-output refusal verified through the `inventory` command.
- [x] Specification review passed; fresh installed inventory/preparation/replay commands verified.
- [x] Final independent quality/integration review passed without findings.

This is a byte reader, not a video decoder, immutable snapshot, media-rights verifier, or timing/label audit. Real data remains private and has not been accessed. The reviewed [pilot handoff](docs/recording-pilot.md) explains what the owner can supply later.

## Completed boundary: offline setup profile and local facts

- [x] Strict, detached v1 setup-profile validation implemented without model/controller defaults or execution switches.
- [x] Exact model/revision/architecture and controller/release declarations compared against a fixed repository research snapshot; unfamiliar contracts remain unreviewed.
- [x] Reports separate `declared`, `comparison`, `observed_local`, 12 ordered `unmeasured` identifiers, and five always-false `execution` flags.
- [x] Current-interpreter/OS features and fixed-name boolean PATH discovery collected without running discovered programs or importing optional runtimes.
- [x] Bounded regular-file input, pre-read existing-output refusal, independent null/unreviewed warnings, retained contradiction diagnostics, and real subprocess output-failure regression verified.
- [x] Specification and final quality/integration reviews passed; reviewed installed-package reports and a genuine unchanged-output check independently inspected.

This completes a current-Mac configuration-report boundary, not target-machine setup, a dependency compatibility lock, model/controller integration, native media validation, or training authorization. Exit 0 means a valid noncontradictory report was written, not that the system is ready. See the [exact specification](docs/superpowers/specs/2026-09-07-setup-preflight-design.md) and [implemented setup notes](docs/setup-preflight-notes.md).

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
- Earlier video-input research is recorded in `docs/media-preparation-notes.md`: byte inventory, native timestamp indexing, and verified frame extraction are separate boundaries. At that research checkpoint neither `ffmpeg` nor `ffprobe` was found on the task's PATH and no decoder had run. The later local CPU experiment below is separate evidence; it did not change global PATH or the preflight command.
- Byte inventory `8ef2c25`: coordinator freshly ran all 246 tests, compilation, and commit-range/working-tree diff checks successfully. Specification and final independent quality/integration reviews passed without findings. The shared path predicate preserves manifest acceptance; new tests exercise request types/limits, no-follow/FIFO boundaries, streamed caps, mutation and descriptor cleanup, duplicate candidates, failure privacy, and all previous commands. The final reviewer independently checked baseline/shared path acceptance parity across all Unicode codepoints plus type/length/segment cases, repeated the full suite, and verified all three installed commands and unchanged synthetic sources.
- A fresh wheel built and installed without index/dependencies into `work/inventory-package-aeiXmN/environment` (wheel SHA-256 `26e72c3bbac6848c3d6c8570f6bb0122dd9c8f253c7a881f5b66380c18205019`). Isolated installed inventory, preparation, and replay demos all passed; the 246-test suite also passed in that environment (CLI subprocess tests explicitly select source code). Inventory hashed three synthetic text assets/77 bytes and found one two-file duplicate candidate; only `file_bytes_hashed` was true. Repeated output exited 2 and preserved report SHA-256 `2ab0bd02529781b70a75ef18dc29746caab31fa313fa43afb7fe9cbfb2b20daa`. No real media, model/controller dependencies, or GPU was involved; execution evidence remains Python 3.13.7/macOS only.
- Before preflight implementation, the reviewed collection packet and setup-report design basis were recorded in `docs/recording-pilot.md` and `docs/setup-preflight-notes.md`. At that earlier checkpoint there was no preflight command. Selected package metadata was a separate current-Mac research observation, not an H20 measurement, dependency compatibility lock, native decoder integration, or a field collected by the later command.

### Setup-preflight closeout (2026-09-07)

- Feature `5b7e68ece88e698bead4bc0824b8ceeb1f15adcd` and real subprocess write-failure regression `4fbcafac3fdab72401bd497ac30dbfca38b3caab` constitute the reviewed implementation. Independent specification and final quality/integration reviews passed. The coordinator's source suite passed all 307 tests in 4.742s and the suite in the installed environment passed all 307 in 4.971s. Documentation closeout independently repeated all 307 tests in that existing environment under isolated Python mode: 5.094s, exit 0. CLI subprocess tests explicitly select the archived source path; this suite is not a claim that every CLI test exercised the installed package.
- Reused the exact-reviewed-HEAD package in `work/preflight-package-h8h8tk`, without another build or installation. Wheel `arknights_vision_agent-0.1.0-py3-none-any.whl` has SHA-256 `5b7142f43127dba343ec0a1a26df719db44946b3d9815a24669965453395d82d`. A fresh `python -I -B` check confirmed the preflight module came from the environment's installed `site-packages`; all 12 package Python files matched the reviewed Git commit, archived source, wheel, and installed copy byte for byte. Absolute interpreter/module paths stay in private local evidence, not this document.
- Separate coordinator checks ran the real installed replay, preparation, inventory, and preflight commands under `-I`. Closeout inspected their retained reports: replay contains three non-executed events and `game_clear_verified: false`; preparation assigns three groups but has zero eligible records/groups; inventory hashes three synthetic text assets/77 bytes, finds one two-file duplicate candidate, and sets only `file_bytes_hashed` true. These remain synthetic software checks, not real-data or game evidence.
- All five retained preflight reports were independently checked for exact top-level sections, canonical JSON bytes, the ordered 12 unmeasured identifiers, and five false execution flags; each exactly matched a fresh installed API report. The 27B and 8B examples match their own saved tuples. The unfamiliar revision stays unreviewed with a null controller; the known wrong architecture contradicts the snapshot with an independently unreviewed controller; both null integrations remain unconfigured. CLI regression coverage confirms per-integration warnings independently of a retained known-contradiction report and exit 2; valid noncontradictions exit 0 without establishing readiness.
- Observed local facts in those reports and the fresh collector check: CPython 3.13.7, `darwin`/`posix`, `arm64`; all five inventory feature booleans and their conjunction true; `ffmpeg`, `ffprobe`, `adb`, and `nvidia-smi` all absent from that process's PATH. Lookup retained booleans only and did not execute programs. No model download/loading, inference, native decoding, device contact, GPU measurement, or training occurred in these checks. Python 3.11/3.12 and the H20 environment remain unverified.
- A genuine repeat of the installed `preflight` command against existing `work/preflight-package-h8h8tk/preflight27-report` exited 2, printed no success output, and preserved the report bytes. SHA-256 before and after was `302f4877d01aa969fb7db82a43e4ef7e54b969d441c89416efce574273461c63`; the repeated command had a 10-second subprocess limit.
- At this closeout, the coordinator's bounded remote lookup (2.325s, exit 0) confirmed `origin/codex/offline-foundation` still points to `bc9946a600e352149c09c3ae9d1cb6a64a51e1fc`. The three later local commits `bec534e`, `5b7e68e`, and `4fbcafa` were not on that remote branch at that check. This documentation closeout does not claim publication; the coordinator still owns that step.

### Local media-runtime experiment (2026-09-07)

- Pinned pkgconf 3.0.7, x264 commit `b35605ace3ddf7c1a5d67a2eb553f034aef41d55`, and FFmpeg/ffprobe 9.0.1 built in ignored local directories on macOS arm64. The developer supervisor and nine real-process tests are retained under `tools/media_runtime/`, outside the product package. Source identity, supervised-command limits, necessary configuration correction, warnings, actual features and dynamic linkage are in the [runtime receipt](docs/media-runtime-calibration.md).
- The original FFmpeg configure exited 1 because pkgconf filtered local include/library paths. One supported argument retaining those paths fixed the probe; the subsequent configure/build/install exited 0. The binaries are not fully static, advertised hardware acceleration is empty, and upstream warnings remain recorded. No private-media or game/device access was involved.
- A video-only 160x90 H.264 MP4 decoded to 12 frames at exact time base `1/1000`. Actual PTS were `[0,40,80,140,180,220,280,320,360,420,460,500]`, with intervals of 40 or 60 ticks and seven B pictures. Missing frame-reported DTS at indices 10 and 11 was preserved. This does not establish packet-level reordering, orientation handling, causal extraction or a product index.
- The coordinator independently checked raw frame/shape data using integer/Fraction arithmetic and verified all 58 retained command-result/output byte counts and hashes. Fresh hashes of binaries, source archives and helper copies matched. Independent receipt specification/factual review and documentation-quality review passed without actionable findings; the factual reviewer also compared 11,424 ordinary source files against their three archives. This is identity correspondence, not a full source-code safety audit. All experiment commands finished; no build/calibration process is a pending continuation dependency.

### Portable continuation package (2026-09-07)

- Root `AGENTS.md` supplies the startup reading order and standing owner directions. `HANDOFF.md` records the mission, implemented boundaries, concrete next task and non-transferable local state. `docs/project-roadmap.md` preserves CP0–CP10, and `docs/continuation-guide.md` contains source checks, synthetic commands, local-runtime reconstruction, independent-review fallback and privacy rules. `HUMAN_HELP.md` remains the H01–H07 owner queue.
- Independent handoff specification and quality reviews passed. The subsequent completed-runtime snapshot and safe scratch-command correction also passed independent quality review. The helper copies retain their reviewed bytes and are explicitly outside `src/`; no binary, source download, real recording, machine wrapper, raw chat or credential is included.
- Fresh coordinator checks in the original checkout: application suite 307 tests in 4.466s; separate developer-helper suite 9 tests in 9.958s; compilation of `src`, `tests` and `tools/media_runtime` passed. All 92 Markdown local links resolved and the targeted private-path/key-pattern check found no actual private-path/key issue. These are scoped checks, not a comprehensive secret or security audit.
- The guide's scratch block now runs in a fail-fast subshell. A real-shell diagnostic with stub directory/CLI functions first reproduced both directory-failure paths continuing to four CLI calls; after correction they exited 19/17 with zero CLI calls, while success exited 0 with four calls. This diagnostic is separate from the 307/9 suites.
- A new-clone test and remote publication are pending at this checkpoint. Two bounded GitHub Git-ref lookups timed out; no new push has been attempted or claimed. Keep local commits and verify current remote/default-branch state before publication. A local commit alone does not make this handoff available to future GitHub clones.

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
- [x] Implement explicitly selected private-media byte inventory using synthetic acceptance data.
- [x] Implement and review the bounded offline setup-profile/local-facts report and verify its installed-package boundary.
- [x] Complete a bounded project-local CPU build and narrow synthetic presentation-timing calibration; retain its actual limitations separately from the product.
- [x] Independently review the runtime receipt and portable handoff package.
- [ ] Validate a fresh clone and publish the portable handoff to the default entry and development branch.
- [ ] Implement native timestamp indexing and verified causal frame extraction as separate boundaries.
- [ ] Continue separately gated target-environment, model-snapshot/dependency, and controller integration checks without launching training.
- [ ] Prepare offline policy/evaluation interfaces and reports; do not claim real performance from fixtures.

The v1 manifest, metadata report, preparation command, byte inventory, and setup-preflight report are implemented and reviewed but do not constitute a complete media pipeline or a model/controller runtime. The local CPU runtime experiment is now measured, not a product decoder interface. After handoff closeout, write and review the native timestamp-index specification/plan, then implement it test-first; causal frame extraction remains a later separate boundary. [HANDOFF.md](HANDOFF.md) gives the concrete continuation order and [the roadmap](docs/project-roadmap.md) retains the full goal. Target/model/controller readiness still needs its own evidence and appropriate access. No actual training job should start automatically. See `HUMAN_HELP.md` for real recordings, target scope, and environment access.
