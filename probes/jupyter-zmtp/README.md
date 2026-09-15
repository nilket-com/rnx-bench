# Record 0048 bounded ZMTP prototype

**Ready for review, not yet adopted by 0047.** The accepted bounded heartbeat
extension handles the PING that libzmq sends after a 3.0 greeting. Current evidence
is in `results/jupyter-zmtp-0048-extension/`. The original failed prototype and
its captures remain in `results/jupyter-zmtp-0048/` and commit ae74699.

From this directory:

```sh
cargo build --release --locked
cargo test --locked
../jupyter-transport/.venv/bin/python probe.py
```

The command now exits **0**, with client transport heartbeats enabled.
It cleans up the server and checks zero remaining connection/credit counters.
The Python environment and its complete pins are in the earlier transport
probe. The fixture uses only loopback ports and a public test HMAC key. Servers
have a 512 MiB address-space limit; tests send finite bounded workloads.

The optional no-heartbeat mode remains for comparison, not as an acceptance workaround:

```sh
../jupyter-transport/.venv/bin/python probe.py --diagnostic-no-heartbeats
```

The default run covers signed/empty-key exchanges, three ROUTER endpoints, binary REP
heartbeat, metadata and payload boundaries, maximum u64 lengths, split greetings,
32/33 parts, duplicate/reconnected/anonymous identities, a forced generated-ID
collision, connection caps, deadlines, subscriptions, publication saturation and
cleanup. Run `bash run.sh` to rebuild, run the Rust tests, and record both wire fixtures
twice. `extended.py` adds heartbeat boundaries and idle/interleaved deadlines,
all forty connection slots with 40 MiB reserved, independent allocation counters,
stale pending replies, pending-read/write shutdown and READY/identity boundaries.
Eleven Rust tests cover parser fragmentation, capacity endpoints, reference counts,
atomic fanout failure, command admission, partial writes and absolute write timeout.
The evidence map distinguishes wire tests, unit tests and structural bounds.

## Shape and accounting

The server is a standalone Rust/Tokio executable, with no Rune or ZMQ library.
One task owns each listener and its JoinSet of admitted connections. Admission
permits remain in a listener-owned map until the task is joined, bounding both
running and completed task records. Each
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

The old unpaced flood was inconclusive. The new producer emits 1000 messages
with a 2 ms pacing request; actual intervals depend on scheduling. The fixture
proves the stalled connection disappears, the reading connection generation is
unchanged, and all 1000 publications plus a final marker arrive. Control and
heartbeat are checked while publication is still pending. This measures service
under that offered load, not lossless delivery at arbitrary publication rates.

PING is bounded to 7–23 command-body bytes, PONG to 5–21, before body allocation.
PONG echoes at most 16 context bytes through the same bounded writer. TTL and
valid inbound PONG are ignored. Interleaved commands leave a multipart's deadline
unchanged; standalone heartbeat traffic does not acquire an idle data lifetime.
The server remains 3.0 plus this extension, not a general 3.1 implementation.
