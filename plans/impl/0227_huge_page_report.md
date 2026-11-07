# ADR 0227 follower: huge-page timing report

Status: Accepted

Follow rnx ADR 0227 at published commit
`7802ce4af471ee6178118671e61b7b645b00883e`.

Report the six 100M F64 cells, five-process first/warm medians and ranges,
with raw sample times, binary identities and receipt hashes. Validate the
summary and derive the README table from it. Disclose the exact +1/call
exception, size-class constants, partial-THP cold call, column-buffer scope,
and different-day 0224 context. No confidence or interpreter-speed claim.
Keep public artifacts below 1 MB and exclude private paths and hostnames.
