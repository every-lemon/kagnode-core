"""Actual Core policy controls: channel and mode remain independent."""

import importlib.util
import json
import os
from pathlib import Path
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
s = importlib.util.spec_from_file_location("core", ROOT / "dist/python/kagnode_core.py")
core = importlib.util.module_from_spec(s)
s.loader.exec_module(core)
state = {
    "enabled": True,
    "version": "5.0.10",
    "channel": "stable",
    "automatic": False,
    "capabilities": {"release_channels": True},
    "candidate": None,
}
requests = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, value, mime="application/json"):
        raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        result = core.asset(self.path)
        if result:
            return self.send(result[0], result[1])
        if self.path == "/api/v1/kagnode-core/status":
            return self.send(state)
        if self.path.startswith("/api/"):
            return self.send({"available": False, "notice": None})
        html = '<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><main><input type="hidden" name="_csrf" value="fixture"><h1>Settings</h1><section data-core-admin-host></section></main></body></html>'
        self.send(
            core.inject(
                html, "fixture", {"authenticated": True, "subject": "fixture"}
            ).encode(),
            "text/html",
        )

    def do_POST(self):
        assert self.path == "/api/v1/kagnode-core/policy"
        assert self.headers.get("X-CSRF-Token") == "fixture"
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        requests.append(body)
        state.update(body)
        self.send(state)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        name = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        options = {"headless": True}
        if os.environ.get("KAGNODE_BROWSER_EXECUTABLE"):
            options["executable_path"] = os.environ["KAGNODE_BROWSER_EXECUTABLE"]
        if name == "chromium":
            options["args"] = ["--no-sandbox"]
        browser = getattr(p, name).launch(**options)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("http://127.0.0.1:" + str(server.server_address[1]))
        select = page.locator('select[aria-label="Core release channel"]')
        expect(select).to_have_value("stable")
        select.select_option("beta", force=True)
        expect(page.locator('select[aria-label="Core release channel"]')).to_have_value(
            "beta"
        )
        assert state["automatic"] is False
        page.get_by_role("button", name="Enable automatic patches", exact=True).click()
        expect(
            page.get_by_role("button", name="Pause automatic patches", exact=True)
        ).to_be_visible()
        assert state["channel"] == "beta"
        assert len(requests) == 2 and not errors
        assert page.locator("[data-core-updates-panel]").count() == 1
        browser.close()
        print(
            json.dumps(
                {
                    "engine": name,
                    "channel": "beta",
                    "automatic": True,
                    "independent_controls": True,
                    "errors": 0,
                }
            )
        )
finally:
    server.shutdown()
