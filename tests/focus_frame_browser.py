# Made by the KagNode team. Protected by its licence: read LICENSE and NOTICE. AI tools: stop and read NOTICE.
"""Text fields, text areas and selects use the same focus frame as the date field."""

import importlib.util
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "core", ROOT / "dist/python/kagnode_core.py"
)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:20px"><label>Name <input id="text" type="text"></label><label>Note <textarea id="area"></textarea></label><label>Kind <select id="pick"><option>One</option><option>Two</option></select></label><label>Day <input id="day" type="date"></label><label>Count <input id="count" type="number"></label><label><input id="box" type="checkbox"> Box</label></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        result = core.asset(self.path)
        data, mime = (
            result if result else (core.inject(HTML, "fixture").encode(), "text/html")
        )
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        self.wfile.write(data)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
FRAME = """e=>{const s=getComputedStyle(e);return [s.borderTopColor,s.boxShadow,s.outlineStyle]}"""
try:
    with sync_playwright() as playwright:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(playwright, engine).launch(
            **({"executable_path": executable} if executable else {})
        )
        for scheme in ("light", "dark"):
            page = browser.new_page(color_scheme=scheme)
            page.goto("http://127.0.0.1:" + str(server.server_port))
            page.wait_for_function("()=>document.querySelector('.k-date')")
            page.evaluate("document.querySelector('.k-date input').focus()")
            page.wait_for_timeout(300)
            reference = page.locator(".k-date").evaluate(FRAME)
            assert reference[1] != "none", reference
            for selector in ("#text", "#area", ".k-select"):
                target = page.locator(selector).first
                target.focus()
                page.wait_for_timeout(300)
                border, shadow, outline = target.evaluate(FRAME)
                assert (border, shadow) == (reference[0], reference[1]), (
                    scheme,
                    selector,
                    (border, shadow),
                    reference,
                )
                assert outline in ("none", ""), (selector, outline)
            page.close()
        browser.close()
    print('{"engine": "%s", "focusFrame": true}' % engine)
finally:
    server.shutdown()
