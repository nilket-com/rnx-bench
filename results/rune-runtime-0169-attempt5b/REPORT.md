# Standing runtime baseline (0169)

| Subject | Mode / workload | Median ms | p10–p90 ms |
|---|---|---:|---:|
| lua54 | run answer | 0.436 | 0.409–0.457 |
| lua54 | run empty | 0.419 | 0.396–0.438 |
| lua54 | run fib | 9.529 | 9.484–9.682 |
| lua54 | run numeric | 6.350 | 6.317–6.365 |
| lua54 | run strings | 4.775 | 4.755–4.816 |
| lua54 | unpinned answer | 1.545 | 1.402–1.859 |
| luajit | run answer | 0.464 | 0.437–0.494 |
| luajit | run empty | 0.459 | 0.429–0.479 |
| luajit | run fib | 1.614 | 1.518–1.649 |
| luajit | run numeric | 8.334 | 8.292–8.379 |
| luajit | run strings | 3.130 | 3.112–3.138 |
| luajit | unpinned answer | 1.603 | 1.491–1.680 |
| new | compile answer | 4.264 | 4.227–4.326 |
| new | context  | 3.634 | 3.604–3.684 |
| new | empty-context  | 0.510 | 0.481–0.525 |
| new | floor  | 0.505 | 0.474–0.522 |
| new | run answer | 4.275 | 4.236–4.354 |
| new | run empty | 3.956 | 3.916–4.010 |
| new | run fib | 55.565 | 55.356–56.102 |
| new | run numeric | 124.841 | 124.260–125.555 |
| new | run strings | 19.240 | 19.158–19.343 |
| new | runtime  | 3.881 | 3.845–3.927 |
| new | unpinned answer | 5.994 | 5.504–13.489 |
| old | compile answer | 3.727 | 3.685–3.774 |
| old | context  | 3.406 | 3.375–3.462 |
| old | empty-context  | 0.507 | 0.476–0.532 |
| old | floor  | 0.504 | 0.476–0.533 |
| old | run answer | 3.746 | 3.696–3.803 |
| old | run empty | 3.686 | 3.649–3.734 |
| old | run fib | 38.791 | 38.722–39.053 |
| old | run numeric | 84.374 | 84.000–84.846 |
| old | run strings | 14.382 | 14.306–14.448 |
| old | runtime  | 3.625 | 3.602–3.664 |
| old | unpinned answer | 9.674 | 5.353–12.874 |
| stock | eval literal-42 | 4.173 | 4.119–4.286 |
| stock | run answer | 3.855 | 3.805–3.932 |
| stock | run empty | 3.799 | 3.748–3.877 |
| stock | run fib | 37.685 | 37.536–37.944 |
| stock | run numeric | 90.597 | 90.501–91.028 |
| stock | run strings | 15.538 | 15.427–15.779 |
| stock | unpinned literal-42 | 12.643 | 9.903–13.622 |

## Complete registration diagnostic: stdio=False

| Module (construction + install, paired) | Median ms |
|---|---:|
| iter | 0.501 |
| ops | 0.476 |
| string | 0.186 |
| collections::hash_set | 0.182 |
| collections::hash_map | 0.138 |
| object | 0.116 |
| option | 0.082 |
| collections::vec_deque | 0.079 |
| f64 | 0.060 |
| ops::generator | 0.054 |

| Install stage (summed across modules per context) | Median ms |
|---|---:|
| trait_impls | 1.505 |
| associated | 0.281 |
| types | 0.095 |
| items | 0.050 |
| traits | 0.032 |
| module | 0.027 |
| reexports | 0.003 |
| construct | 0.001 |

## Complete registration diagnostic: stdio=True

| Module (construction + install, paired) | Median ms |
|---|---:|
| iter | 0.504 |
| ops | 0.477 |
| string | 0.188 |
| collections::hash_set | 0.184 |
| collections::hash_map | 0.140 |
| object | 0.117 |
| option | 0.083 |
| collections::vec_deque | 0.080 |
| f64 | 0.061 |
| ops::generator | 0.054 |

| Install stage (summed across modules per context) | Median ms |
|---|---:|
| trait_impls | 1.503 |
| associated | 0.296 |
| types | 0.096 |
| items | 0.052 |
| traits | 0.032 |
| module | 0.027 |
| reexports | 0.003 |
| construct | 0.001 |

Diagnostic timings are separate, with complete module/stage hierarchy and overhead in JSON. Nested event counts do not add to parent event counts. No optimization chosen.
