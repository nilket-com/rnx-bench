# Step-four server boundary evidence

Measured by Codex on 2026-09-16. Reproduce with
[`../../probes/server-boundary/README.md`](../../probes/server-boundary/README.md).
This is a Rune-only boundary experiment, not an rnx HTTP implementation.
The root executable and PostgreSQL adapter are unchanged.

Two complete repeats pass: **70 scheduling samples, eight ownership cases**.
The final source is formatted and passes release clippy with warnings denied;
the locked offline release build is recorded by SHA-256 in conditions.json.
No root suite rerun is claimed or needed for this probe-only change.

| Model and slow work | Healthy median, repeat 1 | Repeat 2 |
| --- | ---: | ---: |
| One shared thread, awaiting | 0.0055 ms | 0.0061 ms |
| One shared thread, CPU loop | 59.2120 ms | 59.2614 ms |
| Two workers, awaiting, one spare | 0.0137 ms | 0.0352 ms |
| Two workers, CPU loop, one spare | 0.0107 ms | 0.0128 ms |
| Two workers, both CPU-bound | 56.9576 ms | 59.1631 ms |

These are healthy **dispatch-to-completion** medians, including queueing,
not HTTP timings. The CPU handler spends its whole 10,000,000-instruction
budget; it is never resumed. Awaiting is a 250 ms sleep. Raw samples, completion
order and VM outcomes are in scheduling-0/1.jsonl. Saturation has a 72.4 ms
maximum in these final runs; no median is a latency guarantee.

The single-slot transaction actor passes Rune panic, budget halt and awaiting
deadline cases, with the queued borrower admitted only after acknowledged
rollback and independent observation. Before rollback, row locking refuses
with 55P03; afterward the original row and absence of the audit row are visible.
The same backend is reused and returns zero audit rows to the next Rune call.

Shutdown during active SQL waits approximately 800 ms for the server-side
statement timeout and rollback. Dropping the handler does not cancel that
command. The owned client and observer contribute two socket descriptors and
two runtime driver tasks while quarantined, all explicitly asserted. Both fall
to zero before block_on ends. The local owner task is separately joined:
LocalSet tasks are not inferred from the runtime metric. Backend disappearance
is measured separately, also reaching zero; the Python parent checks it again.
cleanup-0/1.json prove each private postmaster and directory disappeared.

The results support a bounded-worker candidate with explicit saturation and
a server-owned transaction/pool shutdown path. They do not prove a production
pool, HTTP protocol behavior, arbitrary native-call interruption or integration
with rnx's thread-affine Scope. No new public lifecycle primitive follows from
this experiment alone. The proposed 0054 draft makes assembly the next gate.

Initial fixture corrections: Rune calls its raw budget halt `limited`, not
`budget`; the assertion was fixed. A first zero-only runtime-task assertion
was strengthened by placing Send connection drivers on the runtime and proving
two live tasks before cleanup (the original local drivers were explicitly joined
but not counted by that metric). These files are fresh full runs of the final
binary, not a mixture of those development runs.
