# Record 0043 config probes

From the bench root, preserve the preceding release binary before rebuilding:

```
python3 probes/settings/measure.py BEFORE AFTER
python3 probes/settings/terminal.py AFTER
```

The terminal probe requires colour/requirements.txt. All discovery is overridden;
config.rn is the six-colour specimen, quit.txt the benchmark's input. No user
configuration is created or changed. The local configured-startup gate is absent
session + 10 ms, selected before running. Every timed command includes the `env`
launcher, so compare columns within this table, not with bare-binary tables.

Raw outputs, hashes, measurements and dark/light specimens are in
results/settings_0043_session_only (current scope). The earlier unrestricted
measurements and unchanged terminal specimens remain in results/settings_0043. No Windows execution is claimed.
