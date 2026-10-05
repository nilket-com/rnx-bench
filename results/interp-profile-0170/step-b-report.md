# 0170 target-process self samples by symbol family (retired instructions; S2; period 1e6)

Model-based descriptive shares; families named 'mixed' are not exclusive to one operation; Vm::run vs helper moves may be inlining.

## old: share of target instruction samples (%)

| family | numeric | while | fib | calls | compare | vector | strings | answer | empty |
|---|---|---|---|---|---|---|---|---|---|
| vm: Vm::run self | 59.6 | 93.1 | 86.4 | 77.5 | 96.8 | 73.4 | 25.6 | 0.0 | 0.0 |
| vm: comparison helpers | 0.0 | 0.0 | 0.6 | 0.0 | 0.3 | 0.0 | 0.1 | 0.0 | 0.0 |
| vm: call/return/frame helpers | 6.6 | 0.0 | 2.7 | 15.6 | 0.0 | 0.0 | 6.2 | 0.0 | 0.0 |
| vm: range iterator next | 8.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.1 | 0.0 | 0.0 |
| vm: value/AnyObj construction and conversion | 12.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 7.3 | 0.0 | 0.0 |
| vm: Value clone/drop glue and dismantle | 5.1 | 3.3 | 0.3 | 2.1 | 1.0 | 14.4 | 4.1 | 0.0 | 0.0 |
| vm: rune Stack methods | 3.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.1 | 3.4 | 0.0 | 0.0 |
| mixed: Vec<Value> resize/truncate/collect | 0.0 | 0.0 | 5.8 | 2.9 | 0.0 | 0.3 | 3.2 | 0.0 | 0.0 |
| vm: integer conversion/arith helpers | 0.2 | 0.9 | 0.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| vm: other rune::runtime symbols | 0.2 | 0.3 | 0.3 | 0.2 | 0.1 | 9.7 | 11.3 | 9.1 | 9.5 |
| allocator | 3.1 | 0.8 | 1.2 | 0.6 | 0.5 | 0.6 | 21.3 | 28.5 | 29.5 |
| formatting and strings | 0.4 | 0.5 | 0.7 | 0.3 | 0.3 | 0.4 | 9.5 | 14.4 | 13.6 |
| compile::context install/insert | 0.2 | 0.3 | 0.5 | 0.3 | 0.3 | 0.2 | 1.8 | 15.4 | 15.0 |
| mixed: item paths/hashing/maps | 0.5 | 0.7 | 1.1 | 0.5 | 0.4 | 0.7 | 4.1 | 27.3 | 27.7 |
| compiler | 0.0 | 0.0 | 0.1 | 0.0 | 0.1 | 0.1 | 0.3 | 3.7 | 3.2 |
| libc other | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.3 | 1.0 | 1.1 |
| other | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.6 | 0.6 | 0.3 |
| target samples | 20535 | 21169 | 20191 | 22216 | 22995 | 21693 | 20055 | 19683 | 19764 |
| wrapper samples excluded | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 7 | 7 |

## new: share of target instruction samples (%)

| family | numeric | while | fib | calls | compare | vector | strings | answer | empty |
|---|---|---|---|---|---|---|---|---|---|
| vm: Vm::run self | 41.8 | 69.8 | 60.0 | 58.5 | 68.5 | 54.7 | 19.2 | 0.0 | 0.0 |
| vm: comparison helpers | 0.0 | 12.9 | 11.3 | 8.3 | 17.2 | 12.3 | 1.4 | 0.0 | 0.0 |
| vm: call/return/frame helpers | 6.3 | 0.0 | 9.4 | 7.9 | 0.0 | 0.0 | 4.8 | 0.0 | 0.0 |
| vm: range iterator next | 12.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2.5 | 0.0 | 0.0 |
| vm: value/AnyObj construction and conversion | 6.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.4 | 7.4 | 0.0 | 0.0 |
| vm: Value clone/drop glue and dismantle | 12.1 | 9.6 | 10.1 | 8.8 | 8.7 | 18.2 | 11.2 | 0.0 | 0.0 |
| vm: rune Stack methods | 13.9 | 0.0 | 0.3 | 10.0 | 0.0 | 0.3 | 8.4 | 0.0 | 0.0 |
| mixed: Vec<Value> resize/truncate/collect | 0.0 | 0.0 | 4.5 | 3.4 | 0.0 | 0.0 | 1.8 | 0.0 | 0.0 |
| vm: integer conversion/arith helpers | 2.9 | 5.0 | 0.8 | 1.4 | 3.7 | 4.4 | 0.1 | 0.0 | 0.0 |
| vm: other rune::runtime symbols | 0.5 | 0.4 | 0.3 | 0.2 | 0.3 | 7.6 | 11.3 | 7.3 | 6.9 |
| allocator | 2.9 | 0.7 | 1.2 | 0.6 | 0.5 | 0.7 | 15.8 | 29.3 | 32.1 |
| formatting and strings | 0.4 | 0.6 | 0.9 | 0.4 | 0.4 | 0.5 | 10.5 | 27.3 | 27.6 |
| compile::context install/insert | 0.1 | 0.1 | 0.2 | 0.1 | 0.1 | 0.1 | 0.8 | 6.0 | 6.1 |
| mixed: item paths/hashing/maps | 0.5 | 0.9 | 0.9 | 0.5 | 0.5 | 0.7 | 3.7 | 27.6 | 24.4 |
| compiler | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.2 | 0.8 | 0.9 |
| libc other | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.3 | 1.0 | 1.2 |
| other | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.4 | 0.6 | 0.6 |
| target samples | 20977 | 20268 | 22276 | 21120 | 20316 | 23329 | 20162 | 19408 | 19740 |
| wrapper samples excluded | 6 | 6 | 6 | 6 | 6 | 6 | 6 | 7 | 6 |

