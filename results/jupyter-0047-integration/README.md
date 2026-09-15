# 0047 integration, first implementation: transport and message layer

Measured 2026-09-15 on nano. Record 0048 is accepted; record 0047 has adopted its
transport. This evidence covers extraction into `rnx/jupyter`, not a functioning
notebook kernel. No kernelspec has been installed by this run and no notebook
cells have run through this package yet.

## Reproduce

From rnx-bench, using the already pinned environment in
`probes/jupyter-transport/requirements.txt`:

```sh
bash probes/jupyter-integration/transport.sh
probes/jupyter-transport/.venv/bin/python -m playwright install chromium
probes/jupyter-transport/.venv/bin/python probes/jupyter-integration/browser.py
```

The first command builds the feature-gated acceptance example from **rnx's kernel
package**, not the old prototype. It runs 18 tests with default features and with
`transport-probe`, runs each of 0048's wire fixtures twice, checks formatting and
checks the Windows target. The same fixtures accept explicit `RNX_ZMTP_BINARY`
and `RNX_ZMTP_RESULTS` overrides; their defaults and old evidence are unchanged.
The example uses the new kernel message codec, so signed echo covers the
extraction plus authentication/serialization. It has no worker connection.

The root suites were additionally run, sequentially, with `TERM=xterm-256color`:
`cargo test --locked`, then `cargo test --locked --features test-support`.
Their complete logs and totals are preserved here, along with root formatting
and notices checks. No test was skipped for lack of Python.

## Results and scope

- 18 kernel-component tests pass with each feature selection. Eleven are the
  accepted transport tests. Seven added tests exercise authenticated envelopes,
  all four signed dictionaries, byte-exact parent headers, malformed/unsupported
  messages, bounded JSON expansion, typed connection files, regular-file/size
  refusal and a blocked application callback cancelled by transport shutdown.
- Both real-client wire fixtures pass twice (`exit-status.json`). In the final
  confirmation, all 1,001 paced publications reached the unchanged reading
  subscriber; the stalled subscriber disconnected. Control response during
  publication was at most 0.763 ms in that run. This is an offered-load
  observation, not a losslessness or throughput guarantee.
- The 40-connection/40 MiB unfinished-payload cycles recover. Near-maximum
  declared lengths, heartbeat floods, assembly deadlines, stale reply identity,
  pending writes and shutdown continue to pass. Full raw traces are retained.
- Root suites: 344 default, 385 test-support; zero failures. Root source,
  manifest, lockfile and notices have no diff from `7f667d2`. Root metadata has
  one workspace member and no kernel package. `root-independence.json` records
  those checks and hashes. No startup speedup or matched startup rerun is claimed.
- Windows **type checking only** passes. Neither transport execution nor job
  containment has run on Windows.
- Playwright 1.62.0 launches Chromium 151.0.7922.34, checks a DOM node and captures
  a page. `browser-preflight.png` is a browser prerequisite check, deliberately
  **not JupyterLab screen evidence**.

`clean-build.json` measures an offline release build in an empty target directory.
Its size/time describe the instrumented acceptance example, not kernel-ready or
first-cell cost. `linked-libraries.txt` has no native ZMQ library. `versions.json`,
`sha256.json`, the source lockfile and the raw logs identify what was measured.

## What changed at extraction

The transport is an owned library component in the independent kernel package.
The callback borrows multipart data while receive credits remain attached. It
cannot transfer the transport message into an unbounded inbound queue. Any
future retained execution representation needs separate application admission
before copying. The blocked-callback test observes held byte/connection credits,
then verifies their release on shutdown. A scope guard also retires the generation
on application unwind or cancellation, covered by a separate unwind test. The
publisher refuses after shutdown.

Replies retain an `Arc` to the original connection generation. Publication still
reserves the whole fanout before enqueueing. Listener admission continues to
cover completed task records until they are joined. Framing and limits otherwise
remain 0048's. Fixture commands, test signing key, fixed timestamp, allocator
instrumentation and stdout telemetry live in an explicitly feature-gated example,
not a kernel entry point. Diagnostic wire capture is off by default.

The new codec authenticates before parsing JSON, preserves parent bytes and
refuses extra binary buffers. Its output serializer limits bytes while writing,
including JSON-escaping expansion, before passing frames to the transport.
Connection-file validation enforces the local subset before listeners bind.
The kernel has independent reproducible notices; the root notices are unchanged.

## Still to implement and accept

The worker supervisor and platform containment, execution admission/counters,
stream barriers and IOPub ownership, interrupt/restart/shutdown, installation,
nbclient and actual JupyterLab notebook gates remain. Browser availability does
not pass gate 5. Root test success does not supply kernel timing evidence. No
Windows execution or notebook acceptance is claimed by this component commit.
