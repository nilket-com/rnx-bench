# Record 0056 gate 3: errors returned by COMMIT

Linux, private PostgreSQL 18 cluster, tokio-postgres exactly 0.7.18. This is
an isolated classification probe, not a new rnx API or pool implementation.
Run from rnx-bench:

```sh
python3 probes/commit-classification/run.py
PYTHONDONTWRITEBYTECODE=1 python3 probes/server-transactions/transactions.py \
  --output results/commit-classification-0056/transaction-regression
```

The second command reuses the accepted gate-5 binary named and hashed in
`server-transactions/build.json`. If it is absent, rebuild that prototype using
its documented build procedure and retain the resulting build identity. Its
source and fixtures are unchanged; the replay tests old lost-reply/rollback
behavior, not integration of the new classifier into the pool. Extraction and
integration remain record 0056 gate 4.

Each of two fresh clusters runs these cases:

- A deferred foreign key rejects COMMIT with 23503.
- Two serializable transactions read a shared predicate and write separate rows.
  The antagonist commits first; the victim's COMMIT rejects with 40001.
- A deferred constraint trigger takes an advisory lock during COMMIT. The
  antagonist already holds it and is observed waiting for the victim's lock.
  A 50 ms victim deadlock timeout versus a 10 s antagonist timeout makes the
  victim detect the cycle and return 40P01 from COMMIT, not from earlier SQL.
- A deferred trigger explicitly raises 40003. Although this fixture rolls back,
  the classifier calls it ambiguous. The class-40 prefix is not an allowlist.

Classification requires an actual driver DbError for the one outstanding
COMMIT, nonlocalized parsed severity ERROR, and class 23 or exactly 40001 or
40P01. Other errors remain ambiguous. A separate observer waits for the victim
backend to be idle with no transaction, then verifies the victim's audit row,
insertions and updated row all match their pre-transaction state **before** the
client is dropped. An antagonist's independently committed row is not claimed
rolled back. Mere invisibility of an uncommitted insert is insufficient.

Every victim connection is retired by dropping its client and awaiting its
connection driver, including known rejections; no ReadyForQuery/reuse claim is
inferred from DbError. The replacement has a new backend PID and answers a
query. The unchanged fault proxy counts one
literal COMMIT on the victim's wire connection. The classifier never retries
or performs an outcome-reconciliation query; only the fixture observer reads
outcomes. All drivers are joined and independent psql checks see zero tagged
backends after each case. The private cluster is stopped and reaped.

The eight-case unchanged transaction regression preserves lost-COMMIT-reply
ambiguity (including observed commit), lost rollback retirement and the original
completion/cancellation policies. All artifacts are under
`results/commit-classification-0056/`.

The lock was seeded from the accepted server-transactions graph. Every third-
party package/version is already present there; conditions.json records the
resolved package/license inventory and source/lock/binary hashes. Existing
`server-transactions/ADDITIONAL-NOTICES.md` together with that archive's root
notices cover this subset. No binary is distributed. The debug profile is for
correctness, not a performance comparison. No system PostgreSQL server is used.
