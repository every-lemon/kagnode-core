"""Notice navigation cancellation and preference actions never affect ordinary clicks."""

import importlib.util
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "core", ROOT / "dist/python/kagnode_core.py"
)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
reads = []
HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><script>window.noticeReady=READY;window.KagNodeWhatsNewHost={ready:()=>noticeReady};</script></head><body data-core-auth-page><main><h1>Local account</h1><button type="button" id="ordinary"><span>Ordinary action</span></button><a id="next" href="/destination">Account</a><a id="partial" href="/destination" onclick="event.preventDefault();this.textContent='Updated locally'">Local view</a><form method="post" action="/destination"><input type="hidden" name="csrf" value="fixture"><button>Continue</button></form><div data-core-preferences-host></div></main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, data, mime="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        asset = core.asset(self.path)
        if asset:
            return self.send(*asset)
        if self.path == "/api/v1/kagnode-core/whats-new":
            reads.append(time.monotonic())
            time.sleep(2)
            return self.send(b'{"available":true,"notice":null}')
        if self.path.startswith("/api/"):
            return self.send(b'{"available":false,"notice":null}')
        ready = self.path.startswith("/source")
        self.send(
            core.inject(
                HTML.replace("READY", "true" if ready else "false"),
                "fixture",
                {
                    "authenticated": True,
                    "subject": "fixture-user",
                    "name": "Fixture User",
                },
            ).encode(),
            "text/html; charset=utf-8",
        )

    def do_POST(self):
        assert self.path == "/destination"
        assert self.rfile.read(int(self.headers["Content-Length"])) == b"csrf=fixture"
        self.send(b"<p>Native submission completed</p>", "text/html; charset=utf-8")


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
origin = f"http://127.0.0.1:{server.server_port}"


def wait_reads(count):
    until = time.monotonic() + 10
    while len(reads) < count and time.monotonic() < until:
        time.sleep(0.01)
    assert len(reads) >= count, (count, len(reads))


try:
    with sync_playwright() as p:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        exe = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": exe} if exe else {})
        )
        rows = []
        for width in [390, 820, 1440]:
            context = browser.new_context(viewport={"width": width, "height": 900})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(origin + "/preferences")
            page.wait_for_function(
                'document.documentElement.dataset.coreReady==="true"'
            )
            assert page.evaluate("Object.keys(localStorage)") == []
            # A legacy root state marker must never become an action control.
            page.evaluate("document.documentElement.dataset.coreScrollMode='custom'")
            page.locator("#ordinary span").click()
            page.locator("#ordinary").focus()
            page.keyboard.press("Enter")
            assert page.evaluate("Object.keys(localStorage)") == []
            assert page.locator("html").get_attribute("aria-pressed") is None
            page.locator("button[data-core-scroll-mode=native]").click()
            assert (
                page.evaluate("localStorage.getItem('kagnode.scrollMode')") == "native"
            )
            page.locator("button[data-core-scroll-mode=custom]").click()
            assert (
                page.evaluate("localStorage.getItem('kagnode.scrollMode')") == "custom"
            )
            for method in ["GET", "POST"]:
                before = len(reads)
                page.goto(origin + "/source")
                wait_reads(before + 1)
                if method == "GET":
                    page.locator("#next").click()
                else:
                    page.get_by_role("button", name="Continue", exact=True).click()
                page.wait_for_url("**/destination")
                if method == "POST":
                    expect(page.locator("p")).to_have_text(
                        "Native submission completed"
                    )
                else:
                    expect(page.locator("h1")).to_have_text("Local account")
            before = len(reads)
            page.goto(origin + "/source")
            wait_reads(before + 1)
            page.locator("#partial").click()
            wait_reads(before + 2)
            assert page.url.endswith("/source")
            before = len(reads)
            page.goto(origin + "/preferences")
            page.evaluate(
                "()=>{window.operation=KagNodeLoading.begin({mode:'topbar',label:'Opening local view…'});noticeReady=true;KagNodeWhatsNew.refresh()}"
            )
            page.wait_for_timeout(150)
            assert len(reads) == before
            page.evaluate("operation()")
            wait_reads(before + 1)
            page.evaluate(
                "dispatchEvent(new PageTransitionEvent('pagehide'));KagNodeWhatsNew.refresh()"
            )
            before = len(reads)
            page.wait_for_timeout(100)
            assert len(reads) == before
            page.evaluate(
                "dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))"
            )
            wait_reads(before + 1)
            page.goto(origin + "/destination")
            assert not errors, errors
            context.close()
            rows.append(
                {
                    "width": width,
                    "ordinaryClickNoStorage": True,
                    "explicitPreferencesPersist": True,
                    "nativeGetPost": True,
                    "cancelledPartialResumes": True,
                    "loadingDefersReads": True,
                    "pagehideResume": True,
                }
            )
        browser.close()
        print(json.dumps({"engine": engine, "cases": rows}))
finally:
    server.shutdown()
