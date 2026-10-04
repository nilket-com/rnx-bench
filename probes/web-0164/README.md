# 0164 HTTP host gate

The generic product is `rnx serve`. This probe reuses the unchanged 0162 Rune
workload, axum reference, Flask reference and 26 frozen wire fixtures. Applications
need no Rust launcher. HTTP/1, two workers, server CPUs 2,4; oha CPUs 8,10,12,14.

- `host_controls.py STOCK_BINARY`: actual host options, source location, wire
  bounds, invalid outputs, HEAD, keep-alive, deadlines, disconnect, queue/admission
  pressure, grace/drain, IPv6, undrained stderr and parent descriptor flags.
- `run.py --controls`: inherited fail-closed load refusals.
- `run.py NEW_OUT`: three interleaved repetitions of five conditions, 3s warmup
  and 10s measured. Request logs disabled for all systems. All complete oha JSON
  and exits retained, plus connection and RSS samples, fixture logs and medians.
- `validate_saved.py OUT`: exact 45-condition census, 90 complete artifacts,
  warmups and measured schemas, exits, association and keep-alive occupancy.
- `logging_cost.py NEW_OUT`: separate three-repetition hello/c32 product comparison
  with request logs off versus default logging to a drained file. Log counts,
  hashes, sizes and non-request records retained; repetitive log files removed.
- `readiness.py OUT_JSON`: ten interleaved starts per host, excluding fixtures;
  product waits for all slots, gunicorn for two loaded worker callbacks.
- `summarize_logging.py LOG_OUT`: delivered plus dropped must equal all successful
  warmup, measured and wire-control requests.
- `startup.py`: 0068's interleaved two-repeat stock launch gate against f86c714,
  100 samples per binary/command and 200 persistent prompt cells. A reproducible
  median regression over 5% fails. `startup_common.py` isolates config/history.

Build the A/C references with 0162's setup, and copy the reviewed product binary
into `target/stock`. The initial startup sample uses `target/baseline`, the saved
f86c714 stock binary. No builds or test runs should overlap timed measurements.
The final sample journals state exact binary hashes and commands.

The product uses its default 2,000,000-instruction budget, versus 10,000,000 in
0162/0163; the compared handlers fit. Product limits/logging/ownership differ
from the references. This is a local workload comparison, not an axum-equivalent
performance claim or a completed Flask-style framework.
