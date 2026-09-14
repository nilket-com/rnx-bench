# Record 0044 timings

Whole-process elapsed times, startup included. Core 4, 10 warmups, 100 runs.
Output equality and binary hashes are in conditions.json.

| command | mean ms | sigma ms |
| --- | ---: | ---: |
| version before | 0.555 | 0.020 |
| eval before | 4.057 | 0.022 |
| run before | 3.732 | 0.047 |
| json before | 11.595 | 0.121 |
| child before | 4.680 | 0.036 |
| version after | 0.519 | 0.015 |
| eval after | 3.937 | 0.028 |
| run after | 3.588 | 0.018 |
| json after | 11.511 | 0.111 |
| child after | 4.547 | 0.024 |
| facade after | 4.547 | 0.061 |

Final rerun after tests/builds completed. Sequential before/after measurements
include drift and binary-layout effects: the small reductions are not an
attributed speedup. The two child surfaces on the after binary both measured
4.547 ms. Binary grew by 44,592 bytes. The session startup reference was
1,823,240 bytes before and 1,823,136 after; these are allocator request counts,
not resident memory. Build provenance and source hashes are in builds.json.
