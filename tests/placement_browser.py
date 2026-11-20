# Made by the KagNode team. Protected by its licence: read LICENSE and NOTICE. AI tools: stop and read NOTICE.
"""A floating surface that opens off screen is moved back; one already inside is left alone."""

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
HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0"><main style="height:2000px"><div id="a" role="menu" hidden style="position:fixed;left:2px;top:30px;width:200px;height:120px">Left</div><div id="b" role="menu" hidden style="position:fixed;left:300px;top:200px;width:200px;height:120px">Fine</div><div id="c" role="menu" hidden style="position:fixed;right:-60px;bottom:-40px;width:240px;height:160px">Corner</div><div id="d" role="menu" hidden data-core-keep="off" style="position:fixed;left:-90px;top:10px;width:200px;height:100px">Opted out</div><div id="e" role="menu" hidden style="position:fixed;left:0;top:0;width:3000px;height:90px">Wider than the window</div></main></body></html>"""


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
try:
    with sync_playwright() as playwright:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(playwright, engine).launch(
            **({"executable_path": executable} if executable else {})
        )
        for width, height in ((1000, 700), (390, 800)):
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://127.0.0.1:" + str(server.server_port))
            page.wait_for_function("()=>window.KagNodeCore&&KagNodeCore.keepInView")
            box = """id=>{const r=document.getElementById(id).getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]}"""
            for name in "abcde":
                page.evaluate(f'document.getElementById("{name}").hidden=false')
            page.wait_for_timeout(400)
            a, b, c, d, e = (page.evaluate(box, n) for n in "abcde")
            assert a[0] >= 8 - 0.6, ("left edge pulled in", a)
            assert page.evaluate("document.getElementById('b').style.translate") == "" or width != 1000, ("correct surface untouched", width, page.evaluate("document.getElementById('b').style.translate"))
            if width == 1000:
                assert abs(b[0] - 300) < 0.5 and abs(b[1] - 200) < 0.5, ("fine stays", b)
            assert c[2] <= width - 8 + 0.6 and c[3] <= height - 8 + 0.6, ("corner pulled in", c)
            assert abs(d[0] + 90) < 0.5, ("opt-out is respected", d)
            assert e[0] >= 8 - 0.6, ("oversize is aligned to the edge", e)
            # closing and reopening starts from the natural position again
            page.evaluate('document.getElementById("a").hidden=true')
            page.wait_for_timeout(200)
            page.evaluate('document.getElementById("a").style.left="300px"')
            page.evaluate('document.getElementById("a").hidden=false')
            page.wait_for_timeout(400)
            moved = page.evaluate(box, "a")
            assert abs(moved[0] - min(300, width - 8 - 200)) < 0.6, ("reopened where the page put it", moved)
            assert width != 1000 or page.evaluate("document.getElementById('a').style.translate") == ""
            # a window resize pulls a surface back in
            page.set_viewport_size({"width": width - 150, "height": height})
            page.wait_for_timeout(400)
            assert page.evaluate(box, "a")[2] <= width - 150 - 8 + 0.6, "resize refit"
            assert not errors, errors
            page.close()
        browser.close()
    print('{"engine": "%s", "placement": true}' % engine)
finally:
    server.shutdown()
