#!/usr/bin/env python3
import json, os, pathlib, sys, time

helper = os.getpid()
if len(sys.argv) > 2 and sys.argv[2] == "escape":
    pid = os.fork()
    if pid:
        time.sleep(30)
        sys.exit(0)
    os.setsid()
pathlib.Path(sys.argv[1]).write_text(
    json.dumps(dict(helper=helper, pid=os.getpid(), group=os.getpgrp()))
)
time.sleep(30)
