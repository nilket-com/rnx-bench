# rnx 0172 attempts: producer source map

The pre-squash branch `w2-0172` commits are kept here for traceability. They're not pushed; the push is one squashed commit, whose tree contains every file listed below.

| Attempt | Producer tooling | Retained in |
|---|---|---|
| run1 | uncommitted: `4b362bd4`'s measure.py without its affinity lines | 4b362bd4 |
| run2 | 4b362bd4 | 6116c332 |
| run3 | 2acdf315 (references verified before any work) | e4de7a62 |
| diag-aa | c9bdd2a8 (diag_aa.py) | ac2ec45c |
| run4 | 7f188744 (amendment 7) | 50891c4f |

The final `probes/borrow-context-type-0172/measure.py` in the squashed commit is the run4 producer, byte for byte. Harness sources are exact copies of fb56b1d (`SOURCES-fb56b1d.sha256`).
