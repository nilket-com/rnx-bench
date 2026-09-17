# 0061 gate 2 evidence

Twenty actual-filesystem/Cargo identity cases pass using the new product module.
The fixture and exact commands are documented in probes/cache-identity/README.md.

| Changes | Key |
| --- | --- |
| Different application text | same |
| Mapped Rune package, renamed mount, edited mapped contents | same |
| Relative spelling of the same native roots | same |
| Symlink selecting the same cache root | same |
| Native trees moved with identical contents | different |
| Registration name, builder path, plain/lifecycle hook | different |
| Adapter bytes or runtime bytes | different |
| Real additional Cargo dependency | different |
| Actual native default-feature activation | different |
| Explicit selection of the installed toolchain | different |
| Previously absent Cargo config, cache root or Cargo home | different |
| Original inputs restored | original key |

Every result is also computed with reversed inventory ordering and is identical.
Eight cases compile and run: baseline, relocated native, registration name,
builder path, lifecycle hook, native edit, Cargo graph and native feature activation
are recorded with output/artifact hashes (eight builds in total).

Tool suites: 40 passed each, two ignored each, zero failures. Strict all-targets
Clippy passes in both configurations; formatting and notices pass. Windows
all-targets type-check passes with the pre-existing test-only unused UNIX_EPOCH
import warning, without an execution claim. The native dependency graph/lock is
unchanged. The root source outside the project tool is unchanged.

Three new unit tests pin canonical document/refusal behaviour, independently
changed context fields and inventory association/boundary validation. Synthetic
target/profile/feature-string mutations are not cross-target execution evidence.
The real cases use the installed toolchain and host target throughout.

conditions.json identifies the compiled probe, source baseline and source.patch;
imported-sources.json proves exactly which product files the probe used. Each
case contains canonical identity bytes and readable JSON plus its generated and
native sources, context, metadata and Cargo lock. results.json records hashes and
observed outputs. No user cache, history or database was touched; all fixture
commands completed before temporary directories were removed.

Product commands do not yet call this module. Cache publication, concurrency,
legacy lock migration, receipts, Polars cost and full workflow regressions remain
gates 3–6. No cache hit speed or user-facing behaviour change is claimed here.
