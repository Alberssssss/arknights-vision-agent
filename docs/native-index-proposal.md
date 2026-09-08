# Native video index: proposed next boundary

Date: **2026-09-08**. Status: **proposal awaiting owner review (H08)**.
This is not an implemented API, an approved native invocation, a completed
media index, or permission to access real recordings. No implementation plan
or native-index code has been started from this proposal.

Later owner direction on 2026-09-08 prioritizes MAA/controller integration
before this video track. This remains the proposed next *video* boundary,
not the current first project task; H08 has not been approved.

## Owner-facing decision

建议首版采用下面的 A 方案：用独立进程读取一段明确选定的短 H.264
MP4/MOV 视频，生成保留原始时间戳、缺失信息和画面方向信息的离线索引。
先只用我们自己生成的测试视频。这个阶段不抽取训练样本、不推断玩家操作、
不训练模型，也不连接游戏。

H08 只需要确认这个阶段的范围和方案方向。确认后，先写出并评审完整接口规范
和有界验证计划，再用合成样例校准参数，并依据实测修正规范。确认方向不等于
批准访问私人素材、启动训练，或认定视频已经与操作日志正确对齐。

The brainstorming workflow requires review of the new design before product
implementation. Keep this explicit rather than treating the owner's general
autonomous-development direction as evidence that this particular new interface
has already been reviewed. Independent work from existing reviewed plans can
continue while H08 waits.

## Alternatives and recommendation

| Approach | Benefit | Trade-off / decision |
| --- | --- | --- |
| A. Narrow, separately supervised ffprobe process plus a pure Python normalizer | Builds on the measured local runtime while keeping native parsing outside the core Python process | Requires its own invocation, diagnostics, descriptor, limits and cleanup acceptance. Recommended first boundary, with conservative evidence flags. |
| B. In-process Python/native decoder binding | Could expose richer packet/decoder state directly | Adds a native Python dependency and another packaging/compatibility boundary; a decoder fault shares the Python process. Not selected for this first increment. |
| C. Accept previously generated probe JSON only | A small offline parser can be tested without native execution | Imported JSON cannot establish that this project inspected the selected bytes. Useful as A's pure parsing component, not a substitute for native execution provenance. |

The local build and 12-frame experiment are already complete. Do not rebuild or
repeat them merely to start this proposal. The remaining work is a new product
boundary, not another claim that the historical experiment is still pending.
See the [runtime receipt](media-runtime-calibration.md) and
[media preparation notes](media-preparation-notes.md).

## Proposed architecture and scope

Explicit file selection and expected identity → bounded native probe → strict,
detached metadata normalization → private index with scoped evidence and gaps.

1. **Input and runtime configuration.** Accept one explicit literal relative
   file reference under an owner-trusted root, its expected byte count/SHA-256,
   and an explicit absolute video-stream index. Reuse the lexical/no-follow
   boundaries from the [byte-inventory contract](superpowers/specs/2026-09-07-byte-inventory-design.md)
   without changing its accepted inputs. Never discover folders, select a
   preferred stream automatically, accept a URL/playlist, or download a runtime.
   Configure the trusted ffprobe executable and expected binary identity
   separately from imported media metadata or model output.
2. **Descriptor and observed identity.** Open a regular file with the required
   no-follow/nonblocking boundary, hash/check it before probing, keep the
   descriptor pinned, and recheck content and relevant file identity afterwards.
   Explicitly manage its seek position between passes. Refuse an observed
   mismatch. These checks do not provide an immutable snapshot or protection
   from a hostile filesystem or concurrent privileged mutation. A controlled
   executable path, its ancestors, dynamic libraries and stable local originals
   remain trust assumptions.
3. **Native execution.** Start only an explicitly configured local executable,
   with fixed argument construction, no shell, no hardware decoding, a bounded
   supervisor and a deliberately limited child environment. Inherited report or
   loader settings must not silently change execution or write files. The
   developer-only helper under `tools/media_runtime/` is reference evidence,
   not a product runner to import unchanged. A product runner needs its own
   contract and tests, including descriptor passing and cleanup failure.
4. **Narrow first supported media.** Short, self-contained H.264 MP4/MOV only;
   explicitly disable external-track and absolute-alias loading, force the
   intended demuxer, and restrict input protocols. The initial implementation
   must not broaden formats, fall back to a network input, or choose another
   stream after failure. Stream selection does not isolate the earlier native
   container/stream-information parsing phase.
5. **Private output.** Normalize only the bounded selected fields. Retain source
   identity, stream identity, runtime identity and an explicit index-format
   version. Use an exclusively created fresh output directory, no overwrite
   option, and concise stage-based errors without raw native diagnostics or
   submitted path/value text. Original files are not intentionally modified.
   Relative names and hashes can still be sensitive; real reports stay private.

Proposed initial ceilings are one file/256 MiB, 30 seconds per native probe,
8 MiB combined stdout/stderr, 10,000 retained frame records, and dimensions no
larger than 3840×2160 or 8,294,400 pixels. These are proposed engineering limits,
not measured capacity or a promise that every legitimate recording fits.
Output acceptance limits cannot retroactively constrain native decoding.
Probing options and per-allocation/pixel limits are not total-memory/CPU or
filesystem/network isolation. The final design must say exactly which bounds
are enforced while running and which are checked after receiving records;
it must not advertise an OS sandbox that does not exist.

## Timing and image geometry to retain

- Preserve the observed frame-output order with a separate ordinal; do not
  silently sort records into an apparently clean presentation sequence.
- Preserve signed integer PTS, frame-reported packet DTS, best-effort timestamp,
  duration, and the original rational stream time base separately. Missing is
  not zero, a requested seek time, a guessed FPS timestamp, or an inferred value
  copied from another field. Best-effort values remain labeled as estimates.
- A stream's declared start timestamp is not automatically the first returned
  frame timestamp. Keep nonzero and negative origins. Use integer/rational
  arithmetic; do not round into the v1 millisecond demonstration manifest.
- Report missing, repeated or decreasing presentation timestamps as explicit
  conditions. An index can describe missing evidence without becoming an
  eligible action-training example. The final contract must specify which
  malformed structures are hard failures versus valid-but-incomplete metadata.
- Preserve stream and frame display-matrix data separately, including the raw
  nine integer coefficients and their native representation. Do not reduce a
  matrix to a rounded rotation angle or treat an absent/singular matrix as a
  proven identity transform.
- Record stream dimensions, decoder coded dimensions, returned frame dimensions,
  sample aspect ratio and crop rectangles with an explicit cropping policy.
  Indexing does not yet transform or extract pixels, and it does not establish
  a screen-to-controller coordinate mapping.

No action-clock mapping, causal frame selection, label eligibility promotion,
permission verification, model execution or training belongs to this boundary.
Those later steps must use the actual returned frame identity and uncertainty,
not a seek request or a future result frame.

## Completion and error policy to make explicit

Reject a timeout, output excess, nonzero native status, cleanup failure, malformed
JSON, identity mismatch or unsupported shape. A proposed first adapter should
capture warnings/errors and refuse to silently accept them; the exact logging
and rejection policy still needs calibration with the selected build.

Native exit zero alone must never set a blanket `complete_decoding_verified` or
`timestamps_verified` assertion. A structurally valid, diagnostic-free index
records what this invocation returned, not authenticated clean EOF or coverage
of every intended source frame. Keep full-decode completeness, extraction,
action-clock alignment, label/permission checks, training and game success
explicitly unverified. Pure imported-JSON tests must not claim that native
decoding actually ran.

## Primary-source findings that constrain the design

These are **source-inspected findings**, not execution acceptance for a new
invocation. The separate source-check agent and coordinator inspected the pinned
FFmpeg 9.0.1 source. The coordinator checked the known archive SHA-256
`cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635`
and byte-matched eleven selected source/documentation files against it.
This is selected-file identity checking, not another full source safety audit.

| Finding | Pinned source location and implication |
| --- | --- |
| Available raw frame PTS/DTS/best-effort ticks and frame duration are emitted as integer JSON values; missing frame timestamps and unknown frame duration (zero) use optional `N/A`, omitted by default JSON output | `fftools/ffprobe.c:1524` and `fftools/textformat/avtextformat.c:525`. Preserve absence rather than fabricating zero. This is not the representation of formatted `_time` fields or stream duration fields. |
| In this inspected version, `show_optional_fields=never` returns before integer/string printing, not only before missing fields | `fftools/textformat/avtextformat.c:284` and `:468`. Do not assume that option is harmless; select and calibrate the actual writer policy. |
| Exact descriptor URL is `fd:` with the descriptor supplied separately by `-fd`; a regular descriptor supports seeking | `libavformat/file.c:494`. `fd:N` is not the proposed invocation. Passing the descriptor to the child and managing its offset remain untested adapter work. |
| Input opening, stream-information probing and decoder-context setup precede selection of streams | `fftools/ffprobe.c:2593` and `:2701`. Selection is an output/decode-selection setting, not a guarantee that other stream metadata was never parsed or its decoder opened. |
| MOV external-reference disabling can skip an alias and log embedded names; disabling absolute aliases alone does not disable relative aliases | `libavformat/mov.c:5170`, `:5380`, and the MOV options table. Restrict both settings and handle diagnostics privately; a disabled reference does not necessarily make the entire probe fail. |
| An inherited `FFREPORT` setting can initialize a report-file write | `fftools/cmdutils.c:569`. The child environment is part of the invocation contract. |
| Display matrices are formatted strings containing offset-prefixed rows; derived integer rotation can report zero for a singular matrix | `fftools/ffprobe.c:462` and `:536`; fixed-point layout in `libavutil/display.h:35`. Preserve matrix evidence rather than interpreting angle zero as identity. |
| Stream/packet and frame matrix labels differ | `libavcodec/packet.c:277` uses `Display Matrix`; `libavutil/side_data.c:50` uses `3x3 displaymatrix`. The parser needs separate location-aware handling. |
| Default cropping changes returned frame dimensions and zeros the crop fields | `libavcodec/avcodec.h:1789`. The source-supported `apply_cropping=0` policy needs native invocation acceptance; an autorotation choice alone is insufficient. |
| The packet-read loop does not separately retain the terminal read error, and inner frame-processing loop termination does not by itself propagate a negative result there | `fftools/ffprobe.c:1740` and `:1792`. Exit zero is not standalone complete/corruption-free decode evidence. |

The inspected upstream manuals also distinguish packet-count read intervals
from frame caps, and probing/per-allocation limits from wall-clock or total
memory bounds (`doc/ffprobe.texi`, `doc/formats.texi`,
`doc/fftools-common-opts.texi`). These distinctions must survive implementation.

Primary entry points for future rechecking are the
[pinned release archive](https://ffmpeg.org/releases/ffmpeg-9.0.1.tar.xz),
[ffprobe manual](https://ffmpeg.org/ffprobe.html),
[protocol manual](https://ffmpeg.org/ffmpeg-protocols.html),
[format manual](https://ffmpeg.org/ffmpeg-formats.html), and
[Python 3.11 subprocess reference](https://docs.python.org/3.11/library/subprocess.html).
Web-tool calls in this check yielded no usable source text; current online
agreement is not claimed. The evidence above is the pinned local primary source.
Use the archive's internal paths, not an old machine's ignored directories, in
a fresh clone. Do not treat future upstream `trunk` as this pinned version.

## Acceptance work after H08

1. Turn the approved boundary into the complete native-index specification and
   file-by-file plan. Fix strict request/report schemas, executable/file trust,
   field types and omissions, descriptor lifetime, child environment, live
   resource bounds, diagnostic rejection and private errors before coding.
2. Calibrate the exact descriptor/stream/output/cropping invocation with bounded
   self-authored synthetic clips. Check actual results for variable intervals,
   nonzero/negative origins, fractional milliseconds, B pictures, missing timing,
   identity/90-degree/singular matrix representations and crop geometry. Record
   rejected or unpreserved generator cases honestly; do not claim intended
   generation parameters survived muxing without inspecting the file.
3. Specify malformed/truncated media and multi-stream/external-reference cases,
   and distinguish their execution observations from a parser-security guarantee.
   A format or platform that cannot meet the selected contract remains unsupported.
4. Add failing pure-normalizer, descriptor/runner, cleanup, privacy and CLI
   acceptance tests before their respective product implementations. Include
   exact cap boundaries, stale identities, unknown/malformed fields and refusal
   of reused output. Run the current application/helper suites and independent
   specification/quality reviews without importing a model/controller stack.
5. Keep frame extraction and the projection into action-clock demonstration
   records a later, separate specification. Approved real samples and label
   review still require H02/H03; target H20/device work still has its own gates.

Until then, [HANDOFF.md](../HANDOFF.md) and [HUMAN_HELP.md](../HUMAN_HELP.md)
must identify this proposal as pending, not describe native indexing as built.
