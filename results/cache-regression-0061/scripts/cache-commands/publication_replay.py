from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1];O=B/'results/cache-regression-0061/commands/publication-replay';O.mkdir(parents=True,exist_ok=True)
for name in ['build.py','check.py']:
 p=B/'probes/cache-publication'/name
 s=p.read_text().replace("O=B/'results/cache-publication-0061'","O=B/'results/cache-regression-0061/commands/publication-replay'")
 exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
