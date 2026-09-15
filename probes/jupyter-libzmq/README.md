# Native transport replacement for record 0047

A probe, not a kernel. Build with `cargo build --release --locked` here and run
`../jupyter-transport/.venv/bin/python probe.py` from this directory. The Python
environment and pins belong to the preceding transport probe. Output is JSONL
on stdout; stderr files go to `results/jupyter-0047-replacement/`.

The independent lockfile selects zmq 0.10.0, zmq-sys 0.12.0 and
zeromq-src 0.2.6+4.3.4. The binary reports native version 4.3.4; it does not use
nano's system 4.3.5. It builds through cc with the native compiler toolchain,
without CMake. Each socket has one owning thread. ROUTER receivers call
recv_bytes for individual parts, retaining at most 32 parts/1 MiB and discarding
excess until the final part. This does NOT establish a pre-receive native bound.
The receiver deliberately does not claim to disconnect an individual ROUTER
peer: there is no proven abandonment mechanism in this probe.

Every socket has MAXMSGSIZE=1 MiB, SNDHWM=RCVHWM=64, linger=0, receive timeout
20 ms and send timeout 100 ms. The publisher has an eight-item admission queue.
Real jupyter_client signs requests and verifies replies, including additional
routing frames and empty-key mode. A reading subscriber and an unread subscriber
are both confirmed connected before publication. PUB counts are successful local
sends, not delivery counts; no exact subscriber loss is inferred.

The raw ZMTP client sends a finite counterexample, not an exhaustion workload:
4096 8 KiB parts with MORE, sampled halfway and at 32 MiB, then an empty final
part. The server runs with a 512 MiB address-space limit. External /proc statm
RSS includes native allocations, at the machine's page resolution, but does not
identify each allocation or prove a total memory ceiling. The 200 ms observations
are not deadlines or guaranteed consumption times. Healthy shell/control probes
and heartbeat run while the multipart is unfinished. Source audit confirms why
the application receives no parts until completion. An oversized 64 MiB length
header, without a body, is separately refused by closing its connection.

Result: replacement still reaches the receive-memory stop condition. See
`results/jupyter-0047-replacement/README.md`. Do not start kernel integration on
the assumption that part-at-a-time application reads fix native buffering.
