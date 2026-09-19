# 0067 gate 2 evidence

See ../../probes/stock-management/README.md for sources, limitations and reruns.
The six frontend/matrix directories are the final results. `early/` is historical,
not a passing result. `boundary.json`, `discovery.json`, `scratch.json`, and their
PTY traces cover the newly introduced routing. `product.patch` and `clean.bundle`
preserve the measured root sources against accepted `4e887b6`.

No performance claim is made at this gate. All build durations are fixture runs
with registry sources cached, not end-user Polars or fresh-install measurements.
