"""Public wrappers and dedicated sign-in never sit beneath navigation."""

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


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        found = core.asset(self.path)
        if found:
            data, mime = found
        else:
            html = '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body class="site-body" style="margin:0"><header class="site-header">Header</header><div id="main"><h1>Real content wrapper</h1><p>Keep this visible.</p></div><footer class="site-footer">Help</footer></body></html>'
            data = core.inject(html, "public", {"publicNavigation": True}).encode()
            mime = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        self.wfile.write(data)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": executable} if executable else {})
        )
        for width in [390, 1100, 1440]:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto("http://127.0.0.1:" + str(server.server_port))
            page.wait_for_function(
                'document.documentElement.dataset.coreReady==="true"'
            )
            if width >= 1024:
                for collapsed in [True, False, True]:
                    page.evaluate(
                        "value=>KagNodeCore.navigation.collapse(value)", collapsed
                    )
                    page.mouse.move(900, 400)
                    page.wait_for_timeout(500)
                    for selector in ["#main", ".site-header", ".site-footer"]:
                        assert (
                            page.locator(selector).bounding_box()["x"]
                            >= page.locator("#sidebar").bounding_box()["width"] - 1
                        )
                page.locator("#sidebar").hover()
                page.wait_for_timeout(500)
                assert page.locator("#sidebar").bounding_box()["width"] >= 259
                assert page.locator("#main").bounding_box()["x"] >= 259
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
            page.close()
        browser.close()
finally:
    server.shutdown()
print("PASS public content/header/footer footprint and hover expansion")
