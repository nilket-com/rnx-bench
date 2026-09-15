# Record 0049: domain namespaces

`run.sh BEFORE AFTER` compares the accepted pre-migration release binary
with the migrated binary. Each side receives its own preserved JSON source;
process calls retain explicit deadlines. The output gate compares successful
exit, full stdout and stderr, including JSON refusal values. It does not
compare intentionally different diagnostic source excerpts as equal bytes.

Run after building root release and the accepted separate kernel package
(including its supervision examples). Notebook fixtures use the dedicated
`probes/jupyter-notebook/.venv` and isolate kernelspec installation from the
user's Jupyter directories. They copy `../rnx/target/release/rnx`; that must
be the AFTER binary. The shell script also reruns the real browser journey
and four supervision fixtures, writing a new results directory.

Old raw exports, notebooks and source snapshots are not rewritten. The
0044 process timing driver and 0047 identical-worker timing driver remain
historical revision-specific probes, documented at their call sites.
