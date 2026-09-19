# 0068 gate 1: registration API stop

The accepted plan asks for an isolated prototype before a product API or wrapper
change. The exploratory candidate makes `Extensions::with` generic over a return
convertible to Registration, retaining Vec help returns and admitting native
presenters. Its registry is context/session-owned, keyed by Rune native type hash,
and the existing formatter is unchanged. This patch is **not validated product
code**: the source-compatibility check stopped before Polars, display-protocol,
worker ownership, escaping and bounded-work gates. Do not port it.

The unchanged root test with a panic-only builder fails type inference. A separate
runner-only embedding consumer demonstrates the same break with an error-only
builder. It compiles against the baseline and fails with E0283 against the patch.
Giving these callers new annotations would hide a public source-compatibility
break rather than preserve the existing API.

```sh
python3 probes/frame-presentation/reproduce.py --work /tmp/rnx-0068-registration-review
```

The work directory must be absent; Cargo's required registry dependencies must
already be cached. The driver archives the exact recorded baseline and applies
the preserved patch in its own tree. Both consumers disable default features.
It retains logs and compilation outputs. No product checkout is modified.

Proposed next decision: retain `Extensions::with` and `with_lifecycle` exactly,
add a separate `with_presentations` builder API, and select it through an explicit
presentation hook in generated applications. Review that additive registration
and declaration shape before implementing it; this checkpoint does not declare
an automatic-display API complete or gate 1 passed.
