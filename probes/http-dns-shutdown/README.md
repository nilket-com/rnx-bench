Record 0034 DNS shutdown counterexample. Uses the same spawn_blocking and
abort-on-drop pattern as hyper-util 0.1.20's GaiResolver, substituting a
controlled two-second delay for getaddrinfo. No network or DNS is performed.

cargo run --release --locked --manifest-path probes/http-dns-shutdown/Cargo.toml

Output: results/http_0034_dns_shutdown.txt. The request deadline expires
while a started blocking lookup survives; zero async tasks does not imply
bounded runtime destruction. This is a model of a stalled system lookup,
not a claim that system DNS took two seconds on this machine.
