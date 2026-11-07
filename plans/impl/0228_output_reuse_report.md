# ADR 0228 follower: explicit output reuse report

Status: Accepted

Follow rnx ADR 0228 at published commit
`c7d08d9b8ef9ccd69ba5fba6916e689dbeaa989c`.

Report all six 100M F64 cells, first and warm medians and ranges across
five processes, raw sample times and receipt hashes. Derive the README
from a validated compact summary. Explain consuming map_reusing, exclusive
ownership, the 2x capacity bound, fresh-allocation fallbacks and no hidden
retention. Disclose exact approved plain-map exceptions and different-run
Arrow/Polars context. No new measurements or interpreter speed claims.
Keep public artifacts below 1 MB and exclude private paths and hostnames.
