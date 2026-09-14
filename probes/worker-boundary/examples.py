#!/usr/bin/env python3
"""Small actual-worker transcript; no terminal transcript parsing."""

import argparse, json, pathlib, sys

root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root.parent / "rnx/tests"))
from worker_parent import Parent

p = argparse.ArgumentParser()
p.add_argument("binary")
args = p.parse_args()
w = Parent(args.binary)
try:
    print(json.dumps(w.ready))
    for source in [
        "let x = 41;",
        "x + 1",
        "fn old(v) { v.missing() }",
        "old(1)",
        'print!("tail"); host::eprint("err")?; ()',
    ]:
        reply, messages, streams = w.execute(source)
        print(
            json.dumps(
                dict(
                    source=source,
                    control=messages,
                    streams={
                        name: dict(
                            hex=s.data.hex(), discarded=s.discarded, id=s.identity[1]
                        )
                        for name, s in streams.items()
                    },
                )
            )
        )
    w.begin(op="reset")
    reply, messages = w.settled()
    w.handoff()
    print(json.dumps(dict(control=messages)))
    w.begin(op="shutdown")
    reply, messages = w.settled()
    w.handoff()
    print(json.dumps(dict(control=messages, exit=w.p.wait(timeout=5))))
finally:
    w.close()
