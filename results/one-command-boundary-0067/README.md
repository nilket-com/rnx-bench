# 0067 gate 1 evidence

Gate 1 prototype is ready for review. Production rnx and tool sources are
unchanged at `9570b25`. The private implementation and replay instructions are in
[the probe](../../probes/one-command-boundary/README.md).

## Results

- A real Cargo Git install of the fixture origin installs only `rnx`; its
  `project adapters` command lists Polars and PostgreSQL through the internal
  management library. No binary or source payload is embedded.
- Actual runner-only release compilation, package graph and symbols exclude
  management. `rnx_project::dispatch` is present in stock as a positive control
  and absent in the consumer. `rnx-project`, `blake3`, `toml` and `sha2` are absent
  from the consumer's resolved graph. A forced rebuild with Git trapped succeeds
  with zero Git calls and networking disabled.
- Both adapter graphs, the server graph and an actual generated combined wrapper
  omit management. The wrapper preserves allocation accounting/project sources.
  No combined native build is claimed in this gate.
- Thirteen main coordinate cases plus the missing-acquisition-evidence control
  pass. Clean path builds are unverified and reach consent. Pushed succeeds at
  acquisition; unpushed fails there, preserving Cargo's diagnostic. Dirty and
  unknown refuse before acquisition. Fresh and cached real Git installs classify
  acquired with two revisions sharing one Cargo cache. Removing FETCH_HEAD gives
  unverified, not an invented acquired state or a refusal.
- Fifteen fixed schema vectors, 42 malformed/binding cases, and 11 independent
  retained-context key changes pass. Existing declaration/lock/receipt/identity
  readers remain byte-identical; ready uses the unchanged old decode helper.
  New readers do not run on any product path.

The ordinary stock path build is also traced: zero Internet socket calls. The
coordinate driver runs every refusal/description/decline with Cargo trapped and
network disabled, creating no request directory. Its gate-only switch is not the
real session protocol; that remains gate 2.

The binary sizes in `boundary.json` are artifacts, not a matched size/performance
claim: stock and the external consumer use different Cargo profile settings.
Stock startup timing, combined notices and the changed default dependency graph
are gate 5. There is no inference from the current binary size.

## Schemas pinned

| Document | New | Original path reader |
|---|---:|---:|
| Declaration | 2 | 1 |
| Lock | 4 | 3 |
| Receipt | 5 | 4 |
| Assembly identity / generator | 3 / 3 | 2 / 2 |
| Ready | 3 | 2 |

See `vectors/index.json` under the probe for both fixed byte hashes and BLAKE3
encodings. `schemas.json` records the explicit refusals and retained identity
inputs. Git ownership replaces native tree digests only; external audit and the
rest of 0061 remain. This gate validates wire shapes, not the future raw-blob
verification or Cargo workflow.

## Evidence map

`setup.json`, `fixture.bundle`, `prototype.patch`, `final-prototype.patch` and `unpublished.bundle` preserve
the actual fixture sources against the published `94f5f3f` prerequisite.
`coordinates.json` and `no-acquisition-evidence.json` record classifications.
`boundary.json`, `consumer-no-git.json`, `generated.json` and the exact generated
wrapper cover graph/feature/symbol controls. `stock-build-network.*` retains the
actual build trace. `checks.json` records checks and unchanged reader hashes. `source-hashes.json`
and `schema-adapters.patch` retain the remaining isolated reader correspondence.
The prototype root lock was regenerated offline, with incidental compatible
updates; the production port should preserve unrelated pins.
`commands.jsonl` retains command outcomes including failed scaffolding attempts.

## Findings and limits carried forward

The private root initially failed with “multiple workspace roots”; excluding the
internal crate from root workspace membership resolves it and is part of the
archived prototype. The clean-unpushed assertion initially expected “revision”
but Cargo reported “revspec”; the actual result was the required post-consent
refusal, and the fixed assertion binds the missing full revision. Formatting and
clippy also caught probe-only adapter placement and an unused copied helper;
both are corrected, with failures retained in the command journal. The new build
script had one collapsible-if lint. Its equivalent correction is retained in
`style-check.patch` and `style-check.bundle`, with a real Git installation of that
revision passing acquired classification, management output and eval controls.
The earlier coordinate matrix remains tied to its original source bundles.
Root clippy also reports 13 existing warnings in unchanged library code; no root
strict-clippy pass is claimed. New main/build code has no diagnostics.

The stock build scans on every build to detect chmod; ordinary Cargo file mtimes
cannot provide that guarantee. Defaults-off consumers skip discovery completely.
Acquisition uses local trusted Cargo evidence and makes no reachability promise.
The acquired/unverified distinction changes notice wording only. Gate 2 still
owes the real consent protocol, shell-quoted recoveries for arbitrary paths,
retained-session failure behavior and management startup isolation.
