# 0181 execution-cost diagnostics: official run, COMPLETE

One official run under plan rnx 7d0f280. Registered outcome: **COMPLETE**: R and all three eligible diagnostics (C
branches, D frontend delivery, E loads) completed their 140 samples and reproduced the 0179 instruction and cycle
anchors. This record was selected after seeing 0180's measurement STOP; 0180's group B stays failed and uninterpreted,
and groups A and B were neither opened nor measured here. Nothing was repaired, replayed or added after the result. No
engine, profile or product change follows, and 0179's STOP is unchanged.

## Identities

- Subjects: the two retained 0179 PRIMARY binaries, staged at 0179's stage path with E0 and 0179's argv, hash checked
  before and after every sample: base `af06e8b3...0c87`, candidate `e4a5f207...a787`.
- Driver `probes/execution-cost-0181/events0181.py` (source 11ceb6e4, tree 52ae9c49). It imports 0180's `events.py`
  (sha256 `36595033...10c2`) and 0179's `common.py` (`abd19671...ddba`) as pinned libraries, verified before import.
- Discovery `discovery1` (driver d3cf6e39): availability sha256 `298b3d5dd83c8f5b80075ebd21e6e868f4e09c806d7eecc21fed57213290d2de`,
  identity sha256 `c281c11d5b0a0d3552415836e66635a9aed03c6fa3162c06f7f921848882f2aa`, byte-identical to 0180's identity
  (no host field changed). Eight opens, two per group, on the affinity probe; all four groups eligible.
- Rehearsal `rehearsal1` (11ceb6e4). Official raw rows sha256 `4b83a82b650d0aa8739d0e6ac38e822719694d0e9ad3c46167b655ea17d0d418`.
- Event definitions (unchanged from 0180, cpu_core, user only, one strong pinned group with both anchors, `--no-scale`):
  C BR_INST_RETIRED.ALL_BRANCHES (0xc4/0x00), BR_MISP_RETIRED.ALL_BRANCHES (0xc5/0x00); D IDQ.DSB_UOPS (0x79/0x08),
  IDQ.MITE_UOPS (0x79/0x04), ICACHE_DATA.STALLS (0x80/0x04); E MEM_LOAD_RETIRED.L1_MISS (0xd1/0x08),
  LD_BLOCKS.STORE_FORWARD (0x03/0x82).

## Disclosures

- Retained control runs: controls1 19/19 (433208f4), controls2 20/20 (ea5045e3), controls3 22/22 (d3cf6e39),
  controls4 23/23 (11ceb6e4); each includes 0180's 26 controls replayed against the pinned library.
- A first dry run of the new controls, 17/19, was made in a scratch directory and NOT retained. One failure was a real
  driver gap (a counter line with no event name was ignored, as in 0180's parser); 0181 refuses such a line as
  unclassified, hence global. None of 0180's 417 retained rows contains such a line; 0180's file and results are
  unchanged. The other failure was an ineffective control that altered a metadata field instead of the post-sample
  stage hash the driver compares; it was replaced. No receipt exists for that run.
- Review then required two driver repairs before discovery: the open check now applies the same 0181 classifier as
  the official run, and the pinned library bytes are hashed with the standard library before import.
- The mocked official runs inside the controls write synthetic raw rows; after checking them the control script keeps
  their counts and sha256 and removes the synthetic files (controls1 predates this and kept them). Real discovery,
  rehearsal and official raw rows are all retained.
- perf 7.0.14's JSON rows carry no PMU field and no enabled-time field; the cpu_core binding is the frozen argv.

## The official run

Command, from the repository root at a clean tree, controller environment PATH/HOME/LANG only:

	flock --exclusive --timeout 3000 /tmp/rnx-runtime-bench.lock python3 probes/execution-cost-0181/events0181.py official results/execution-cost-0181/official1 results/execution-cost-0181/discovery1/availability.json

Exit status 0; report status `COMPLETE`; 76 s; 560 raw rows (140 per group). Admission passed
(reviewed receipt bytes, content, libraries, current host equal to the recorded identity) and the identity was rechecked
before each group. No group-local counter-validity failure occurred. Sentinel scan completed, 0 occurrences.

Reproduction anchors, every group (cycle change and instruction change, candidate against base):

| Workload | 0179 cycles | R | C | D | E | 0179 instructions | R | C | D | E |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| run-numeric | +8.32% | +8.25% | +8.24% | +8.47% | +8.22% | -0.793% | -0.793% | -0.793% | -0.793% | -0.793% |
| run-range_signed | +16.11% | +15.87% | +16.24% | +16.00% | +15.97% | -0.831% | -0.831% | -0.831% | -0.831% | -0.831% |
| run-range_negative | +16.38% | +16.16% | +16.01% | +16.08% | +16.10% | -0.831% | -0.831% | -0.831% | -0.831% | -0.831% |
| run-fib | +2.94% | +2.77% | +2.73% | +2.46% | +2.56% | +2.283% | +2.283% | +2.283% | +2.283% | +2.283% |
| run-calls | +2.72% | +3.13% | +2.59% | +3.30% | +3.09% | +0.452% | +0.452% | +0.452% | +0.452% | +0.452% |
| run-while | +0.22% | +0.04% | +0.04% | +0.09% | -0.08% | -0.783% | -0.783% | -0.783% | -0.783% | -0.783% |
| run-empty | -4.53% | -5.23% | -5.88% | -4.97% | -5.34% | -6.854% | -6.855% | -6.854% | -6.853% | -6.854% |

"Resolved" below is the frozen descriptive rule: all five ABBA paired contrasts with one strict sign AND the pooled
median difference beyond the base p10-p90 width. It is not a confidence interval or a causal test. "Per operation"
divides the difference by the script-bound operation count (1,000,000 iterations or calls; 635,621 fib invocations).

### C: branches

| Workload | Quantity | Base median | Candidate median | Difference | Relative | Per operation | Five paired contrasts | Base p10-p90 width | Frozen rule |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| run-numeric | br_inst_retired_all | 2.96755e+08 | 2.99407e+08 | +2.65209e+06 | +0.89% | +2.652 | +2.652e+06, +2.652e+06, +2.652e+06, +2.652e+06, +2.652e+06 | 377.9 | resolved up |
| run-numeric | br_misp_retired_all | 108520 | 103462 | -5058 | -4.66% | -0.005 | -5474, -4700, -4886, -5182, -4402 | 1168 | resolved down |
| run-numeric | branch_miss_rate | 0.000365689 | 0.000345556 | -2.01327e-05 | -5.51% |  | -2.154e-05, -1.893e-05, -1.955e-05, -2.055e-05, -1.794e-05 | 3.934e-06 | resolved down |
| run-range_signed | br_inst_retired_all | 2.42749e+08 | 2.454e+08 | +2.65074e+06 | +1.09% | +2.651 | +2.651e+06, +2.651e+06, +2.651e+06, +2.651e+06, +2.651e+06 | 390.3 | resolved up |
| run-range_signed | br_misp_retired_all | 106772 | 102780 | -3992 | -3.74% | -0.004 | -3464, -3880, -4116, -3899, -3950 | 1443 | resolved down |
| run-range_signed | branch_miss_rate | 0.000439843 | 0.000418825 | -2.10182e-05 | -4.78% |  | -1.884e-05, -2.056e-05, -2.153e-05, -2.064e-05, -2.085e-05 | 5.945e-06 | resolved down |
| run-range_negative | br_inst_retired_all | 2.42749e+08 | 2.454e+08 | +2.6511e+06 | +1.09% | +2.651 | +2.651e+06, +2.651e+06, +2.651e+06, +2.651e+06, +2.651e+06 | 432.6 | resolved up |
| run-range_negative | br_misp_retired_all | 106606 | 102872 | -3733.5 | -3.50% | -0.004 | -2862, -3691, -3623, -3265, -4407 | 1204 | resolved down |
| run-range_negative | branch_miss_rate | 0.000439159 | 0.000419201 | -1.99581e-05 | -4.54% |  | -1.64e-05, -1.979e-05, -1.95e-05, -1.804e-05, -2.272e-05 | 4.962e-06 | resolved down |
| run-fib | br_inst_retired_all | 1.45287e+08 | 1.44939e+08 | -347928 | -0.24% | -0.547 | -3.48e+05, -3.477e+05, -3.479e+05, -3.479e+05, -3.484e+05 | 451.2 | resolved down |
| run-fib | br_misp_retired_all | 450076 | 456618 | +6543 | +1.45% | +0.010 | +1.12e+04, -6936, +7550, -168, +9178 | 1.106e+04 | unresolved |
| run-fib | branch_miss_rate | 0.00309783 | 0.00315041 | +5.25814e-05 | +1.70% |  | +8.466e-05, -4.038e-05, +5.956e-05, +6.249e-06, +7.075e-05 | 7.614e-05 | unresolved |
| run-calls | br_inst_retired_all | 3.03768e+08 | 3.0342e+08 | -347798 | -0.11% | -0.348 | -3.477e+05, -3.482e+05, -3.477e+05, -3.477e+05, -3.478e+05 | 1084 | resolved down |
| run-calls | br_misp_retired_all | 108802 | 104108 | -4695 | -4.32% | -0.005 | -4530, -4880, -4138, -5202, -4984 | 1642 | resolved down |
| run-calls | branch_miss_rate | 0.000358176 | 0.000343113 | -1.50631e-05 | -4.21% |  | -1.452e-05, -1.567e-05, -1.323e-05, -1.673e-05, -1.602e-05 | 5.405e-06 | resolved down |
| run-while | br_inst_retired_all | 2.02758e+08 | 2.0241e+08 | -347840 | -0.17% | -0.348 | -3.477e+05, -3.48e+05, -3.478e+05, -3.477e+05, -3.478e+05 | 330 | resolved down |
| run-while | br_misp_retired_all | 107607 | 103433 | -4174 | -3.88% | -0.004 | -4507, -4972, -4454, -4065, -3974 | 1527 | resolved down |
| run-while | branch_miss_rate | 0.000530717 | 0.000511008 | -1.97094e-05 | -3.71% |  | -2.135e-05, -2.365e-05, -2.109e-05, -1.917e-05, -1.872e-05 | 7.531e-06 | resolved down |
| run-empty | br_inst_retired_all | 5.42966e+06 | 5.08174e+06 | -347918 | -6.41% |  | -3.479e+05, -3.479e+05, -3.48e+05, -3.481e+05, -3.478e+05 | 285.2 | resolved down |
| run-empty | br_misp_retired_all | 96879 | 92106 | -4773 | -4.93% |  | -5041, -4572, -4632, -4686, -4816 | 1112 | resolved down |
| run-empty | branch_miss_rate | 0.0178425 | 0.0181249 | +0.000282369 | +1.58% |  | +0.0002302, +0.0003161, +0.0003095, +0.0002984, +0.000271 | 0.0002045 | resolved up |

### D: frontend delivery

| Workload | Quantity | Base median | Candidate median | Difference | Relative | Per operation | Five paired contrasts | Base p10-p90 width | Frozen rule |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| run-numeric | idq_dsb_uops | 1.69884e+09 | 1.64255e+09 | -5.6295e+07 | -3.31% | -56.295 | -5.93e+07, -5.789e+07, -5.512e+07, -4.951e+07, -5.695e+07 | 3.989e+06 | resolved down |
| run-numeric | idq_mite_uops | 1.28718e+07 | 1.44273e+08 | +1.31401e+08 | +1020.85% | +131.401 | +1.318e+08, +1.312e+08, +1.306e+08, +1.317e+08, +1.328e+08 | 3.091e+06 | resolved up |
| run-numeric | dsb_share_of_dsb_plus_mite | 0.992476 | 0.919232 | -0.0732446 | -7.38% |  | -0.07358, -0.07316, -0.07272, -0.07312, -0.07403 | 0.001807 | resolved down |
| run-numeric | icache_data_stalls | 1.1352e+06 | 1.5176e+06 | +382391 | +33.68% | +0.382 | +4.018e+05, +3.971e+05, +4.016e+05, +3.458e+05, +3.495e+05 | 2.316e+05 | resolved up |
| run-numeric | icache_stall_cycles_per_cycle | 0.00255126 | 0.00313101 | +0.000579747 | +22.72% |  | +0.0006382, +0.0006766, +0.000638, +0.0005035, +0.0005401 | 0.0003951 | resolved up |
| run-range_signed | idq_dsb_uops | 1.38721e+09 | 1.37854e+09 | -8.67595e+06 | -0.63% | -8.676 | -9.422e+06, -7.347e+06, -4.234e+06, -1.049e+07, -8.043e+06 | 4.097e+06 | resolved down |
| run-range_signed | idq_mite_uops | 1.26508e+07 | 7.01773e+07 | +5.75264e+07 | +454.72% | +57.526 | +5.947e+07, +5.843e+07, +5.648e+07, +5.88e+07, +5.641e+07 | 3.59e+06 | resolved up |
| run-range_signed | dsb_share_of_dsb_plus_mite | 0.990969 | 0.951633 | -0.0393359 | -3.97% |  | -0.04073, -0.03997, -0.03855, -0.04029, -0.03863 | 0.002567 | resolved down |
| run-range_signed | icache_data_stalls | 1.1538e+06 | 1.1138e+06 | -40000.5 | -3.47% | -0.040 | -6.402e+04, +4080, +4060, -3.51e+05, -2.546e+05 | 4.841e+05 | unresolved |
| run-range_signed | icache_stall_cycles_per_cycle | 0.00345866 | 0.00287574 | -0.000582924 | -16.85% |  | -0.0006664, -0.0004597, -0.0004627, -0.001484, -0.001214 | 0.00146 | unresolved |
| run-range_negative | idq_dsb_uops | 1.38672e+09 | 1.37965e+09 | -7.07783e+06 | -0.51% | -7.078 | -6.13e+06, -4.345e+06, -7.975e+06, -9.108e+06, -5.786e+06 | 2.394e+06 | resolved down |
| run-range_negative | idq_mite_uops | 1.35686e+07 | 6.99727e+07 | +5.6404e+07 | +415.69% | +56.404 | +5.836e+07, +5.621e+07, +5.67e+07, +5.611e+07, +5.571e+07 | 3.331e+06 | resolved up |
| run-range_negative | dsb_share_of_dsb_plus_mite | 0.990312 | 0.951684 | -0.0386276 | -3.90% |  | -0.03981, -0.03839, -0.0388, -0.03843, -0.03808 | 0.00237 | resolved down |
| run-range_negative | icache_data_stalls | 1.34047e+06 | 1.1252e+06 | -215270 | -16.06% | -0.215 | -2842, -1.247e+05, -4.089e+05, -8.572e+04, -1.314e+05 | 5.215e+05 | unresolved |
| run-range_negative | icache_stall_cycles_per_cycle | 0.00401229 | 0.00290499 | -0.0011073 | -27.60% |  | -0.0005579, -0.0008526, -0.001693, -0.0007059, -0.0008536 | 0.001552 | unresolved |
| run-fib | idq_dsb_uops | 9.06848e+08 | 9.26084e+08 | +1.92365e+07 | +2.12% | +30.264 | +2.282e+07, +1.846e+07, +1.214e+07, +1.86e+07, +1.903e+07 | 7.517e+06 | resolved up |
| run-fib | idq_mite_uops | 9.67017e+06 | 9.0693e+06 | -600869 | -6.21% | -0.945 | -7.399e+05, -6.022e+05, +8.12e+05, -6.527e+05, -6.443e+05 | 4.638e+05 | unresolved |
| run-fib | dsb_share_of_dsb_plus_mite | 0.989442 | 0.990302 | +0.00086011 | +0.09% |  | +0.001043, +0.0008447, -0.0007289, +0.000901, +0.0008976 | 0.0005625 | unresolved |
| run-fib | icache_data_stalls | 1.10097e+06 | 1.0986e+06 | -2362 | -0.21% | -0.004 | +5497, -4916, -1.362e+04, +8.011e+04, -1193 | 1.057e+05 | unresolved |
| run-fib | icache_stall_cycles_per_cycle | 0.00546832 | 0.00532128 | -0.000147048 | -2.69% |  | -0.0001629, -0.0001573, -0.0002065, +0.0002722, -0.0001364 | 0.0005411 | unresolved |
| run-calls | idq_dsb_uops | 1.70048e+09 | 1.66752e+09 | -3.29548e+07 | -1.94% | -32.955 | -3.106e+07, -3.636e+07, -3.158e+07, -3.416e+07, -3.07e+07 | 4.34e+06 | resolved down |
| run-calls | idq_mite_uops | 1.10861e+07 | 3.40331e+07 | +2.29471e+07 | +206.99% | +22.947 | +2.203e+07, +2.304e+07, +2.319e+07, +2.263e+07, +2.33e+07 | 1.48e+06 | resolved up |
| run-calls | dsb_share_of_dsb_plus_mite | 0.99352 | 0.980018 | -0.013502 | -1.36% |  | -0.01297, -0.01362, -0.01366, -0.01335, -0.0137 | 0.0008604 | resolved down |
| run-calls | icache_data_stalls | 1.12099e+06 | 1.12852e+06 | +7529.5 | +0.67% | +0.008 | -3.522e+04, +1.946e+04, +1.117e+04, +2.405e+04, +1.873e+04 | 8.171e+04 | unresolved |
| run-calls | icache_stall_cycles_per_cycle | 0.00298709 | 0.00290585 | -8.12421e-05 | -2.72% |  | -0.000191, -3.722e-05, -6.793e-05, -2.92e-05, -4.265e-05 | 0.000228 | unresolved |
| run-while | idq_dsb_uops | 1.07874e+09 | 1.0714e+09 | -7.34024e+06 | -0.68% | -7.340 | -1.101e+07, -6.376e+06, -7.47e+06, -8.985e+06, -7.366e+06 | 8.478e+06 | unresolved |
| run-while | idq_mite_uops | 9.38614e+06 | 8.97915e+06 | -406992 | -4.34% | -0.407 | -4.178e+05, -7.587e+05, -4.149e+05, -4.168e+05, -2.229e+05 | 7.622e+05 | unresolved |
| run-while | dsb_share_of_dsb_plus_mite | 0.991378 | 0.991688 | +0.000309939 | +0.03% |  | +0.000296, +0.0006429, +0.000321, +0.0003107, +0.0001457 | 0.0007408 | unresolved |
| run-while | icache_data_stalls | 1.09547e+06 | 1.14056e+06 | +45090.5 | +4.12% | +0.045 | +1.126e+05, -4045, -7401, -2.178e+04, +4.205e+04 | 9.095e+04 | unresolved |
| run-while | icache_stall_cycles_per_cycle | 0.00403668 | 0.00418343 | +0.000146751 | +3.64% |  | +0.0004166, -2.26e-05, -3.058e-05, -8.069e-05, +0.0001434 | 0.0003486 | unresolved |
| run-empty | idq_dsb_uops | 2.59723e+07 | 2.41512e+07 | -1.82114e+06 | -7.01% |  | -1.904e+06, -1.585e+06, -1.679e+06, -1.758e+06, -1.889e+06 | 9.405e+05 | resolved down |
| run-empty | idq_mite_uops | 8.78626e+06 | 8.3795e+06 | -406758 | -4.63% |  | -4.294e+05, -6.833e+05, -4.186e+05, -3.812e+05, -3.972e+05 | 5.175e+05 | unresolved |
| run-empty | dsb_share_of_dsb_plus_mite | 0.747474 | 0.742922 | -0.00455256 | -0.61% |  | -0.004849, +0.002875, -0.0034, -0.004835, -0.005558 | 0.01727 | unresolved |
| run-empty | icache_data_stalls | 904892 | 918888 | +13996 | +1.55% |  | +8727, +2.801e+04, -1.801e+04, -1.194e+04, +7960 | 1.065e+05 | unresolved |
| run-empty | icache_stall_cycles_per_cycle | 0.0720686 | 0.077668 | +0.00559936 | +7.77% |  | +0.005107, +0.007043, +0.001683, +0.002443, +0.005086 | 0.00905 | unresolved |

### E: loads

| Workload | Quantity | Base median | Candidate median | Difference | Relative | Per operation | Five paired contrasts | Base p10-p90 width | Frozen rule |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| run-numeric | mem_load_retired_l1_miss | 77802.5 | 75376.5 | -2426 | -3.12% | -0.002 | -2353, -2074, -1854, -2366, -3740 | 1.858e+04 | unresolved |
| run-numeric | ld_blocks_store_forward | 1.11159e+07 | 1.0904e+07 | -211952 | -1.91% | -0.212 | +2.333e+05, -1.837e+05, -2.123e+05, -2.008e+05, -2.223e+05 | 8.481e+05 | unresolved |
| run-range_signed | mem_load_retired_l1_miss | 77335.5 | 75786 | -1549.5 | -2.00% | -0.002 | -1619, -1842, -1486, -1572, -1151 | 2.036e+04 | unresolved |
| run-range_signed | ld_blocks_store_forward | 9.02713e+06 | 7.03286e+06 | -1.99427e+06 | -22.09% | -1.994 | -1.956e+06, -2.076e+06, -5.64e+05, -1.972e+06, -1.659e+06 | 2.733e+06 | unresolved |
| run-range_negative | mem_load_retired_l1_miss | 77603.5 | 75999 | -1604.5 | -2.07% | -0.002 | -6380, -2454, -1994, +8300, +8614 | 8733 | unresolved |
| run-range_negative | ld_blocks_store_forward | 8.99317e+06 | 7.01588e+06 | -1.97729e+06 | -21.99% | -1.977 | -2.34e+06, -1.992e+06, -1.755e+06, -1.998e+06, -1.988e+06 | 4.998e+05 | resolved down |
| run-fib | mem_load_retired_l1_miss | 77609 | 75808 | -1801 | -2.32% | -0.003 | -2180, +8252, -1880, -2208, +7566 | 1087 | unresolved |
| run-fib | ld_blocks_store_forward | 7.36283e+06 | 6.93384e+06 | -428984 | -5.83% | -0.675 | -4.522e+05, -3.913e+05, -4.424e+05, -4.204e+05, -4.224e+05 | 7.104e+04 | resolved down |
| run-calls | mem_load_retired_l1_miss | 77983 | 75921.5 | -2061.5 | -2.64% | -0.002 | -1926, -1966, -1592, -2266, -2.179e+04 | 2.085e+04 | unresolved |
| run-calls | ld_blocks_store_forward | 1.6768e+07 | 1.52705e+07 | -1.4975e+06 | -8.93% | -1.498 | -1.536e+06, -1.456e+06, -1.659e+06, -1.16e+06, -1.477e+06 | 1.729e+05 | resolved down |
| run-while | mem_load_retired_l1_miss | 77931.5 | 75524.5 | -2407 | -3.09% | -0.002 | -2536, -1900, -2278, -1590, -1.229e+04 | 2.056e+04 | unresolved |
| run-while | ld_blocks_store_forward | 9.08391e+06 | 9.04642e+06 | -37492.5 | -0.41% | -0.037 | -2.342e+04, -3.378e+04, -4.149e+04, -4.296e+04, -4.897e+04 | 1.662e+04 | resolved down |
| run-empty | mem_load_retired_l1_miss | 70104.5 | 68034.5 | -2070 | -2.95% |  | -2079, -1780, -1.701e+04, -1583, +1.316e+04 | 2.991e+04 | unresolved |
| run-empty | ld_blocks_store_forward | 72358.5 | 57647.5 | -14711 | -20.33% |  | -1.537e+04, -1.488e+04, -1.322e+04, -1.385e+04, -1.622e+04 | 3979 | resolved down |

## What the completed groups show

- **Frontend delivery differs where the cycle excess is.** Uops delivered by the legacy decode path (IDQ.MITE_UOPS)
  rise, resolved, on exactly the windows whose cycle excess reproduces: numeric 12.9M to 144.3M, signed range 12.7M to
  70.2M, negative range 13.6M to 70.0M, calls 11.1M to 34.0M. The decoded-uop-cache share of DSB+MITE falls, resolved,
  on the same four: 0.992 to 0.919, 0.991 to 0.952, 0.990 to 0.952, 0.994 to 0.980. On while (cycle change -0.08% to
  +0.09%) and on fib, MITE uops and the DSB share are unresolved; this does not establish equivalence.
- **Branch misprediction does not rise on the Q1 windows.** Retired mispredicted branches and the miss rate resolve
  DOWN for numeric and both ranges (about -3.5% to -5.5%), and for calls and while. Retired branches rise by about 2.65
  per iteration on numeric and the ranges while total instructions fall.
- **These load events do not rise.** Store-forward blocks are lower in the candidate on every window (resolved down for
  negative range, fib, calls, while, run-empty; unresolved for numeric and signed range). L1-miss loads are unresolved
  everywhere, about 2-3% lower.
- **Instruction-cache stall cycles** resolve up only on numeric (+33.7%, 1.14M to 1.52M cycles, which is small beside
  that window's roughly 37M excess cycles); unresolved elsewhere.
- **fib (Q2)** shows no resolved MITE increase or DSB-share decrease; its DSB uops rise 2.1% in step with its 2.28% instruction growth, its
  branch misses are unresolved, and its store-forward blocks fall. These groups add no dynamic attribution of the +33
  instructions per invocation.

## Interpretation and limits

Under plan section 5 a resolved change may support a mechanism CATEGORY compatible with the static differences and the
cycle excess. On that basis:

- The frontend-delivery category is **supported** for Q1: the numeric/range process windows, and to a lesser degree
  calls, show increased legacy-decoder delivery and a lower DSB share of DSB+MITE alongside reproduced excess cycles.
  While has no resolved delivery-share change and near-zero cycle change; fib has no resolved MITE increase or
  DSB-share decrease but still has about +2.5% excess cycles. These whole-process counters do not locate the delivery
  change inside an interpreter loop or establish that it caused the excess cycles.
- The speculation category is **not supported** by group C on the Q1 windows (mispredictions fall), and the two load
  events of group E do **not** show an increase. Neither group excludes every branch or backend cost: other cache
  levels, port pressure and dependency chains were not measured.
- The association is directional, not proportional: numeric has the largest MITE increase (about +131 uops per
  iteration) but a smaller cycle excess (+8.3%) than the ranges (about +57 per iteration, +16%). DSB and MITE counts
  omit other delivery sources and say nothing about the number or cost of switches between them.
- None of this proves that the altered generated code or its placement caused the counter change, identifies a
  particular boundary, loop or instruction, or explains why the compiler emitted different interpreter code for a
  context.rs-only change. 0180's group B remains failed; its top-level frontend-bound fraction is not available to
  corroborate this.
