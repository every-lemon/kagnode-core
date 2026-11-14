"""Controls inherit Core appearance despite conflicting host tokens and layouts."""

import importlib.util
import json
import os
from pathlib import Path
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "core", ROOT / "dist/python/kagnode_core.py"
)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
BODY = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{--panel:#fff;--text:#000;--border:#ddd}input{width:100%;min-height:44px;color:#000;background:#fff}body{margin:0}</style>
</head><body><aside class="sidebar" id="sidebar"><a class="brand">KagNode</a><div data-core-nav-root>
<button class="quick-search" data-core-search-open aria-label="Quick search"><svg viewBox="0 0 24 24"><path d="M4 4h16"/></svg>Quick search<kbd>Ctrl K</kbd></button>
<button data-core-nav-open="settings"><span class="nav-label">Settings</span></button></div>
<div data-core-nav-folder="settings" hidden><button data-core-nav-back>Back</button><a href="#fields">Preferences</a></div></aside>
<div class="workspace"><main id="fields"><h1>Controls</h1><form id="form">
<label for="select">Provider</label><select id="select"><option>Local</option><option>Remote</option></select>
<label for="count">Count</label><input id="count" type="number" min="0" max="10" value="2">
<label><input type="checkbox" name="selection" id="selection">Select item</label>
<label><input type="checkbox" name="enabled" id="enabled" data-core-switch>Enable monitoring</label>
<label><input type="checkbox" id="disabled" data-core-switch disabled>Unavailable</label>
<button type="reset">Reset</button></form></main></div>
<div hidden data-core-search-source><a href="/settings">Settings</a></div></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        asset = core.asset(self.path)
        if asset:
            raw, mime = asset
        else:
            raw = core.inject(BODY, context={"authenticated": False}).encode()
            mime = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        self.wfile.write(raw)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        engine = os.getenv("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.getenv("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            **({"executable_path": executable} if executable else {})
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:" + str(server.server_address[1]))
        page.wait_for_function("!!window.KagNodeControls")
        for theme in ("dark", "light", "dark"):
            page.emulate_media(color_scheme=theme)
            expect(page.locator("html")).to_have_attribute("data-theme", theme)
            for selector in (".k-select", ".k-number", "#selection"):
                actual = page.locator(selector).evaluate(
                    "e=>getComputedStyle(e).backgroundColor"
                )
                expected = (
                    "rgb(16, 16, 16)" if theme == "dark" else "rgb(255, 255, 255)"
                )
                assert actual == expected, (selector, theme, actual)
            assert page.locator("#count").evaluate("e=>getComputedStyle(e).color") == (
                "rgb(241, 241, 243)" if theme == "dark" else "rgb(23, 24, 27)"
            )
            page.locator(".k-select").click()
            expect(page.locator(".k-options")).to_be_visible()
            assert (
                page.locator(".k-options").evaluate(
                    "e=>getComputedStyle(e).backgroundColor"
                )
                == expected
            )
            page.keyboard.press("Escape")
        assert page.locator("#selection").bounding_box()["width"] == 18
        assert page.locator("#selection").bounding_box()["height"] == 18
        expect(page.locator("#enabled")).to_have_attribute("role", "switch")
        page.locator("#enabled").focus()
        page.keyboard.press("Space")
        expect(page.locator("#enabled")).to_be_checked()
        assert (
            page.evaluate(
                "new FormData(document.querySelector('#form')).get('enabled')"
            )
            == "on"
        )
        page.get_by_role("button", name="Reset", exact=True).click()
        expect(page.locator("#enabled")).not_to_be_checked()
        for _ in range(12):
            page.locator('[data-core-nav-open="settings"]').click()
            expect(page.locator('[data-core-nav-folder="settings"]')).to_be_visible()
            page.locator("[data-core-nav-back]").click()
        page.wait_for_function(
            "document.querySelector('[data-core-nav-root]').getAnimations().length === 0"
        )
        page.evaluate("KagNodeCore.navigation.collapse(true)")
        page.mouse.move(1000, 600)
        page.wait_for_timeout(350)
        search = page.locator(".quick-search")
        assert search.bounding_box()["width"] == 38
        assert search.evaluate("e=>getComputedStyle(e).fontSize") == "0px"
        page.evaluate("KagNodeControls.enhance();KagNodeControls.enhance()")
        assert page.locator(".k-number").count() == 1
        assert not errors, errors
        browser.close()
        print(
            json.dumps(
                {
                    "engine": engine,
                    "theme_sync": True,
                    "native_switch_semantics": True,
                    "folder_cycles": 12,
                    "collapsed_search": True,
                }
            )
        )
finally:
    server.shutdown()
