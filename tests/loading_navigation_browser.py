"""Composited visible animation while real document GET/POST is pending."""

import importlib.util
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright
from png_pixels import region_digest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "core", ROOT / "dist/python/kagnode_core.py"
)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
HTML = """<!doctype html><html><head><meta charset="utf-8"><style>[hidden]{display:none!important}</style><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><a href="/slow">Open page</a><form method="post" action="/slow"><input name="csrf" value="fixture" type="hidden"><button>Submit</button></form><script>addEventListener('click',e=>{if(e.target.closest('a'))KagNodeLoading.show('Opening page…')});addEventListener('submit',()=>KagNodeLoading.show('Submitting form…'));</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, data, mime="text/html"):
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
        if self.path == "/slow":
            time.sleep(9)
            return self.send(b"<p>Finished</p>")
        self.send(core.inject(HTML, "fixture").encode())

    def do_POST(self):
        assert self.rfile.read(int(self.headers["Content-Length"])) == b"csrf=fixture"
        time.sleep(9)
        self.send(b"<p>Finished</p>")


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": executable} if executable else {})
        )
        rows = []
        for motion in ["no-preference", "reduce"]:
            for method in ["GET", "POST"]:
                context = browser.new_context(
                    viewport={"width": 1000, "height": 800},
                    reduced_motion=motion,
                    color_scheme="light",
                )
                page = context.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}")
                page.wait_for_function(
                    "document.documentElement.dataset.coreReady === 'true'"
                )
                page.evaluate(
                    "()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))"
                )
                session = (
                    context.new_cdp_session(page) if engine == "chromium" else None
                )
                # The committed document and native form semantics own navigation.
                page.evaluate(
                    "document.querySelector('a').click()"
                    if method == "GET"
                    else "document.querySelector('form').requestSubmit()"
                )
                print(engine, motion, method, "pending", page.url, flush=True)
                samples = []
                for _ in range(3):
                    page.wait_for_timeout(370)
                    if engine == "chromium":
                        import base64

                        samples.append(
                            base64.b64decode(
                                session.send(
                                    "Page.captureScreenshot",
                                    {"format": "png", "captureBeyondViewport": False},
                                )["data"]
                            )
                        )
                    else:
                        samples.append(
                            page.screenshot(timeout=3000, animations="allow")
                        )

                energy = [
                    region_digest(data, (440, 310, 560, 425), True) for data in samples
                ]
                if motion == "reduce":
                    assert min(energy) / max(energy) < 0.95, (
                        engine,
                        motion,
                        method,
                        energy,
                    )
                bars = [region_digest(data, (0, 0, 1000, 4)) for data in samples]
                assert (
                    (len(set(bars)) > 1)
                    if motion == "no-preference"
                    else (len(set(bars)) == 1)
                ), (engine, motion, method, "topbar")
                fingerprints = [
                    region_digest(data, (440, 310, 560, 425)) for data in samples
                ]
                assert len(set(fingerprints)) > 1, (engine, motion, method)
                page.wait_for_url("**/slow")
                assert page.locator("p").inner_text() == "Finished"
                rows.append(
                    {
                        "motion": motion,
                        "method": method,
                        "visibleMotion": True,
                        "nativeNavigationCompleted": True,
                    }
                )
                context.close()
        browser.close()
        print(json.dumps({"engine": engine, "cases": rows}))
finally:
    server.shutdown()
