# Record 0048 bounded ZMTP prototype

**Not accepted for integration.** The default interoperability run reaches the
record's explicit command-compatibility stop: the heartbeat-enabled libzmq
client sends PING after a 3.0 greeting. This prototype refuses that command.
See `results/jupyter-zmtp-0048/README.md` before using these results.

From this directory:

```sh
cargo build --release --locked
cargo test --locked
../jupyter-transport/.venv/bin/python probe.py
```

The last command is expected to exit **1**, with a named heartbeat gate failure.
It cleans up the server and checks zero remaining connection/credit counters.
The Python environment and its complete pins are in the earlier transport
probe. The fixture uses only loopback ports and a public test HMAC key. Servers
have a 512 MiB address-space limit; tests send finite bounded workloads.

For independent diagnostic coverage, explicitly disable the client's transport
heartbeat setting (this does not pass the default gate):

```sh
../jupyter-transport/.venv/bin/python probe.py --diagnostic-no-heartbeats
```

That run covers signed/empty-key exchanges, three ROUTER endpoints, binary REP
heartbeat, metadata and payload boundaries, maximum u64 lengths, split greetings,
32/33 parts, duplicate/reconnected/anonymous identities, a forced generated-ID
collision, connection caps, deadlines, subscriptions, publication saturation and
cleanup. The five Rust tests cover framing splits/truncation, capacity release,
subscription/count overflow and publication/reply admission mechanics. They do
not amount to exhaustive acceptance of every record gate.

## Shape and accounting

The server is a standalone Rust/Tokio executable, with no Rune or ZMQ library.
One task owns each listener and its JoinSet of admitted connections; each
connection independently reads and writes. Handshake and assembly have absolute
timeouts. A u64 length is checked before conversion and allocation. Payload
credit moves with a complete message through application processing. Exact
payload capacities are checked. Frame/credit descriptor vectors have at most 32
entries; handshake dictionaries at most 64 properties inside an 8 KiB body.

Each endpoint admits eight connections, including unfinished handshakes. The
accept loop may briefly own one additional socket before closing it. Outgoing
credit includes the current writer packet, not only its queue. Publication
preflight reserves each recipient's byte/message allowances and the total before
queueing any recipient. Slow peers are closed. Generated identities start with
zero but collisions with arbitrary raw-peer declarations are still checked.
Connection-specific senders and a generation counter keep stale replies away
from a newly connected peer with the same identity.

The bounded test trace stores at most 64 events, with greeting bytes, READY
prefixes (at most 512 bytes) and subscription prefixes (at most 257 bytes). It
is fixture instrumentation, not a production wire logger. A single last-error
string is limited to 512 characters. Stats on the parent's separate stdin/stdout
channel include routes, identities, credits and the trace. `stop` joins listener
and connection tasks, then emits the final snapshot. Script output/worker modes
are not implemented. Application errors in the signed echo fixture can close the
connection; this is not 0047's final Jupyter refusal behavior.

## Limits of the evidence

RSS samples before/after the finite multipart attempt are not peak-memory
measurements or an independent exhaustive allocator audit. Windows cross-check
is type checking only. There is no installed kernel, notebook screenshot,
worker integration, final notices audit or rnx performance comparison here.

The unpaced publication flood can exceed even the reading Python subscriber's
queue capacity. Both subscriber connections were gone at its final snapshot;
receiving some output does not prove sustained service to a healthy peer.
A paced producer/consumer gate and the remaining aggregate-capacity, partial-write
and teardown-state tests are still needed after the protocol decision is reviewed.
Do not cite the diagnostic command's exit zero as all five record gates passed.
