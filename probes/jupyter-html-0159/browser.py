"""rnx 0159: the Polars notebook's HTML tables in a real JupyterLab, light and dark.

	probes/jupyter-notebook/.venv/bin/python probes/jupyter-html-0159/browser.py

Uses the pinned JupyterLab 4.6.3 + Playwright Chromium environment of the 0047 notebook probe,
the kernel and Polars worker built in ../rnx, and a temporary Jupyter environment (the user's
registry is never read or changed). Per theme it opens the committed 04_polars_sales.ipynb as
saved (untrusted: JupyterLab's sanitizer applies), then runs all cells and saves, and requires:
five rendered tables whose DOM text equals the CSV expectations (computed by the notebook
checker's own independent code), no script element in any output, no browser console error,
the theme applied, and every saved execute_result carrying text/plain and text/html.
Writes into results/jupyter-html-0159 (refuses to overwrite)."""
import json, os, pathlib, shutil, socket, subprocess, sys, tempfile, time
import requests
from playwright.sync_api import sync_playwright

BENCH = pathlib.Path(__file__).resolve().parents[2]
RNX = BENCH.parent / "rnx"
VENV = BENCH / "probes/jupyter-notebook/.venv"
OUT = BENCH / "results/jupyter-html-0159"
sys.path.insert(0, str(RNX / "demos/notebooks"))
import check  # the notebook checker: sales_expected, ROWS_SHOWN, HALF

THEMES = {"light": "JupyterLab Light", "dark": "JupyterLab Dark"}
TABLES = "document.querySelectorAll('.jp-OutputArea-output table')"


def log(case, **data):
	line = json.dumps(dict(case=case, **data))
	print(line, flush=True)
	with open(OUT / "journal.jsonl", "a") as f:
		f.write(line + "\n")


def expected_tables():
	"""Each frame's visible table as strings: shape, names, dtypes, rows (head/tail, elided row)."""
	out = []
	for label, height, schema, rows in check.sales_expected(RNX / "demos/data/sales.csv")["frames"]:
		def show(v):
			return ("true" if v else "false") if isinstance(v, bool) else str(v)
		shown = [[show(v) for v in r] for r in rows]
		if height > check.ROWS_SHOWN:
			shown = shown[:check.HALF] + [["…"] * len(schema)] + shown[-check.HALF:]
		out.append({"label": label, "shape": f"shape: ({height}, {len(schema)})",
					"names": [n for n, _ in schema], "dtypes": [d for _, d in schema], "rows": shown})
	return out


DOM = """() => [...document.querySelectorAll('.jp-OutputArea-output')].filter(o => o.querySelector('table')).map(o => {
  const t = o.querySelector('table'), head = [...t.querySelectorAll('thead tr')];
  const td = t.querySelector('tbody td'), cs = td ? getComputedStyle(td) : null;
  return {shape: o.querySelector('small')?.textContent,
		  names: [...head[0].querySelectorAll('th')].map(c => c.textContent),
		  dtypes: [...head[1].querySelectorAll('td')].map(c => c.textContent),
		  rows: [...t.querySelectorAll('tbody tr')].map(r => [...r.querySelectorAll('td')].map(c => c.textContent)),
		  scripts: o.querySelectorAll('script').length,
		  color: cs && cs.color, background: getComputedStyle(document.body).backgroundColor};
})"""


def check_tables(page, want, where):
	got = page.evaluate(DOM)
	assert len(got) == len(want), (where, len(got))
	for g, w in zip(got, want):
		for key in ("shape", "names", "dtypes", "rows"):
			assert g[key] == w[key], (where, w["label"], key, g[key], w[key])
		assert g["scripts"] == 0, (where, w["label"], "script in output")
	assert page.evaluate("document.querySelectorAll('.jp-OutputArea-output script').length") == 0
	return got


def unexpected(console, failed):
	"""Console errors not explained by JupyterLab's own infrastructure. Each allowance is named and
	logged: the debugger panel asks every kernel for a debug session (rnx's kernel has none), and a
	request that failed with 404 is allowed only if it is one of JupyterLab's own optional API
	lookups. Anything else, including any script or sanitizer error, fails the check."""
	allowed_404 = ("/lsp/status",)  # the language-server extension is disabled, as in the 0047 probe
	bad = [c for c in console if c != "No active debugger session"
		   and not c.startswith("Failed to load resource: the server responded with a status of 404")]
	bad += [f for f in failed if f[0] != 404 or not any(a in f[1] for a in allowed_404)]
	return bad


def main():
	OUT.mkdir(parents=True, exist_ok=False)
	temp = tempfile.TemporaryDirectory(prefix="rnx 0159 html ")
	root = pathlib.Path(temp.name)
	bin_ = root / "bin"
	bin_.mkdir()
	kernel, worker = bin_ / "rnx-jupyter", bin_ / "rnx-polars-demo"
	shutil.copy2(RNX / "jupyter/target/release/rnx-jupyter", kernel)
	shutil.copy2(RNX / "demos/polars/target/release/rnx-polars-demo", worker)
	env = {k: v for k, v in os.environ.items()
		   if not k.startswith(("JUPYTER", "IPYTHON", "RNX_", "POLARS_")) and not k.lower().endswith("_proxy")}
	env.update(PATH=str(VENV / "bin") + os.pathsep + env.get("PATH", ""), HOME=str(root),
			   JUPYTER_DATA_DIR=str(root / "data"), JUPYTER_CONFIG_DIR=str(root / "config"),
			   JUPYTER_RUNTIME_DIR=str(root / "runtime"), JUPYTER_PREFER_ENV_PATH="0", PYTHONDONTWRITEBYTECODE="1")
	p = subprocess.run([str(kernel), "install", "--rnx", str(worker)], env=env, capture_output=True, text=True, timeout=30)
	assert p.returncode == 0, p.stderr
	want = expected_tables()
	digest = lambda f: subprocess.run(["sha256sum", str(f)], capture_output=True, text=True).stdout.split()[0]
	log("environment", kernel_sha256=digest(kernel), worker_sha256=digest(worker),
		notebook_sha256=digest(RNX / "demos/notebooks/04_polars_sales.ipynb"), python=sys.version.split()[0])
	for theme, name in THEMES.items():
		work = root / f"work-{theme}"
		(work / "notebooks").mkdir(parents=True)
		(work / "data").mkdir()
		shutil.copy2(RNX / "demos/notebooks/04_polars_sales.ipynb", work / "notebooks")
		shutil.copy2(RNX / "demos/data/sales.csv", work / "data")
		settings = root / f"settings-{theme}/@jupyterlab/apputils-extension"
		settings.mkdir(parents=True)
		(settings / "themes.jupyterlab-settings").write_text(json.dumps({"theme": name}))
		tenv = dict(env, JUPYTERLAB_SETTINGS_DIR=str(root / f"settings-{theme}"))
		with socket.socket() as s:
			s.bind(("127.0.0.1", 0))
			port = s.getsockname()[1]
		url, token = f"http://127.0.0.1:{port}", "rnx-fixture-only"
		server = subprocess.Popen([str(VENV / "bin/jupyter"), "lab", "--no-browser", "--ServerApp.ip=127.0.0.1",
								   f"--ServerApp.port={port}", "--ServerApp.port_retries=0", f"--ServerApp.root_dir={work}",
								   f"--IdentityProvider.token={token}", "--LabApp.expose_app_in_browser=True",
								   "--ServerApp.jpserver_extensions={'jupyter_lsp': False}"],
								  env=tenv, stdin=subprocess.DEVNULL,
								  stdout=open(OUT / f"jupyterlab-{theme}.txt", "w"), stderr=subprocess.STDOUT)
		try:
			end = time.monotonic() + 30
			while True:
				assert server.poll() is None, "JupyterLab exited"
				try:
					if requests.get(url + "/api", params={"token": token}, timeout=.5).ok:
						break
				except requests.RequestException:
					pass
				assert time.monotonic() < end
				time.sleep(.1)
			with sync_playwright() as pw:
				browser = pw.chromium.launch(headless=True)
				page = browser.new_page(viewport={"width": 1440, "height": 2200})
				console, failed = [], []
				page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
				page.on("pageerror", lambda e: console.append(str(e)))
				page.on("response", lambda r: failed.append((r.status, r.url.split("?")[0])) if r.status >= 400 else None)
				page.goto(url + "/lab/tree/notebooks/04_polars_sales.ipynb?token=" + token)
				page.wait_for_function("window.jupyterapp && window.jupyterapp.shell.currentWidget", timeout=60000)
				page.evaluate("async () => { await window.jupyterapp.shell.currentWidget.context.ready; }")
				page.wait_for_function(f"{TABLES}.length === 5", timeout=60000)
				applied = page.evaluate("document.body.dataset.jpThemeName")
				assert applied == name, (applied, name)
				trusted = page.evaluate("window.jupyterapp.shell.currentWidget.content.widgets"
										".filter(c => c.model.type === 'code').map(c => c.model.trusted)")
				# the saved notebook is opened untrusted, so JupyterLab's sanitizer applies
				assert trusted and not any(trusted), (theme, trusted)
				saved = check_tables(page, want, f"{theme}/saved")
				page.screenshot(path=str(OUT / f"saved-{theme}.png"), full_page=True)
				log("saved", theme=theme, applied=applied, tables=len(saved), trusted=trusted,
					cell_colour=saved[0]["color"], page_background=saved[0]["background"])
				page.wait_for_function("window.jupyterapp.shell.currentWidget.sessionContext.session?.kernel?.name === 'rnx'",
									   timeout=60000)
				page.evaluate("async () => { await window.jupyterapp.commands.execute('notebook:clear-all-cell-outputs'); }")
				page.wait_for_function(f"{TABLES}.length === 0")
				page.evaluate("async () => { await window.jupyterapp.commands.execute('notebook:run-all-cells'); }")
				page.wait_for_function("window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.status === 'idle' && "
									   f"{TABLES}.length === 5 && document.body.innerText.includes('Top region: north')",
									   timeout=120000)
				ran = check_tables(page, want, f"{theme}/run")
				page.screenshot(path=str(OUT / f"run-{theme}.png"), full_page=True)
				page.evaluate("async () => { await window.jupyterapp.shell.currentWidget.context.save(); }")
				book = json.loads((work / "notebooks/04_polars_sales.ipynb").read_text())
				bundles = [sorted(o["data"]) for c in book["cells"] for o in c.get("outputs", [])
						   if o["output_type"] == "execute_result"]
				assert bundles == [["text/html", "text/plain"]] * 5, bundles
				log("console", theme=theme, errors=console, failed_requests=failed)
				assert not unexpected(console, failed), (console, failed)
				log("run", theme=theme, tables=len(ran), bundles=bundles, console_errors=len(console),
					cell_colour=ran[0]["color"], page_background=ran[0]["background"], browser=browser.version)
				browser.close()
		finally:
			try:
				requests.post(url + "/api/shutdown", headers={"Authorization": "token " + token}, timeout=5)
			except requests.RequestException:
				pass
			try:
				server.wait(timeout=15)
			except subprocess.TimeoutExpired:
				server.kill()
	temp.cleanup()
	log("passed")


if __name__ == "__main__":
	main()
