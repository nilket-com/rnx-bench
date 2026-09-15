# Jupyter transport gate for rnx 0047

This is a standalone local fixture, not a kernel implementation. It binds five
loopback sockets and exercises the selected Rust transport with Python's actual
jupyter_client Session and pyzmq. No personal kernelspec is installed.

## Reproduce on Linux

From rnx-bench, with rnx checked out alongside it:

```
uv venv --python 3.14 probes/jupyter-transport/.venv
uv pip sync --python probes/jupyter-transport/.venv/bin/python probes/jupyter-transport/requirements.txt
cargo build --manifest-path probes/jupyter-transport/Cargo.toml --locked --release
PYTHONDONTWRITEBYTECODE=1 probes/jupyter-transport/.venv/bin/python probes/jupyter-transport/probe.py
```

Python packages are pinned in requirements.txt; Cargo.lock pins the Rust graph.
The Python freeze is the measured Linux environment, not a tested Windows lock.
Results and tool versions are under `results/jupyter-0047/`. The test key is a
constant fixture value, never a user's Jupyter connection key. Every network
endpoint is the probe's own loopback listener. The largest announced frame is
64 MiB; the test does not attempt exhaustion. The global allocator reports
allocation request size, **not resident memory or total live allocation**.

## Findings

- Signed requests/replies interoperate, including extra routing identity and
  extra JSON fields; wrong signatures receive no reply and are not dispatched.
  Empty-key operation works. Short multipart and unsupported buffers are refused
  by the fixture's application parser, not by claims about upstream parsing.
- Fifty PUB sends succeed with no subscriber. This is not delivery evidence.
- An unread subscriber produces a send timeout/error at the probe's 250 ms bound;
  separate control and heartbeat remain responsive. The fixture does not reuse
  that timed-out publisher for further sends or prove cancellation-safe reuse.
- A 4 MiB message is allocated before the application refuses its 1 MiB limit.
- More decisively, a 9-byte long-frame header announcing 64 MiB, with no body,
  causes an allocation request of about 64 MiB before application recv returns.
  That crosses record 0047's receive-bound stop condition.

`source-audit.json` hashes the reviewed files from the locked zeromq 0.6.0 source.
ZmqCodec::decode reserves waiting_for bytes and obtains that value from the
peer's frame length. Multipart frames accumulate internally before returning a
message. SocketOptions has identity and connect-timeout settings, not frame or
multipart limits. Application validation and HMAC happen after this allocation;
neither fixes it. There is no claim of an application-level memory ceiling.

The server implements only enough framing to test transport, not the full
kernel message set. The publisher's probe messages are deliberately simple
multipart frames, not execute_result messages. Kernel installation, execution
semantics, history, rich output and browser behavior remain unimplemented.

A clean-target release build was timed offline with all dependency sources
already cached. `clean-build-time.txt` records elapsed time and build-process
maximum RSS; `binary.json` records the binary size. `rust-packages.json` records
resolved features and declared licences, not a completed redistribution-notices
audit for a shipping kernel. No evcxr or zeromq source was copied into the probe.

Playwright is installed in the pinned environment. Its planned Chromium revision
is recorded in `planned-browser.json`; the browser has not been downloaded or
run. The later JupyterLab gate is a headless Chromium/Playwright capture, not an
nbclient run relabelled as screen evidence.
