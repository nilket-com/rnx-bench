#!/usr/bin/env python3
import argparse, json, os, pathlib, shlex, subprocess, tempfile

p = argparse.ArgumentParser()
p.add_argument("--before", required=True)
p.add_argument("--after", required=True)
a = p.parse_args()
root = pathlib.Path(__file__).resolve().parents[2]
results = root / "results/worker-boundary-0046"
env = dict(
    os.environ,
    TERM="xterm-256color",
    RNX_CONFIG="/nonexistent/worker-bench-config",
    NO_COLOR="1",
)
for k in ["RNX_MEMORY_CEILING", "RNX_TEST_WORKER_PAUSE", "RNX_TEST_CONFIG_READS"]:
    env.pop(k, None)
comparisons = {}
for name, args in [
    ("version", ["version"]),
    ("help", ["help"]),
    ("eval", ["eval", "42"]),
    ("run", ["run", str(root / "scripts/bare.rn")]),
    ("json", ["run", str(root / "scripts/json.rn")]),
    ("error", ["eval", "1.missing()"]),
]:
    runs = [
        subprocess.run([b, *args], capture_output=True, env=env)
        for b in (a.before, a.after)
    ]
    assert (runs[0].returncode, runs[0].stdout, runs[0].stderr) == (
        runs[1].returncode,
        runs[1].stdout,
        runs[1].stderr,
    ), name
    comparisons[name] = {
        "exit": runs[0].returncode,
        "stdout_hex": runs[0].stdout.hex(),
        "stderr_hex": runs[0].stderr.hex(),
    }
source = (
    b"let x=41;\nx+1\n:renumber\nfn old(v) { v.missing() }\nold(1)\n:reset\nx\n:q\n"
)
with tempfile.TemporaryDirectory() as tmp:
    sessions = []
    for index, binary in enumerate((a.before, a.after)):
        session_env = dict(env, RNX_HISTORY=str(pathlib.Path(tmp) / str(index)))
        sessions.append(
            subprocess.run(
                [binary, "repl"],
                input=source,
                capture_output=True,
                env=session_env,
                timeout=5,
            )
        )
    assert (sessions[0].returncode, sessions[0].stdout, sessions[0].stderr) == (
        sessions[1].returncode,
        sessions[1].stdout,
        sessions[1].stderr,
    )
    comparisons["session"] = {
        "stdin_hex": source.hex(),
        "exit": sessions[0].returncode,
        "stdout_hex": sessions[0].stdout.hex(),
        "stderr_hex": sessions[0].stderr.hex(),
    }
(results / "equivalence.json").write_text(json.dumps(comparisons, indent=2) + "\n")
cmd = [
    "taskset",
    "-c",
    "4",
    "hyperfine",
    "-N",
    "--warmup",
    "10",
    "--runs",
    "100",
    "--export-json",
    str(results / "startup.json"),
]
for name, args in [
    ("version", ["version"]),
    ("eval", ["eval", "42"]),
    ("run", ["run", str(root / "scripts/bare.rn")]),
    ("json", ["run", str(root / "scripts/json.rn")]),
]:
    for label, b in [("before", a.before), ("after", a.after)]:
        cmd += [
            "--command-name",
            name + " " + label,
            shlex.join([b, *args]),
        ]
subprocess.run(cmd, check=True, env=env)
(results / "binary-sizes.json").write_text(
    json.dumps(
        {
            label: os.stat(b).st_size
            for label, b in [("before", a.before), ("after", a.after)]
        },
        indent=2,
    )
    + "\n"
)
