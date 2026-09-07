# Local CPU video-runtime calibration receipt

Measured on 2026-09-07, on the original macOS arm64 development host. This is
historical environment evidence, not an installed dependency in a fresh clone.
The [design](superpowers/specs/2026-09-07-media-runtime-design.md) and
[plan](superpowers/plans/2026-09-07-media-runtime.md) retain the source pins,
trust boundary, bounded command arguments and reproduction steps.

## Result and scope

A project-local FFmpeg/ffprobe build generated and sequentially decoded a
12-frame, video-only H.264 MP4. Actual presentation intervals varied and seven
decoded pictures were B pictures. No private recording, device, model, GPU or
training job was involved. The product still has no native timestamp-indexing
or causal frame-extraction API.

All experiment commands have finished. Their old process/session identifiers
are not continuation instructions. Downloads, binaries, machine-specific
wrappers, raw logs and generated media remain ignored; a clone must rebuild and
recheck its own host. Start the next product task from [HANDOFF.md](../HANDOFF.md).

## Source and build identity

- FFmpeg 9.0.1 archive SHA-256:
  `cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635`.
- pkgconf 3.0.7 archive SHA-256:
  `c926ff491cbd9a331a589160811bd97ab1749b4d5198a519338f2cdfabe6940a`.
- x264 commit: `b35605ace3ddf7c1a5d67a2eb553f034aef41d55`, verified through the
  alternate archive/tree/commit reconstruction recorded in the design after
  two bounded Git transfers timed out. The one-commit shallow checkout remained
  detached at that commit with no tracked source diff. Its library version was
  `0.165.x`; no full-history revision count is claimed.
- Compiler: Apple clang 17.0.0 (`clang-1700.3.19.1`), target
  `arm64-apple-darwin25.3.0`; GNU Make 3.81. These are observations, not a
  cross-platform toolchain lock.

Configure/build/install used the reviewed developer supervisor, argument lists
without a shell, separate process groups and an 8 MiB combined output cap.
Configure/install limits were 120 seconds; pkgconf/x264 builds 300 seconds;
FFmpeg build 900 seconds; identity probes 15 seconds; calibration 20 seconds.
Builds used two jobs. No command in the retained build/calibration set hit a
time/output limit. A tool-interface yield was not treated as a deadline.

| Stage / retained log label | Exit | Elapsed seconds |
| --- | ---: | ---: |
| `010-pkgconf-configure` | 0 | 7.154 |
| `011-pkgconf-build` | 0 | 4.236 |
| `012-pkgconf-install` | 0 | 0.347 |
| `020-x264-configure` | 0 | 3.482 |
| `021-x264-build` | 0 | 5.559 |
| `022-x264-install` | 0 | 0.041 |
| `030-ffmpeg-configure-original` | **1** | 17.007 |
| `031-ffmpeg-configure-keep-paths` | 0 | 20.796 |
| `032-ffmpeg-build` | 0 | 26.688 |
| `033-ffmpeg-install` | 0 | 0.592 |

The first FFmpeg configure failed because pkgconf filtered the local prefix's
include/library paths as its default system paths. Its default output was
`-lx264 -lpthread -lm`, and the compiler could not find `x264.h`. Keeping those
paths restored the required `-I` and `-L` options. The only configure change was
one additional argument, written in a POSIX shell as:

```sh
--pkg-config-flags="--keep-system-cflags --keep-system-libs"
```

In an argument list, the whole string
`--pkg-config-flags=--keep-system-cflags --keep-system-libs` is one element.
The plan now includes this supported correction. Both complete configure logs
were retained. No global PATH change, unrelated dependency or upstream source
patch was used. This was the plan's bounded failure-investigation/retry path,
not a separately granted permission or a silent change of source pin.

Warnings remain visible: pkgconf's Autotools-deprecation/default-system-path
warnings, x264 unused-function/variable warnings, and FFmpeg's possible
uninitialized `bit_rate` in `libavcodec/aac_ac3_parser.c`. The last warning
occupies the retained 854-byte build stderr. This is not a warning-free build
or a general-format safety assessment. Separately, x264's help command returns
1 by its source code; that explicitly expected help exit is not a build failure.

## Installed binaries and advertised features

Both programs reported version 9.0.1 and Mach-O 64-bit arm64. Fresh final hashes
matched their earlier measured values:

| Program | SHA-256 |
| --- | --- |
| `ffmpeg` | `e656144155ad4e4a3dab2d5839e5b4e9b9febbd2eec81c4c5810e62e06983856` |
| `ffprobe` | `b70cabaf60fc136de3819d9e1fb7516fd5f69b52dd4c56b5b70747128c371b8c` |

Version/build-configuration reports and direct dynamic-link inspection were
retained for both. Each directly links libSystem and the CoreFoundation,
CoreVideo and CoreMedia OS frameworks. The executables are **not fully static**.
The advertised hardware-acceleration list is empty; framework linkage does not
establish hardware decoding. Build paths affect identity; another host is not
expected to reproduce these binary hashes automatically.

| Observed category | Advertised components |
| --- | --- |
| Input and output protocols, both programs | `fd`, `file`, `pipe` |
| Decoders, both programs | `h264`, `rawvideo`, `wrapped_avframe` |
| Encoders | `libx264`, `ppm`, `rawvideo` |
| Demuxers | `lavfi`, the MOV/MP4 family, `rawvideo` |
| Muxers | `framehash`, `framemd5`, `image2`, `image2pipe`, `mov`, `mp4`, `rawvideo` |
| Bitstream filters | `aac_adtstoasc`, `extract_extradata`, `h264_metadata`, `h264_mp4toannexb`, `vp9_superframe` |
| External library, configure report | `libx264` |
| Parsers, configure report | `ac3`, `h264` |

The filter inventory contains `aformat`, `anull`, `atrim`, `crop`, `format`,
`hflip`, `null`, `rotate`, `scale`, `select`, `setpts`, `settb`, `showinfo`,
`transpose`, `trim`, `vflip`, `color`, `testsrc`, `testsrc2`, `abuffer`, `buffer`,
`abuffersink` and `buffersink`. Thus requested top-level flags are not the final
dependency closure. An advertised component is not a tested format guarantee;
only the narrow synthetic case below was exercised.

## Measured synthetic timing

The plan's generation and sequential frame-probe arguments were used unchanged.
A supplementary all-stream probe checked shape and stream count. Generation,
frame probing, analysis and shape probing exited 0 in respectively 0.023,
0.010, 0.031 and 0.009 seconds, with empty stderr and no limit event.

Observed stream: index 0, H.264, 160x90, `yuv420p`, exactly 12 decoded frames.
The all-stream report contains one video stream and no audio. The native time
base is exactly `1/1000`; the table retains integer ticks, not float seconds.

| Frame index | PTS | Best-effort timestamp | Frame-reported pkt_dts | Duration | Picture |
| ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 0 | 0 | 0 | 40 | I |
| 1 | 40 | 40 | 40 | 40 | B |
| 2 | 80 | 80 | 80 | 40 | B |
| 3 | 140 | 140 | 140 | 40 | P |
| 4 | 180 | 180 | 180 | 40 | B |
| 5 | 220 | 220 | 220 | 40 | B |
| 6 | 280 | 280 | 280 | 60 | P |
| 7 | 320 | 320 | 320 | 40 | B |
| 8 | 360 | 360 | 360 | 40 | B |
| 9 | 420 | 420 | 420 | 60 | P |
| 10 | 460 | 460 | missing | 40 | B |
| 11 | 500 | 500 | missing | 60 | P |

Adjacent PTS differences are `[40,40,60,40,40,60,40,40,60,40,40]`: all strictly
positive, with exact intervals `1/25` and `3/50` seconds. Acceptance uses actual
PTS and rational arithmetic, not the generator's intentions, average FPS or
best-effort estimates. The distinct duration field is not substituted for a
presentation interval. Missing DTS remains missing. Observing B pictures is
not a packet-level reordering audit; packets were not separately indexed.

The container reports duration `0.540000` and size 9277 bytes. Relevant hashes:

| Artifact | SHA-256 |
| --- | --- |
| Synthetic `vfr-bframes.mp4` | `142e71afa7c7cee12f36d6afa2e046ce4761ad58ec6c37a11615e0d9b09ef4d2` |
| Raw frame report | `c990b7dd61cb912be02cee2935a187c87ce262e40ddcfb850a0598daa37df500` |
| Supplementary shape/stream report | `abd3de8d44b3a5e49b9329c3f509d1e4b792a4b0c86a48cffe31fdd1eb5e9b92` |

## Verification and private evidence map

On the original host only, `work/media-build-logs-Ku35qS/` holds per-command
argument/result records and separate stdout/stderr. Labels `040`–`060` cover
binary identity/features; `071-probe-frames.stdout.bin` and
`073-probe-shape.stdout.bin` are the raw JSON reports. The generated clip and
derived `timing-summary.json` are in `work/media-calibration-MHKrXe/`.
The prefix is `work/media-runtime-nX8Bch/`; the source area is
`work/media-sources-4FFZ3L/`. These are historical provenance, not files shipped
by Git or paths to assume on a new host.

The coordinator inspected raw version/configuration/linkage/features, build
failure and warning logs, and the complete frame/shape reports. A separate
integer/Fraction check verified the table, intervals, missing fields, one-stream
shape and file hash against the raw bytes, not just the derived acceptance flag.
All 58 retained command-result records matched their stdout/stderr byte counts
and SHA-256 values. The two nonzero exits were the expected x264 help and the
recorded first FFmpeg configure failure. Source archives, binaries and the
portable helper copies were also rehashed.

Independent read-only specification/factual and documentation-quality reviews
passed. The factual reviewer checked the 58 command records, 116 output files,
the raw timing table, artifact identities and the source/archive correspondence;
it did not rebuild or execute media programs. Publication and fresh-clone
evidence belong in [STATUS.md](../STATUS.md). Raw logs can contain
local paths and must not be published to reproduce this receipt. Follow the
portable plan with fresh directories and the reviewed helper; preserve new
actual results and limitations rather than copying an old success statement.

## Still unverified

Nonzero/negative origins, sub-millisecond time bases, display rotation/crops,
packet reordering, causal frame cutoff/extraction, file-identity races and a
product parser boundary need separate design and acceptance. No real gameplay
recording, label quality, model/H20 compatibility or game performance was tested.
There was no PGP verification, full source audit or OS-level native-parser
sandbox. The Python process supervisor does not impose native-memory/filesystem
quotas or contain arbitrary detached/privileged descendants.

The next independent task is the native-index specification and test-first
implementation, not another identical calibration or actual model training.
