# Project-Local Media Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish and measure a repository-local CPU video runtime using only synthetic media, without starting training or accessing a device.

**Architecture:** The coordinator performs a bounded local dependency experiment in ignored `work/`, independently of the preflight implementation agent. A read-only reviewer checks the resulting receipt and artifacts. No production Python interfaces or model dependencies are changed by this experiment.

**Tech Stack:** Current macOS arm64 compiler/make, HTTPS source acquisition, pinned FFmpeg/pkgconf/x264, generated H.264 MP4, standard-library JSON/rational-number analysis.

**Fresh-clone note (2026-09-07):** The owner requested a repository-contained
handoff for other Codex clients. The reviewed experiment supervisor and its nine
tests are now preserved in `tools/media_runtime/`, outside the product package.
Old `work/` paths below identify the original experiment; use newly created,
validated local paths on another host. Follow `docs/continuation-guide.md` for
setup and equivalent review/TDD steps if the named desktop skills are unavailable.
Do not redo completed steps solely because this original plan has unchecked boxes.

**Measured checkpoint:** the local build and narrow synthetic timing experiment
have finished. The [receipt](../../media-runtime-calibration.md) records the
actual result, initial configure failure, supported correction and remaining
cases. Review/publication state is in `STATUS.md`; this original checklist is
not evidence that a process is still running.

---

## Task 1: Verify acquisition and local build

Files: ignored `work/media-sources-4FFZ3L/`, a new `work/media-runtime-XXXXXX/`
prefix, and a later checked-in `docs/media-runtime-calibration.md` receipt.

- [ ] Recheck metadata endpoints and the pins in the full design. Verify compiler
  availability, disk capacity and Git ignore coverage. These checks do not
  imply that compilation has passed.
- [ ] Download the two archives into the existing, confirmed-empty source
  directory. Run from the repository root:

  ```sh
  curl -q --fail --location --proto '=https' --proto-redir '=https' \
    --connect-timeout 10 --max-time 60 --max-filesize 33554432 \
    --output work/media-sources-4FFZ3L/ffmpeg-9.0.1.tar.xz \
    https://ffmpeg.org/releases/ffmpeg-9.0.1.tar.xz
  curl -q --fail --location --proto '=https' --proto-redir '=https' \
    --connect-timeout 10 --max-time 60 --max-filesize 33554432 \
    --output work/media-sources-4FFZ3L/pkgconf-3.0.7.tar.xz \
    https://distfiles.ariadne.space/pkgconf/pkgconf-3.0.7.tar.xz
  shasum -a 256 work/media-sources-4FFZ3L/ffmpeg-9.0.1.tar.xz \
    work/media-sources-4FFZ3L/pkgconf-3.0.7.tar.xz
  ```

  Abort that component before extraction if its hash differs from the exact
  design table. Inspect archive member paths/types
  before extracting into the same new source area.
- [ ] Use the design's explicit native process limits. Before running a build,
  test the ignored local supervisor with real child processes: successful split
  stdout/stderr, nonzero exit, wall-clock timeout, excessive output, and a child
  that ignores termination. Verify bounded output and leader reaping. The
  supervisor uses argument lists, a new process group, selector-based bounded
  reads, and TERM/two-second grace/KILL cleanup; it never executes a shell by
  default. Use it for configure, builds, install, version/features and calibration.
  This experiment helper is not promoted to a product media-parser sandbox.
- [ ] Create a fresh x264 Git checkout in the source directory, fetch only the
  exact official commit with a 60-second subprocess timeout, verify `FETCH_HEAD`,
  and check out that commit detached. Do not replace a failed fetch with a
  mutable branch or suppress TLS verification. The design records the observed
  Git transfer failures and the verified alternate archive/API acquisition for
  the same commit. That alternative must reconstruct the entire Git tree and
  commit hash, not merely match the PAX comment. Keep its checkout one-commit
  shallow; parent history and a full revision count remain unavailable.
- [ ] Read each downloaded configure help and use a new explicit absolute
  install prefix. Intended flags, subject to the actual source's supported
  options, are:

  ```sh
  ./configure --prefix="$MEDIA_PREFIX" --disable-shared
  ./configure --prefix="$MEDIA_PREFIX" --enable-static --enable-pic \
    --disable-cli --disable-opencl --disable-asm
  PKG_CONFIG_PATH="$MEDIA_PREFIX/lib/pkgconfig" ./configure \
    --prefix="$MEDIA_PREFIX" --pkg-config="$MEDIA_PREFIX/bin/pkgconf" \
    --pkg-config-flags="--keep-system-cflags --keep-system-libs" \
    --disable-autodetect --disable-network --disable-hwaccels --disable-asm \
    --disable-doc --disable-ffplay --disable-shared --enable-static \
    --enable-gpl --enable-libx264 --disable-everything \
    --enable-decoder=h264,wrapped_avframe,rawvideo \
    --enable-encoder=libx264,rawvideo,ppm --enable-demuxer=mov,rawvideo \
    --enable-muxer=mp4,mov,rawvideo,framehash,framemd5,image2,image2pipe \
    --enable-parser=h264 --enable-protocol=file,pipe,fd --enable-indev=lavfi \
    --enable-filter=testsrc2,testsrc,color,settb,setpts,format,scale,select,showinfo,buffer,buffersink \
    --enable-bsf=h264_mp4toannexb,h264_metadata,extract_extradata
  ```

  Run each in its own source directory, then `make -j2` and `make install`.
  `$MEDIA_PREFIX` is task-local and always the validated new repository path,
  never a system environment variable. Keep separate logs per component and
  stage. If a command fails, inspect its actual log and document the necessary
  supported change before retrying. Do not install unrelated dependencies.
  The `--pkg-config-flags` option above was the sole necessary correction after
  the original configure could not find `x264.h`: the local pkgconf otherwise
  filtered the prefix's include/library paths. Pass its value as one argument,
  not two shell words. The full failure and successful retry are in the receipt.
- [ ] Record executable hashes, version/build configuration, `otool -L` linkage,
  and the protocols/codecs/containers/filters actually advertised by this build.

## Task 2: Measure synthetic presentation timing

- [ ] Create a new private scratch directory under `work/` for calibration, and
  run the following with the measured executable and explicit fresh output:

  ```sh
  "$MEDIA_PREFIX/bin/ffmpeg" -nostdin -n -hide_banner -loglevel error \
    -f lavfi -i "testsrc2=size=160x90:rate=25:duration=1" -frames:v 12 -an \
    -vf "settb=1/1000,setpts=40*N+20*floor(N/3)" \
    -fps_mode passthrough -enc_time_base 1:1000 \
    -c:v libx264 -threads 1 -pix_fmt yuv420p \
    -x264-params "bframes=2:b-adapt=0:scenecut=0" \
    -video_track_timescale 1000 "$MEDIA_RUN/vfr-bframes.mp4"
  "$MEDIA_PREFIX/bin/ffprobe" -v error -select_streams v:0 \
    -show_streams -show_frames -show_entries \
    "stream=index,codec_name,time_base:frame=stream_index,pts,best_effort_timestamp,pkt_dts,duration,pict_type" \
    -of json "$MEDIA_RUN/vfr-bframes.mp4"
  ```

  Keep native output logs. A command exit of zero alone does not pass timing
  acceptance; do not suppress unexpected muxer/decoder behavior.
- [ ] Analyze the raw report with exact integer/Fraction arithmetic: exactly
  one selected H.264 stream, positive rational time base, exactly 12 decoded
  frames, integer presentation timestamps whose every adjacent difference is
  strictly positive, at least two distinct
  positive intervals and at least one B picture. Record the observed values and
  missing DTS fields, rather than filling them in. Hash the resulting video.
- [ ] Write the experiment receipt with exact observed identities, successful
  commands, measured acceptance and limits. Include any failed download/build
  attempt; do not claim PGP, fully static linkage, H20 portability, a sandbox,
  native indexing API, causal extraction or real-media readiness.
- [ ] Obtain independent read-only review of the receipt against local artifacts.
  Fix factual discrepancies with `apply_patch`, then re-review. Commit the
  design, plan and final receipt, plus the owner's later-requested reviewed
  supervisor/tests and portable handoff documentation; never downloaded
  third-party sources, binaries, media or raw local logs. Publish
  reviewed documentation with the next reviewed project milestone.

These are environment acceptance checks, not a replacement for test-first
development of the forthcoming media-indexing/extraction APIs. Keep actual
training deferred and the full user goal active.
