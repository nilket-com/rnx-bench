from common import *
source=(B/'probes/one-command-boundary/vectors.py').read_text()
source=source.replace("V=P/'vectors';V.mkdir(exist_ok=True);exe=T/'schema-tool/target/debug/rnx-project-assembly-probe'", "V=B/'probes/one-command-boundary/vectors';exe=PROBE")
source=source.replace("'scope':'typed document readers only; filesystem truth and Cargo workflow integration are later gates'", "'scope':'accepted gate-1 vectors replayed through product readers'")
(O/'vectors-effective.py').write_text(source)
exec(compile(source,'vectors-effective.py','exec'))
