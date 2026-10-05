# Redaction of captured environments

`run4/measure.json` and `diag-aa/diag_aa.json` recorded the controller's full environment, as the 0172 amendment required. That environment contained a session credential and network details. In this version of the files, each environment value outside a fixed allowlist is replaced with `<redacted: N bytes>`.

- **Allowlist:** PATH, HOME, LANG, TERM, SHELL, USER, LOGNAME, PWD, OLDPWD, XDG_RUNTIME_DIR, COLORTERM, SHLVL, _, XDG_SESSION_CLASS, XDG_SESSION_TYPE, XDG_DATA_DIRS, LS_COLORS, LESSOPEN, LESSCLOSE, GIT_EDITOR, IM_CONFIG_ENTRY, DEBUGINFOD_URLS, BUN_INSTALL, COREPACK_ENABLE_AUTO_PIN, NoDefaultCurrentDirectoryInExePath, AI_AGENT, CLAUDECODE, CLAUDE_EFFORT.
- **What's kept:** every key and every value's byte length. No measured value was changed.
- **Producers:** `measure.py` and `diag_aa.py` are unchanged; they're the producers that ran. Later probes redact at capture time.
