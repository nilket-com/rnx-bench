0175 development compile/test checkpoints, before R1/R2 review fixes. No timings.
Final clean source: fork f57fb10c2ee4f1d8e790b4728a8642e78e6a1a50.
Final chain: cargo test -p rune --all-targets --all-features --offline; cargo test -p rune --lib --no-default-features --features alloc,bench,byte-code,capture-io,cli,disable-io,doc,emit,fmt,languageserver,musli,serde,std,workspace --offline range_iteration; cargo check -p rune --no-default-features --features alloc --offline.
All under the shared lock. Final: 609 unit + 2 integration; 14 non-tracing; no-std passed.
Earlier uncommitted source checkpoints include compile failures (wrapper field; Option conversion; private vm accessor); a positive-hit failure revealing memoized Type callable resolution; and a non-tracing configuration failure because upstream tests require languageserver. The first all-feature suite predates conservative tracing-feature fallback. These checkpoints are superseded for final gates, retained for disclosure.
