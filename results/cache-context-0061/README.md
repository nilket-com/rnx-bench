# 0061 gate 1 results

Pass on Linux. This is context/lifetime evidence before the product cache.
See probes/cache-context/README.md for the exact build and run commands.

- Real canonical wrapper/main, locked graph, native inventories and toolchain
  observations match temporary resolution, final build and a second consumer.
- The identity excludes resolution-directory names and its own final key, so
  choosing entries/<key>/assembly introduces no recursive identity here.
- Cargo traces show the same canonical cache-root and private Cargo-home configs
  opened. Both resolver and final workspace observe the cache's offline setting
  in the uncached-package control, without an explicit --offline argument.
- Two consumers read the same retained OUT_DIR file from the final entry; the
  original native directory remains CARGO_MANIFEST_DIR. Deleting temporary
  resolution workspaces does not affect it. Deleting that retained file alone
  causes a runtime failure, and restoring it restores the original output.
- Eighteen late config/toolchain candidate injections refuse, as do managed
  symlinks, FIFOs and generated-input symlinks. The user's symlink to the root
  succeeds. Allowed config changes/new candidates are detected by inventory,
  and unsupported config is refused before metadata.

observations.json contains the key, executable digest/size, both exact outputs,
retained path, entry byte count and assertion results. identity.json, preflight
and metadata captures, Cargo.lock, generated source, native fixture sources,
configuration files and syscall traces preserve the inputs and observations.
commands.json lists successful and intentionally refused commands. The prototype
binary/source identity and source commit are recorded. Imported product code is
byte-identical; only isolated prototype policy is new.

No Polars timing, cache hit speed, publication atomicity, concurrent build,
receipt migration or production cache acceptance is claimed. The small fixture
size is not Polars's size. Gate 5 must report Polars retained bytes and full
artifact-hash cost on attachment separately. Windows execution is not attempted.
