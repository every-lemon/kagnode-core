"""Keyboard range boundaries preserve an enabled calendar tab stop; no user data."""

import importlib.util
import json
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
HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><main><form id="preview"><label for="date">Preview date</label><input id="date" type="date" min="2026-11-08" max="2026-11-10" value="2026-11-08"><label for="time">Preview time</label><input id="time" type="datetime-local" min="2026-11-08T09:30" max="2026-11-10T17:00" value="2026-11-08T09:30"></form></main></body></html>"""


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
        records, errors = [], []
        for width in [390, 768, 1440]:
            for field in ["date", "time"]:
                page = browser.new_page(viewport={"width": width, "height": 1000})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto("http://127.0.0.1:" + str(server.server_port))
                page.wait_for_function("()=>!!window.KagNodeCore")
                page.evaluate(
                    """()=>{window.__submitted=0;document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();window.__submitted++})}"""
                )
                initial = page.locator("#" + field).input_value()
                page.locator("#" + field).locator("..").locator(
                    ".k-calendar-toggle"
                ).click()
                day = page.locator('[data-date="2026-11-08"]:visible')
                day.focus()

                def assert_stop(expected):
                    state = page.locator(".k-calendar-grid:visible").evaluate(
                        """e=>({focus:document.activeElement.dataset.date,enabled:[...e.querySelectorAll('button')].filter(b=>b.tabIndex===0&&!b.disabled).map(b=>b.dataset.date),disabledStops:[...e.querySelectorAll('button')].filter(b=>b.tabIndex===0&&b.disabled).length})"""
                    )
                    assert state == {
                        "focus": expected,
                        "enabled": [expected],
                        "disabledStops": 0,
                    }, state

                assert_stop("2026-11-08")
                for key in ["ArrowLeft", "ArrowUp"]:
                    page.keyboard.press(key)
                    assert_stop("2026-11-08")
                page.keyboard.press("ArrowRight")
                assert_stop("2026-11-09")
                page.keyboard.press("ArrowRight")
                assert_stop("2026-11-10")
                for key in ["ArrowRight", "ArrowDown"]:
                    page.keyboard.press(key)
                    assert_stop("2026-11-10")
                assert page.locator("#" + field).input_value() == initial
                page.keyboard.press("Enter")
                expected = "2026-11-10" + ("T09:30" if field == "time" else "")
                assert page.locator("#" + field).input_value() == expected
                assert page.locator("#" + field).evaluate("e=>e.checkValidity()")
                if field == "time":
                    page.locator(".k-calendar-done:visible").click()
                page.locator(".k-calendar:visible").wait_for(state="hidden")
                assert (
                    page.locator("#" + field)
                    .locator("..")
                    .locator(".k-calendar-toggle")
                    .evaluate("e=>e===document.activeElement")
                )
                assert page.evaluate("window.__submitted") == 0
                assert page.locator("body").evaluate("e=>e.scrollWidth<=innerWidth+1")
                records.append(
                    {
                        "width": width,
                        "field": field,
                        "boundaryFocus": True,
                        "selection": expected,
                    }
                )
                page.close()
        browser.close()
    assert not errors, errors
    print(json.dumps({"engine": engine, "cases": records, "errors": errors}))
    print("PASS: " + engine + " six keyboard calendar range/selection/focus cases")
finally:
    server.shutdown()
