#!/usr/bin/env python3
"""Browser prerequisite, explicitly not notebook evidence."""
import json
import importlib.metadata
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path(__file__).resolve().parents[2] / "results/jupyter-0047-integration"
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_content('<title>rnx browser preflight</title><p id="gate">Chromium works</p>')
    assert page.locator('#gate').inner_text() == 'Chromium works'
    result = {'playwright': importlib.metadata.version('playwright'),
              'browser': browser.version, 'gate': 'launch, DOM and screenshot',
              'notebook_evidence': False}
    page.screenshot(path=str(out / 'browser-preflight.png'))
    browser.close()
(out / 'browser-preflight.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
