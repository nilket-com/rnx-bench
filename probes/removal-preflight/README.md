# 0066 gate 1: unprivileged mount prerequisite

Run from rnx-bench with rnx alongside it:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 probes/removal-preflight/check.py
```

Prerequisites: Python, Git, util-linux unshare/mount, and an ordinary non-root
user. Preserve preflight.json before rerunning; the driver refuses to overwrite
it. No product binary is built or executed. A private temporary directory is the
only filesystem fixture; it is removed after all children exit.

The driver first proves ordinary execution and then distinguishes user namespace
creation, mount namespace creation and UID mapping. The final child must prove
it has a different mount namespace before issuing any mount command. It makes
propagation private, mounts a small tmpfs and bind-mounts a fixture source, checks
mount records and exits. Mounts must not appear in the parent namespace; the
outside sentinel must remain unchanged. Timeout cleanup kills and waits the
fixture process group. No sudo, privileged retry or host mount is attempted.

The recorded host creates an unmapped user namespace but refuses mount namespace
creation without mapping and rejects both mapped attempts at /proc/self/uid_map.
The mount child never enters. This invokes 0066 gate 1's explicit stop: the nested
and bind mount boundary cannot be exercised unprivileged here. Other ownership,
annotation, rename, resume and deletion cases have not run and are not claimed.

Exit zero means the prerequisite result was recorded and its control assertions
held, not that gate 1 passed. preflight.json always leaves gate1_passed false: even
on a host where mounts work, the actual ownership/filesystem prototype is still
required. product.patch is empty and the two scripts are hashed in the result.
