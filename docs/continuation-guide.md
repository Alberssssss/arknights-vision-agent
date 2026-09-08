# Continuing from a fresh clone or another Codex client

This guide is for resuming the same project without the old desktop conversation.
The project files carry the engineering handoff; local sessions, machine setup,
permissions and authentication do not transfer.

## 1. Open the correct repository and read the handoff

Clone `Alberssssss/arknights-vision-agent`, open its root folder in the IDE, and
read [AGENTS.md](../AGENTS.md), [HANDOFF.md](../HANDOFF.md),
[STATUS.md](../STATUS.md), and [HUMAN_HELP.md](../HUMAN_HELP.md).

Codex's documented project-instruction mechanism uses `AGENTS.md`; instructions
are collected on startup by directory scope and may be affected by global or
override files and configured size limits. Keep this root entry concise and
explicitly read the linked handoff. Do not assume the old client's global
settings or plugins exist. Official reference, checked 2026-09-07:
[Custom instructions with AGENTS.md](https://developers.openai.com/codex/agent-configuration/agents-md).

A sufficient first request to the new coding assistant is:

> 请先完整阅读 AGENTS.md、HANDOFF.md、STATUS.md 和 HUMAN_HELP.md，核对当前分支、工作区和验证证据，再从第一个未完成的离线任务继续。实际训练仍暂停；不访问私人录像、GPU 或游戏设备。需要我参与的事项留在人工队列，继续其他独立工作。请用中文更新进度。

Check actual Git state before changing anything:

```sh
git status --short
git branch --show-current
git log -5 --oneline
git remote -v
```

When network access to the intended repository is available, inspect the actual
remote/default branch as well. The development line at the initial handoff is
`codex/offline-foundation`; on 2026-09-08 the reviewed handoff checkpoint
`bb15e44` was published to both that branch and the default `main` entry.
Do not assume either ref remains the newest forever.
On a clean new clone, fetch and inspect before selecting a development branch.
On an existing dirty checkout, preserve changes and do not switch/reset blindly.
No force push, history rewrite or repository-access change is part of resuming.

## 2. Re-establish the offline baseline

The application core targets Python 3.11+ and has no runtime dependencies beyond
the standard library. Actual recorded verification is CPython 3.13.7/macOS
arm64. That is not evidence that the full suite works unchanged on every OS:
some CLI tests use POSIX FIFOs and symbolic links. Verify another Linux/Python
environment explicitly; native Windows needs separate test/platform work.

These commands use POSIX-shell syntax and run from the repository root:

```sh
python3 --version
PYTHONPATH=src python3 -m unittest discover -s tests -q
python3 -m compileall -q src tests
git diff --check
```

The recorded application baseline has 307 tests. Treat the observed result and
current files as authoritative; future legitimate changes may change the count.
Investigate a new failure rather than skipping it to reproduce an old green
number. Do not install torch, Transformers, MAA or a model just for these tests.

The separately scoped local media-experiment helper can be checked with:

```sh
python3 -m unittest discover -s tools/media_runtime -p 'test_*.py' -v
```

Its nine tests create real, bounded local child processes, including POSIX fork
and process-group cases. They are not pure parsing tests and do not certify
cross-platform behavior, arbitrary process containment, a decoder or a GPU.
Read [its scope](../tools/media_runtime/README.md) before use.

Exercise application commands only with committed synthetic fixtures and new
output locations. A unique scratch directory avoids accidental reuse:

```sh
(
  set -eu
  mkdir -p work
  CONTINUATION_CHECK_DIR=$(mktemp -d work/continuation-check-XXXXXX)
  PYTHONPATH=src python3 -m arknights_vision_agent replay \
    --trace examples/synthetic_recruitment.json \
    --output "$CONTINUATION_CHECK_DIR/replay"
  PYTHONPATH=src python3 -m arknights_vision_agent prepare \
    --manifest examples/synthetic_demonstrations.json \
    --output "$CONTINUATION_CHECK_DIR/preparation"
  PYTHONPATH=src python3 -m arknights_vision_agent inventory \
    --request examples/synthetic_inventory.json --media-root examples \
    --output "$CONTINUATION_CHECK_DIR/inventory"
  PYTHONPATH=src python3 -m arknights_vision_agent preflight \
    --profile examples/setup_qwen38.json \
    --output "$CONTINUATION_CHECK_DIR/preflight"
)
```

The block creates the ignored `work/` parent if absent and stops on a failed
directory creation or command without changing the caller's shell options.
Expected semantic results:
replay has no executed action or verified clear; preparation has three assigned
groups and zero eligible records/groups; inventory describes three synthetic
text assets, not videos; preflight retains 12 unmeasured categories and five
false execution flags. Host facts may differ. Read reports rather than treating
exit 0 as real-model or game readiness. Reusing an output path must be refused.

Packaging is a separate optional check and needs a suitable local build tool.
Previous wheels were built/installed with no index or dependencies. They are not
in Git. If you repeat that check, use a fresh project-local environment, verify
the imported installed module path, and run real installed commands with Python
`-I`. The full suite's CLI subprocess tests explicitly select their source root;
running that suite in a virtual environment is not an installed-CLI substitute.

## 3. Rebuild machine-local media tools, not project history

The old ignored `work/media-sources-*`, `work/media-runtime-*`, build logs,
virtual environments and synthetic calibration outputs are absent from a clone.
Do not reuse their old names as though they identify files on the new machine.
Use fresh, explicitly validated directories and record new evidence privately.

What is preserved in Git:

- The [media-runtime design](superpowers/specs/2026-09-07-media-runtime-design.md)
  and [plan](superpowers/plans/2026-09-07-media-runtime.md): pinned source URLs and
  hashes, source-identity procedure, command limits, component scope, intended
  build/calibration commands, and limitations.
- The reviewed [process helper and tests](../tools/media_runtime/README.md),
  copied without behavior changes from the tested local experiment helper.
- Dated measured results in [STATUS.md](../STATUS.md) and the
  [local runtime receipt](media-runtime-calibration.md). A receipt is historical evidence, not a transferable
  executable or a claim that your new host is configured.

Before any native execution, follow the complete current experiment design,
verify the selected sources/executable and the helper on that host, and inspect
the actual build features. Do not copy a macOS binary to Linux/H20. The first
experiment is CPU-only and narrow H.264/MOV, not an all-format decoder or an
operating-system sandbox. A reproducible build result is not promised; retain
actual binary identity, linkage and logs for the new build.

Use the stored source commits and checksums, not a guessed latest release. An
intentional dependency change requires fresh primary-source verification and a
reviewed plan. Do not install system-wide tools, modify global PATH, or add
unrelated model/GPU dependencies to solve a local media issue automatically.

## 4. Portable development workflow

Historical plans mention `superpowers` skills and desktop-specific tools. Use
available applicable skills, but a missing plugin is not missing project source.
The essential workflow can be carried out with ordinary Git, a terminal, an
editor, tests, and a qualified independent reviewer:

1. Read the task's full contract, current implementation and verified status.
   Identify interfaces, failure behavior, limits and the exact files in scope.
2. For new behavior or a bug fix, write a minimal failing regression first and
   observe the expected failure. Implement the smallest conforming change,
   rerun that test and the full relevant suites, then review the exact diff.
3. Independently review specification compliance, then code quality. A separate
   agent or human may do this. If unavailable, do a labeled self-review, keep the
   independent-review gate pending, and continue another independent task; never
   describe self-review as independent approval or publish as reviewed.
4. Preserve unrelated work. Stage exact reviewed files and inspect staged
   content for secrets, recordings, weights, paths and unintended generated data.
   Use the owner's configured GitHub no-reply identity; do not invent a personal
   identity or export credential configuration into the repository.
5. Record commands actually run, interpreter/host scope, counts, exit codes,
   artifacts/hashes where useful, and unresolved limitations in `STATUS.md`.
6. Publish only within the owner's approved scope, without force. Confirm the
   actual remote commit/default entry rather than inferring success from a local
   commit or an unobserved push. Preserve the development branch and checkout.

Old implementation-plan checkboxes are historical task descriptions, not the
current backlog. `STATUS.md` records verified boundaries; `HANDOFF.md` identifies
the first unfinished work; the roadmap preserves the complete goal. If they
contradict current code or reports, investigate and correct the stale document.

## 5. What must remain private or require renewed setup

Do not add raw recordings/frames, event logs, datasets, weights, checkpoints,
credentials, account overlays, private reports, local machine configuration,
virtual environments, native downloads/binaries or raw chat transcripts to Git.
Ignore rules help avoid accidental commits; they are not secure storage.

Record approvals and the human queue at an appropriate non-sensitive level.
Access to a different host, device, dataset or account is not inherited from a
configuration example or a prior machine's successful check. H05 environment
access is not the separate CP7 training decision. The current training deferral
continues until the owner explicitly changes it.

Codex application goals/heartbeats, tool handles, spawned-agent state and model
settings are client-local. A clone does not resume them. Start a new task with
the repository handoff and establish any appropriate local coordination there;
do not recreate old sessions by copying IDs or presume a recorded PID is live.

## 6. Keep the next handoff current

Before pausing or handing off, leave:

- `HANDOFF.md`: first unfinished task, concrete next action and dependency gates.
- `STATUS.md`: verified code/experiment evidence, publication facts and limits.
- `HUMAN_HELP.md`: changed owner-dependent items, with no private payloads.
- The relevant spec/plan or decision notes: agreed contracts and why a necessary
  change was made, including reproducible failure and verification steps.

If work is genuinely running, record a non-sensitive description and verify its
live state before acting again on the same machine. Do not publish ephemeral
process IDs or tool handles as instructions for a new host. A missing artifact
or an unverified result stays missing/unverified, rather than being reconstructed
as a success claim from the narrative.
