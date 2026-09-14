#!/usr/bin/env python3
"""Demonstrate interval attribution, explicitly not causal ownership."""

import json, pathlib, sys, time

root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root.parent / "rnx/tests"))
from worker_parent import Parent

binary = str(pathlib.Path(__file__).parent / "target/debug/worker-boundary-probe")
for during_next in [False, True]:
    w = Parent(binary, probe=True)
    try:
        w.begin(op="late")
        w.settled()
        w.handoff()
        if during_next:
            w.begin(op="hold")
            w.settled()
            data = w.handoff()
            assert data["stdout"].data == b"OLD-WRITER"
            assert data["stdout"].identity[1] == 2
            print(
                json.dumps(
                    dict(
                        case="old writer during next interval",
                        collected_as=2,
                        causal_owner=1,
                        limitation="cannot recover causal owner from a shared pipe",
                    )
                )
            )
        else:
            time.sleep(0.4)
            assert w.late["stdout"] == b"OLD-WRITER"
            print(
                json.dumps(
                    dict(
                        case="old writer between intervals",
                        collected_as="unassociated",
                        bytes=len(w.late["stdout"]),
                    )
                )
            )
    finally:
        w.close()
