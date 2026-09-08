# Project-local media runtime calibration

Date: 2026-09-07. This is environment preparation within the owner's autonomous
offline-development scope. It does not permit private-media access, training,
device contact, or a system-wide installation.

## Decision and alternatives

Prepare a CPU-only FFmpeg/ffprobe runtime under the repository's ignored `work/`
directory, then measure a tiny generated H.264 MP4. The core Python package keeps
its standard-library-only dependency boundary. This is a local environment
experiment, not yet a reusable media-indexing feature or a portable dependency
lock.

The research compared three approaches: Homebrew is absent and would require a
system-level installation; the inspected conda-forge dependency graph includes a
large optional inference stack; a local source build takes more setup work but
keeps the install prefix and external dependencies explicit. Select the source
build for this experiment. Do not alter global PATH, use sudo, install a package
manager, or copy this Mac binary to a future Linux/H20 host.

## Inputs and trust boundary

Proposed pins, rechecked before acquisition:

| Component | Input | Expected identity |
| --- | --- | --- |
| FFmpeg | `https://ffmpeg.org/releases/ffmpeg-9.0.1.tar.xz` | SHA-256 `cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635` |
| pkgconf | `https://distfiles.ariadne.space/pkgconf/pkgconf-3.0.7.tar.xz` | SHA-256 `c926ff491cbd9a331a589160811bd97ab1749b4d5198a519338f2cdfabe6940a` |
| x264 | `https://code.videolan.org/videolan/x264.git` | Git commit `b35605ace3ddf7c1a5d67a2eb553f034aef41d55` |

The archive digests were advertised by the corresponding Homebrew formula APIs,
not previously verified against local downloads. Acquisition uses HTTPS with
normal certificate verification, with `curl -q` as the first option to suppress
implicit curl configuration. Verify archive bytes before extraction and
verify the fetched x264 commit before building; never replace a pin silently.
Record actual downloaded byte counts/hashes and the metadata/source endpoints.

The accepted scope of this experiment is HTTPS plus separately obtained checksum
metadata, and Git's object verification for the exact upstream commit. GPG is
not installed here. FFmpeg's published release signing-key fingerprint is
`FCF986EA15E6E293A5644F10B4322F04D67658D8`, but no PGP verification is claimed.
A digest match is not a signature verification or a comprehensive source audit.
If the pinned source cannot be obtained, record that failure and investigate an
explicitly documented alternative instead of substituting an unrelated binary.

### Verified alternate acquisition for the same x264 commit

Both default and HTTP/1.1 Git fetch attempts reached their 60-second limit and
were stopped. The official fixed-commit archive and public commit API were
available instead:

- Archive: `https://code.videolan.org/videolan/x264/-/archive/b35605ace3ddf7c1a5d67a2eb553f034aef41d55/x264-b35605ace3ddf7c1a5d67a2eb553f034aef41d55.tar.bz2`
- Measured archive SHA-256: `6eeb82934e69fd51e043bd8c5b0d152839638d1ce7aa4eea65a3fedcf83ff224`
- Commit API: `https://code.videolan.org/api/v4/projects/videolan%2Fx264/repository/commits/b35605ace3ddf7c1a5d67a2eb553f034aef41d55`
- Measured commit-JSON SHA-256: `ceb66ee6feb70aedf995590144bb9c228f3ee5d89ae63ae01cd70b809b1ade0d`

The archive's PAX comment alone is not proof of its contents. Before running
source code, a fresh local Git index of every archive file (preserving executable
bits, without text conversions or Git attributes) produced tree
`0700538866963f968154ea768289bf100350e84e`. Reconstructing the Git commit bytes
from that tree plus the API's parent, author/committer timestamps and message
produced exactly the original pinned commit SHA-1
`b35605ace3ddf7c1a5d67a2eb553f034aef41d55`. Thus this alternate transfer retains
the fixed Git-object/content check, rather than accepting a filename assertion.
Retain the archive and API data for independent reproduction. Parent history was
not fetched; mark this one-commit checkout as shallow and do not fabricate a
full-history revision count in its generated library version.
The verified alternate checkout is detached at that exact commit before building;
the temporary local branch used during object reconstruction does not select a
mutable upstream revision.

## Bounded local work

Use new, clearly identified subdirectories of ignored `work/` for source,
installation, logs and synthetic artifacts. Never reuse or delete an existing
directory as a shortcut. Only trusted, selected release archives are extracted;
first inspect their member paths/types and reject absolute paths, parent
traversal, links or special nodes. Git acquisition is confined to its new checkout.

Archive downloads have HTTPS-only redirects, a 32 MiB byte cap, connection
timeouts and a 60-second overall limit per attempt. A timed-out partial archive
may be resumed from the same pinned URL in another bounded attempt; no partial
download is accepted before a complete hash match. A Git fetch has a 60-second
subprocess timeout. All native commands run in their own process group under a
local tested supervisor. Limits are 120 seconds per configure/install command,
300 seconds per pkgconf/x264 build, 900 seconds for the FFmpeg build, 15 seconds
per binary identity/feature probe, and 20 seconds per synthetic generation or
decoding command. The combined stdout/stderr cap is 8 MiB per command. On timeout,
output excess or supervisor failure, terminate the controlled group, allow the
leader at most two seconds to exit, kill any remaining group members, and reap
the leader. A UI/tool yield is not a process deadline. Use at most two compile
jobs and record separate stdout/stderr logs. Compilation is native code
execution, explicitly part of this environment experiment. It is not performed
by the product's `preflight` command.

Every independent cleanup attempt must run even if an earlier one fails,
including after selector initialization fails. A failed group signal still
allows a leader-only kill attempt and bounded reaping; it remains an error,
not proof that all descendants stopped. Always attempt selector and both pipe
closures. Preserve a single cleanup error, or all errors in an exception group
when several cleanup operations fail. This helper targets the current Python
3.13 experiment; it establishes no platform-wide process-containment guarantee.

Build static pkgconf, static/PIC x264 without CLI, OpenCL or assembly, then
FFmpeg/ffprobe with explicitly enabled libx264 and disabled automatic external
library discovery, network support, hardware acceleration, assembly, docs,
ffplay and shared FFmpeg libraries. Use `--disable-everything` and explicitly
request the initial H.264/MOV calibration and elementary frame-export components:
decoders h264/wrapped_avframe/rawvideo; encoders libx264/rawvideo/ppm; demuxers
mov/rawvideo; muxers mp4/mov/rawvideo/framehash/framemd5/image2/image2pipe; parser
h264; protocols file/pipe/fd; input lavfi; filters testsrc2/testsrc/color/settb/
setpts/format/scale/select/showinfo/buffer/buffersink; bitstream filters
h264_mp4toannexb/h264_metadata/extract_extradata. This is deliberately not a
general-format decoder build; future formats require separate enablement and
acceptance. These are the requested top-level components, not the final complete
feature list: the pinned source may select necessary dependencies. Inspect the
actual feature inventory and record those dependencies rather than describing
the handwritten flags as a verified complete closure. Check the configure help before
using flags. System libraries may still be dynamically linked: inspect actual
linkage, do not describe the output as a fully static executable.

The completed local experiment required one supported configure correction:
`--pkg-config-flags=--keep-system-cflags --keep-system-libs`, as a single argv
element. The first attempt failed to find `x264.h` because local pkgconf filtered
the prefix's include/library paths; retaining them fixed that compile probe.
No source pin or other requested component changed. The
[measured receipt](../../media-runtime-calibration.md) records the failure,
actual binary/component inventory, warnings and synthetic timing. The original
experiment is finished; product indexing/extraction still needs a separate
contract and tests.

No decoder is permitted to open private files during this experiment. An
isolated installation prefix is dependency isolation, not a native-parser
filesystem, memory or network security sandbox. Disabling FFmpeg network
features does not establish an operating-system sandbox.

The current Mac briefly returned EPERM during a second signal to an exiting
orphan process group, while immediate targeted process inspection found no
remaining member. The supervisor retries such a signal for at most 0.1 seconds
until it succeeds or ESRCH confirms absence; persistent permission errors remain
failures. Six real-process acceptance tests (including ten inherited-pipe
repetitions) passed after that correction. Independent review then reproduced
two cleanup gaps: failure of the first group signal and selector initialization
could bypass resource cleanup. Three additional real-child regressions failed
before the fix; they cover those paths plus both group signals failing. After
protecting initialization and making cleanup attempts independent, all nine
tests passed in 9.938 seconds. The tests preserve the errors and inspect the
runner's leader-reaping and pipe-closure results before their own fallback
cleanup; they do not reap on behalf of the assertions. Independent specification
re-review passed with all nine tests in 9.906 seconds. Subsequent independent
quality review passed with all nine tests in 9.916 seconds and three additional
real-child checks for selector/stdout close failures and their combination.
Those diagnostics verified later cleanup and retained errors; at that checkpoint,
making them permanent regressions was a nonblocking follow-up for the helper. The limited
local build may proceed. This is local evidence, not a claim
about all operating systems or arbitrary detached/privileged descendants.

**Follow-up (2026-09-08):** The three close-failure scenarios are now permanent
tests, bringing the developer-helper suite to twelve. The runner was unchanged.
The [follow-up plan](../plans/2026-09-08-media-helper-close-regressions.md) and
`STATUS.md` record the independent reviews and deliberately faulty-cleanup
checks. The nine-test counts above remain the original experiment's evidence.

## Acceptance evidence

1. Record source identities, actual successful build steps and failures, compiler
   identity, installed executable SHA-256 values, `-version`, `-buildconf`, and
   dynamic-library linkage for both ffmpeg and ffprobe.
2. Inspect the resulting build's required features: H.264 software decoding,
   libx264 encoding, MOV/MP4 demuxing/muxing, local file/pipe/fd protocols, test
   source and timestamp filters, and frame reporting. Missing features are an
   observed gap, not an automatic broadening to another runtime.
3. Generate at most 12 small (160x90) synthetic frames, with intended varying
   presentation intervals and B-frame encoding. Use no source recording, audio,
   URL or device. Retain the resulting file hash and raw sequential ffprobe
   stream/frame report.
4. Check actual stream time base, number of decoded frames, signed integer PTS,
   presentation order, at least two distinct positive intervals, and observed
   B pictures. Preserve DTS and best-effort timestamp fields independently.
   Passing generator options alone proves none of these properties.
5. Keep exact rational timestamps, never convert them to estimated FPS or
   silently round to the existing millisecond manifest. Later indexing and
   extraction need their own tested APIs, causal clock mapping and orientation
   checks. Calibration is not a training-ready dataset or game-performance test.

The checked-in deliverable is a truthful experiment record and reproducible
commands; native binaries, sources, logs and generated media remain ignored.
Independent review checks the record against the actual artifacts. The full
project goal remains active after this local experiment.

On 2026-09-07 the owner additionally requested a repository-contained handoff
for future Codex/IDE sessions. The already-reviewed pure-Python supervisor and
its nine tests are therefore preserved, without behavior changes, under
`tools/media_runtime/`; they remain developer-only and outside `src/`. The
original ignored copies have the same hashes at handoff. This is not promotion
to a product parsing API or permission to publish machine-specific wrappers,
third-party source downloads, binaries, private logs, or media. Fresh clones use
the portable guide and re-establish environment evidence rather than relying on
the original temporary paths.

Primary reference entry points: `https://ffmpeg.org/download.html`,
`https://ffmpeg.org/ffmpeg.html`, `https://ffmpeg.org/ffprobe.html`,
`https://formulae.brew.sh/api/formula/ffmpeg.json`,
`https://formulae.brew.sh/api/formula/pkgconf.json`, and
`https://formulae.brew.sh/api/formula/x264.json`.
