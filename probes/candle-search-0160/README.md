# rnx 0160: the independent search reference

`reference.py` makes `demos/data/search-reference.json` in rnx: sentence-transformers on
PyTorch (CPU) ranks every bundled help article for every bundled question, from the same CSV
bytes and the same pinned all-MiniLM-L6-v2 files that `06_candle_search` uses. Its docstring
gives the exact method; the output records every input's SHA-256, the model revision, the method
and the environment versions, and the notebook checker refuses a reference whose provenance
doesn't match its inputs.

```sh
python3 -m venv probes/candle-search-0160/.venv
probes/candle-search-0160/.venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1
probes/candle-search-0160/.venv/bin/pip install -r probes/candle-search-0160/requirements.txt
(cd ../rnx && sh demos/candle/fetch-model.sh)
probes/candle-search-0160/.venv/bin/python probes/candle-search-0160/reference.py OUT.json
```

The articles and questions are an authored showcase corpus, not a held-out relevance benchmark.
