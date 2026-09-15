import os, sys, time, json
from pathlib import Path

# Two forks, a new session, and an intermediate parent that exits.
if os.fork():
    time.sleep(30)
    sys.exit(0)
os.setsid()
if os.fork():
    os._exit(0)
tmp = Path(sys.argv[1] + ".tmp")
tmp.write_text(json.dumps({"pid": os.getpid(), "group": os.getpgrp()}))
tmp.replace(sys.argv[1])
time.sleep(30)
