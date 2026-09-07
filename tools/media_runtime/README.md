# Developer-only media experiment supervisor

`process_runner.py` and `test_process_runner.py` preserve the reviewed helper
used for the original project-local CPU media experiment. They are outside the
application's `src/` package and are not imported by its commands. Their initial
tracked copies have the same content as the reviewed local helper/tests; see
[the design](../../docs/superpowers/specs/2026-09-07-media-runtime-design.md) for
the scope and dated evidence.

Run the separate suite from the repository root:

```sh
python3 -m unittest discover -s tools/media_runtime -p 'test_*.py' -v
```

There are nine tests, including real local child processes, a termination-resistant
leader, ten inherited-pipe repetitions, and injected initialization/signalling
failures. Test fallbacks clean up their own children after assertions. Actual
verification is CPython 3.13.7/macOS arm64, not native Windows or Linux/H20.
Three additional close-failure scenarios were independently exercised during
review but are not permanent tests in this nine-test suite; retaining them as
regressions is an explicit nonblocking follow-up recorded in the design.

For explicitly approved developer-controlled commands, `run(argv, timeout=...,
output_limit=..., cwd=..., env=...)` uses argument lists without a shell by
default, a separate process group, bounded collected stdout/stderr and elapsed
time, and independent cleanup attempts. It returns real status/output for normal
and command-limit outcomes; supervision/cleanup exceptions remain errors. Group
signal failure is not converted to successful group cleanup by a leader-only
fallback. Do not catch such an error and continue a build as though it succeeded.

This is **not** a production video-indexing API, validation of arbitrary
untrusted command arguments, a native parser sandbox, a memory/CPU/filesystem
quota, or a containment guarantee for detached/privileged descendants. Do not
expose it directly to model-generated text, device commands or arbitrary uploads.
It does not establish source trust or prevent native-code vulnerabilities.

Build sources, binaries, environment variables, private logs and media remain
local/ignored. Read the complete [runtime plan](../../docs/superpowers/plans/2026-09-07-media-runtime.md)
and [fresh-clone guide](../../docs/continuation-guide.md) before rebuilding. A
future product media runner/indexer needs its own design and tests; do not import
an old `work/` module or silently promote this experimental contract.
