# 0069 gate 2: the shared build directory in the product

The product at rnx `118864f` (the gate 2 port), archived and built as the
stock `rnx`; a bare Git origin of that tree with a second revision adding
the 0061 retained-output native; Git-source projects with `shared_build =
true` written by hand (the catalogue writes it only after gate 3).

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 probes/shared-build-product/prepare.py   # ~3 min: stock rnx, and a test-support build for the removal pause hooks
python3 probes/shared-build-product/matrix.py    # ~6 min: the cost matrix, behaviour verified, the seed lock
python3 probes/shared-build-product/contract.py  # ~4 min: refusal, private fallback by omission, concurrency, removal refusal, overrides
python3 probes/shared-build-product/checks.py    # ~8 min
python3 probes/shared-build-product/collect.py
```

Run from the bench root with `probes/shared-build-product/target` and
`results/shared-build-product-0069` absent. Git acquisition runs online
against the file-URL origin, as every first `:dep` does.
