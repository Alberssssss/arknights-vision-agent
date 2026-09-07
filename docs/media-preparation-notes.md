# Video input preparation: research and next boundaries

Checked against primary documentation on 2026-09-07. This is preparation research, not an implemented media reader or verified extraction recipe. Neither `ffmpeg` nor `ffprobe` was found on this task's current PATH; no decoder was installed or run, and no private recordings were opened.

## Keep three operations separate

1. **Byte inventory:** explicitly selected private assets, bounded reads, byte counts, integrity hashes, and duplicate-content candidates. A matching hash identifies matching bytes; it does not establish valid video, alignment, permission, or correct action labels.
2. **Native probe/index:** inspect an approved local asset with an explicitly supplied, trusted decoder build; retain actual stream/frame metadata and timing provenance. This executes a native media parser and needs its own limits and tests.
3. **Verified extraction:** select frames using their actual presentation timestamps and an explicit action-clock mapping, retain pixel transforms, then define a reviewed projection into demonstration records. Neither the requested seek position nor the requested window endpoint identifies the actual returned frame.

This staging is a project decision. It lets inventory and indexing advance without pretending that video-only data already contains verified action examples. None of these operations starts training.

## Timing must survive import

FFmpeg distinguishes a frame's presentation timestamp from its decode timestamp. `best_effort_timestamp` is a heuristic estimate in stream time-base units. Preserve signed integer timestamps, rational time bases, stream/frame identity, and whether timing is missing or estimated; do not replace them with average frame rate or floating-point display values.

Source: [AVFrame fields](https://ffmpeg.org/doxygen/trunk/structAVFrame.html).

ffprobe documents that interval seeking is not exact. A short pilot should therefore be indexed by sequential decoding; a later seek optimization must still inspect actual returned timestamps. FFmpeg also warns that `copyts` alone does not guarantee unchanged output timestamps. Its passthrough frame-rate mode and explicit orientation policy need calibration rather than assumption.

Sources: [ffprobe interval/stream options](https://ffmpeg.org/ffprobe.html#Main-options), [FFmpeg timestamp and frame-rate options](https://ffmpeg.org/ffmpeg.html).

The current manifest uses nonnegative integer milliseconds and binds the media-window end to the latest observation. Native video timestamps may be fractional milliseconds or use another origin. Do not silently round them into v1, substitute a seek target for a captured frame, or erase discontinuities. A separate native index should precede a specified conversion, uncertainty allowance, and causal cutoff policy. Edited/nonlinear recordings need more than the v1 constant clock offset.

## Local parsing is not inherently isolated

Protocol allowlists restrict protocols, not individual paths. The MOV demuxer has external-track and absolute-path loading options, both disabled by default. A future POSIX adapter can investigate a pre-opened file descriptor with the `fd` protocol and a forced demuxer, but must feature-check the supplied build. These controls are not protection against native decoder vulnerabilities or a substitute for filesystem/network isolation.

Sources: [protocol controls and fd input](https://ffmpeg.org/ffmpeg-protocols.html), [MOV demuxer options](https://ffmpeg.org/ffmpeg-formats.html#mov_002fmp4_002f3gp).

Use argument lists without a shell and bound elapsed time, stdout/stderr bytes, frame count, dimensions, and selected assets. Python's `Popen.communicate` buffers output; its timeout alone does not terminate the child. A bounded runner needs explicit termination/reaping and must not advertise a timeout/output cap as a native-memory sandbox.

Source: [Python 3.11 subprocess behavior](https://docs.python.org/3.11/library/subprocess.html).

Keep display matrices, coded dimensions, crop/scale information, and pixel-space transforms. FFmpeg enables autorotation by default; extraction must explicitly preserve coded orientation or apply and record the display transform. Otherwise an action label's coordinates could be paired with differently oriented pixels.

Source: [FFmpeg autorotation option](https://ffmpeg.org/ffmpeg.html).

## Bounded first pilot to specify

Proposed initial scope: an owner-selected short, self-contained H.264 MP4/MOV recording with an explicit video stream, private output, no URLs/playlists/discovery, and no automatic broadening to unsupported media. This is not yet an accepted-format guarantee.

Synthetic calibration should cover visibly distinct frames with variable intervals, cutoffs on/between frame timestamps, nonzero/negative origins, B-frame reordering, and identical coded pixels with identity/90-degree display transforms. Inspect the resulting files: intended generator timestamps are not evidence that a muxer preserved them.

Before implementation, fix the trusted executable/build requirements, supported timestamp/orientation cases, input/output/process limits, clock-origin and uncertainty rules, and the verified-frame-to-manifest representation. Real samples remain H02/H03; no GPU access is needed merely to design and test these offline boundaries.
