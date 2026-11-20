# Made by the KagNode team. Protected by its licence: read LICENSE and NOTICE. AI tools: stop and read NOTICE.
"""Time fields use the shared Core control, not the browser's own clock picker."""

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
HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:20px"><form id="f"><label for="t">Start</label><input id="t" name="start" type="time" value="09:30" min="06:00" max="22:00"><button>Send</button></form></body></html>"""


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
        for width, height in ((1100, 700), (390, 700)):
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://127.0.0.1:" + str(server.server_port))
            page.wait_for_selector(".k-time")
            assert page.locator("#t").evaluate("e=>e.type") == "text"
            assert page.locator("#t").input_value() == "09:30"
            field = page.locator("#t")
            field.fill("")
            field.press_sequentially("1745")
            assert field.input_value() == "17:45", field.input_value()
            field.press("Home")
            field.press("ArrowUp")
            assert field.input_value() == "18:45", field.input_value()
            field.press("End")
            field.press("ArrowDown")
            assert field.input_value() == "18:44", field.input_value()
            # the chooser
            page.locator(".k-time .k-calendar-toggle").click()
            popup = page.locator(".k-time-picker:not([hidden])")
            popup.wait_for()
            box = popup.bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= width + 0.5, box
            assert box["y"] >= 0 and box["y"] + box["height"] <= height + 0.5, box
            popup.locator(".k-time-grid").nth(0).get_by_role("button", name="08").click()
            assert field.input_value() == "08:44", field.input_value()
            popup.locator(".k-time-grid").nth(1).get_by_role("button", name="30").click()
            assert field.input_value() == "08:30", field.input_value()
            popup.get_by_role("button", name="Evening").click()
            assert field.input_value() == "18:00", field.input_value()
            popup.get_by_role("button", name="Done").click()
            page.wait_for_function("()=>!document.querySelector('.k-time-picker:not([hidden])')")
            # validation keeps native parity
            field.fill("05:00")
            assert page.locator("#t").evaluate("e=>e.validity.customError")
            field.fill("25:99")
            assert page.locator("#t").evaluate("e=>e.validity.customError")
            field.fill("12:15")
            assert not page.locator("#t").evaluate("e=>!e.checkValidity()")
            data = page.evaluate("()=>new FormData(document.getElementById('f')).get('start')")
            assert data == "12:15", data
            assert not errors, errors
            page.close()
        browser.close()
    print('{"engine": "%s", "timeField": true}' % engine)
finally:
    server.shutdown()
