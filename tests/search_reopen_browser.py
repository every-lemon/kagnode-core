"""A queued native close event must not cancel a newly opened search."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = b"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><button data-command>Search</button><div hidden data-core-search-source data-endpoint="/api/search"><a href="/settings">Account settings</a></div><script src="/search.js"></script>"""
requests = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        if self.path == "/search.js":
            data = (ROOT / "web/search.js").read_bytes()
            mime = "text/javascript; charset=utf-8"
        elif self.path.startswith("/api/search"):
            term = parse_qs(urlsplit(self.path).query)["q"][0]
            requests.append(term)
            data = json.dumps(
                {"results": [{"title": term, "url": "/result/" + term}]}
            ).encode()
            mime = "application/json"
        else:
            data, mime = HTML, "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as playwright:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(playwright, engine).launch(
            **({"executable_path": executable} if executable else {})
        )
        rows, errors = [], []
        for width in [390, 768, 1440]:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://127.0.0.1:" + str(server.server_port))
            for cycle in range(3):
                initial = f"initial-{engine}-{width}-{cycle}"
                reopened = f"reopened-{engine}-{width}-{cycle}"
                page.locator("[data-command]").click()
                page.locator("#command-query").fill(initial)
                page.locator(
                    f'.kn-core-search-row[href="/result/{initial}"]'
                ).wait_for()
                page.evaluate(
                    """term=>{document.querySelector('dialog').close();window.KagNodeSearch.open(document.querySelector('[data-command]'));const input=document.querySelector('#command-query');input.value=term;input.dispatchEvent(new Event('input',{bubbles:true}))}""",
                    reopened,
                )
                page.locator(
                    f'.kn-core-search-row[href="/result/{reopened}"]'
                ).wait_for(timeout=5000)
                assert page.locator("#command-query").input_value() == reopened
                assert page.locator("#command-query").evaluate(
                    "e=>e===document.activeElement"
                )
                assert not page.locator("#command-query").get_attribute("aria-busy")
                assert requests.count(reopened) == 1, (
                    "Each reopened intent starts exactly one request"
                )
                page.locator("#command-query").press("Escape")
                page.wait_for_function("()=>!document.querySelector('dialog').open")
                assert page.locator("[data-command]").evaluate(
                    "e=>e===document.activeElement"
                )
            cancelled = f"cancelled-{engine}-{width}"
            page.locator("[data-command]").click()
            page.evaluate(
                """term=>{const input=document.querySelector('#command-query');input.value=term;input.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('dialog').close()}""",
                cancelled,
            )
            page.wait_for_timeout(400)
            assert cancelled not in requests, (
                "Normal close still cancels pending search"
            )
            assert page.locator("[data-command]").evaluate(
                "e=>e===document.activeElement"
            )
            rows.append(
                {
                    "engine": engine,
                    "width": width,
                    "rapidReopenCycles": 3,
                    "newRequestsComplete": True,
                    "normalCloseCancels": True,
                    "focusPreserved": True,
                }
            )
            page.close()
        assert not errors, "Search reopening must not raise browser errors"
        browser.close()
        print(json.dumps({"cases": rows, "errors": errors}))
finally:
    server.shutdown()
    server.server_close()
