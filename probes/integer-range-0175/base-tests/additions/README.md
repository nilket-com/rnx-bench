# Base-contract additions

Fork `c2b68025`, child of `c6f57bd0`. Production engine remains the shared base.
The first four golden files are byte-identical to c6f57bd0. Four new observer
files were captured on the base, then capture code was removed before this
commit. The exhaustive prefix comparison now reads the immutable checked-in
base lines and covers both memoized and associated dispatch.

Added: a resource-owning old output with a Drop counter; Diagnostics installed
at budgets 1/2/1000; finite 1 MiB and explicit usize::MAX scopes around VM
execution plus async_call polled inside Memory<Future>; vector receivers and a
user native struct implementing Rune's Iterator trait with its own NEXT and
call/position counters. The resource trace pins destruction to the original
NEXT store, not the subsequent IterNext or return.

First capture: three cases passed; the finite-scope fixture failed because it
also constructed the large standard-library Context inside the 1 MiB scope.
Correction: prepare the VM outside the scope; only VM execution is bounded,
as requested. Capture of this previously empty fourth file then passed. No
already-captured file was rewritten. The capture switch is absent from the
committed tests.

Final command is the same locked all-targets/all-features suite as the parent.
PASS: 608 unit tests, registration inventory, and UI compatibility. Logs here
retain the capture failure, the targeted repair, and final complete replay.
These are semantic tests, not deciding performance measurements. Same compiler
and Cargo.lock as the parent base-test receipt. Candidate hit/fallback counters
have not been implemented yet and are required before candidate evaluation.
