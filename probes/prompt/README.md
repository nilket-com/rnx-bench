# Record 0042 probes

Before is accepted 0041; preserve its binary. From bench root:

```
python3 probes/prompt/measure.py BEFORE AFTER
python3 probes/prompt/terminal.py AFTER results/prompt_0042
```

The terminal probe reuses colour/terminal.py; install its pinned requirements.
Linux PTYs only. Raw captures, screen assertions and specimens accompany timings.
