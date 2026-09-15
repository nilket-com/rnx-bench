# Source ownership accounting for the 0048 prototype

This accompanies tests and allocator measurements; it is not a claim of an
exhaustive protocol audit. Source hashes in hashes.json identify the checked
implementation. Private fixture instrumentation is included below.

| Owner | Bound and lifetime |
| --- | --- |
| Listener and task records | eight admission permits per endpoint, retained by the listener until JoinSet completion is collected; one transient excess accepted socket |
| Greeting | fixed 64-byte arrays; two-second handshake deadline |
| READY metadata | at most 8 KiB body, at most 64 property entries; copied names/values are subsets of that bounded body |
| Incoming multipart | at most 32 byte vectors and 32 permits; total requested capacities at most 1 MiB per connection; charged before allocation against the endpoint's 8 MiB |
| Complete input | same Message and permits through application processing; no second completion queue or independent ownership copy at handoff |
| Heartbeat | at most 23 command-body bytes; at most 23 encoded PONG bytes, using existing send byte/entry permits; no retained history |
| Subscriber state | at most 128 keys, each at most 256 bytes, and u16 reference counts |
| Encoded message candidate | encoder checks its capacity sum against 2 MiB before allocation; one publisher candidate at a time, in addition to admitted publication obligations |
| Outgoing connection queue and current write | common byte and entry permits stay in Packet through the write; 2 MiB/64 for PUB, 1 MiB/32 otherwise |
| Publication recipients | at most eight; all byte/count/global reservations precede queue insertion; partial reservation failure drops all reservations without fanout |
| Publication total | capacities charged per recipient, even for shared Arc bytes, at most 16 MiB; current and queued packets both retain global permits |
| Registry | at most eight entries per endpoint; retired connections cannot receive new data through an old sender; generation does not wrap |
| Trace and error instrumentation | at most 64 bounded trace events (512-byte READY prefixes / 257-byte subscription prefixes), one 512-character last error |
| Private publication requests | eight jobs, each just a count and pacing flag, rather than an unbounded list of encoded messages |

Packet drops release credit on write success, error, cancellation and receiver
shutdown. A cancelled partial write closes its socket rather than appending the
next message onto an unfinished frame. Subscription retirement cancels both halves
of that connection. The listener drains its JoinSet on shutdown before the final
snapshot. The old generation's channel is closed; name reuse never redirects it.

Allocator counters independently wrap Rust's System allocator and record live
requested bytes, high-water requested bytes and largest request. They do not
consult the payload semaphores. OS buffers, allocator size classes, RSS and
page retention are distinct, so external RSS is also sampled. Counters can be
sampled at different moments from endpoint state; cleanup checks await both.
The repeated maximum-payload cycles test release rather than pretending that
one instantaneous cross-thread snapshot is atomic.

Hash-map buckets, vector descriptors, Tokio tasks and frame overhead have bounded
entry counts but are not charged as payload. The signed-echo fixture's bounded
JSON parsing/serialization can make additional representations of an input;
these are application work, not additional unbounded transport queues. The
40 MiB figure describes retained wire payload across five endpoints, not total
process memory. Fixed-capacity header parsing and frame limits prevent a peer
length from becoming an unchecked reservation. Application validation and HMAC
remain after that bounded transport admission.
