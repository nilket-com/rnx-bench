# 0179 prep1: neutrality stop and investigation

`../prep1/` is the first S1 run, retained as it stopped (`s1.status` = exit 1). Suites passed on both sources; the
neutrality control in its first form (whole-file sha256 equality with 0178's P0 base primary) failed:
`619d30c3...` against `7a66b042...`. `build.py` then removed its target, so that binary was not kept.

Investigation, untimed, under the shared lock, run by hand rather than through the build ledger (so there is no
ledger row for it; this file is its receipt):

	git -C /home/me/work/rune-w-0173 checkout -q --detach 4e84cfacc0278a4f1645c14310453bdc30ac77b4
	env -i PATH=/home/me/.cargo/bin:/usr/bin:/bin HOME=/home/me LANG=C.UTF-8 CARGO_HOME=/home/me/.cargo \
		RUSTUP_HOME=/home/me/.rustup CARGO_INCREMENTAL=0 CARGO_TARGET_DIR=<probes/startup-0179/tgt-build> \
		cargo build --release --locked --offline -j 8 --manifest-path probes/profile-paired-0178/harness/Cargo.toml

Status 0 (`Finished release profile [optimized] target(s) in 37.21s`). The result has the same sha256 as the stopped
run's (`619d30c316b18ae3bd51d9de3ccd34bc5e0f3e2c35c42d1dea276ed84def9641`), so the difference is deterministic. It is
retained, untracked, at `probes/startup-0179/neutrality-bin/prep1-investigation-p0-base-primary`.

- `comparison.json`: `neutrality.py` on that binary against the retained 0178 reference
	(`/home/me/work/rnx-bench-w-0178d/probes/profile-paired-0178/bin/p0-base-primary`, sha256 `7a66b042...`).
	477 differing bytes in a 9,007,272-byte file: 20 build-id descriptor bytes, 456 bytes in the `.llvm.<digits>`
	suffixes of 32 local symbols, and 1 byte: the line field of the panic location for
	`crates/rune/src/compile/context.rs` column 47, 535 -> 537, which is the two `#[cfg(test)]` lines the base adds
	at line 433. `.text` and every other byte are identical.
- `neutrality-controls.json`: the comparator's fail-closed controls on the same pair.

What this supports: the tests-first base has the same machine code and data as 0178's base apart from one panic line
number. It does not show whole-binary identity; panic diagnostics for that location differ.
The first form of the comparison (section list only, path length only) was replaced after review found it accepted a
flipped ELF header byte and did not resolve the referenced path.
