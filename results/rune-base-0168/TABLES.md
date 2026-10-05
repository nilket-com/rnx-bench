# Rune base comparison (0168)

| Whole-process mode | 0.14.2 median ms (min–max) | main median ms (min–max) | main/old |
|---|---:|---:|---:|
| floor | 0.478 (0.465–0.703) | 0.480 (0.461–0.926) | 1.003 |
| empty-context | 0.481 (0.462–0.524) | 0.484 (0.468–0.627) | 1.006 |
| context | 3.412 (3.376–3.472) | 3.643 (3.577–3.729) | 1.068 |
| runtime | 3.626 (3.588–4.261) | 3.892 (3.850–11.053) | 1.073 |
| compile answer | 3.715 (3.663–3.985) | 4.280 (4.212–5.027) | 1.152 |
| run empty | 3.676 (3.634–3.762) | 3.961 (3.921–4.184) | 1.078 |
| run answer | 3.732 (3.692–3.987) | 4.294 (4.247–11.609) | 1.150 |
| run numeric | 83.826 (83.743–85.849) | 125.059 (124.635–150.818) | 1.492 |
| run strings | 14.377 (14.253–14.467) | 19.257 (19.079–19.419) | 1.339 |
| run fib | 38.561 (38.457–39.362) | 53.347 (53.093–53.531) | 1.383 |
| unpinned answer | 10.976 (5.992–13.175) | 12.815 (9.168–14.862) | 1.168 |

Counter windows exclude startup, pipe waiting and teardown; these are separate binaries with allocation accounting disabled.

| Mode | old instructions | main instructions | main/old |
|---|---:|---:|---:|
| context  | 25,318,055 | 26,416,461 | 1.043 |
| runtime  | 26,825,632 | 27,791,637 | 1.036 |
| compile answer | 27,037,195 | 29,450,662 | 1.089 |
| run answer | 27,043,148 | 29,457,250 | 1.089 |
| run numeric | 1,378,164,363 | 1,756,638,881 | 1.275 |
| run strings | 191,619,340 | 227,267,179 | 1.186 |
| run fib | 679,040,402 | 830,599,527 | 1.223 |

All raw values and dispersion are in analysis.json. No samples removed. Unpinned 42 was measured later, separately. These are harnesses, not stock rnx startup measurements.
