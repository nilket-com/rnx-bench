# ADR 0229 follower: write-only masked F64 report

Status: Accepted

Follow rnx ADR 0229 after publication. Report the six 100M const/add cells,
first and warm medians and ranges across five processes, raw sample times,
binary identities and receipt hashes. Explain removal of the output prefill,
unchanged reuse admission, the user-approved sliced-null REP-store exception,
and the observed fault differences without claiming a fault reduction.
Preserve failed gate disclosures and distinguish measurement from acceptance.
Correct the 0228 Arrow-context attribution using committed 0224 Arrow and
Polars figures; explicitly note Polars leads the flat-chain context result.
No new measurements. Keep public artifacts below 1 MB without private paths.
