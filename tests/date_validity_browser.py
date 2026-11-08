"""Custom date controls retain native constraint validation and precision."""

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
HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><form id="preview"><label>Date every two days<input id="date" type="date" min="2026-11-08" max="2026-11-12" step="2" value="2026-11-09"></label><label>Time every fifteen minutes<input id="time" type="datetime-local" min="2026-11-08T09:00" max="2026-11-08T10:00" step="900" value="2026-11-08T09:07"></label><label>Seconds<input id="seconds" type="datetime-local" step="30" value="2026-11-08T09:00:30"></label><label>Value-based date interval<input id="origin" type="date" step="2" value="2026-11-09"></label><button type="submit">Submit</button></form><script>window.__native=Object.fromEntries([...document.querySelectorAll('input')].map(e=>[e.id,e.validity.valid]));window.__submitted=0;document.querySelector('form').onsubmit=e=>{e.preventDefault();window.__submitted++};</script></body></html>"""


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
            for field, valid_value, changed_step, initial_valid in [
                ("date", "2026-11-10", "3", False),
                ("time", "2026-11-08T09:15", "1200", False),
                ("seconds", "2026-11-08T09:01", "120", True),
                ("origin", "2026-11-11", "3", True),
            ]:
                page = browser.new_page(viewport={"width": width, "height": 1000})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto("http://127.0.0.1:" + str(server.server_port))
                page.wait_for_function("()=>!!window.KagNodeControls?.core")
                before = page.evaluate("id=>window.__native[id]", field)
                assert before == initial_valid, (
                    "Native fixture validity must match its documented constraint"
                )
                after = page.locator("#" + field).evaluate("e=>e.validity.valid")
                assert after == before, "Enhancement must preserve native date validity"
                page.evaluate(
                    """id=>{for(const e of document.querySelectorAll('#preview input'))e.disabled=e.id!==id;document.querySelector('form').requestSubmit()}""",
                    field,
                )
                assert page.evaluate("window.__submitted") == int(initial_valid), (
                    "Invalid dates must block form submission; valid seconds must submit"
                )
                target = page.locator("#" + field)
                target.fill(valid_value)
                assert target.evaluate("e=>e.validity.valid"), (
                    "Aligned date/time must be accepted"
                )
                step = target.get_attribute("step")
                target.evaluate("(e,step)=>e.setAttribute('step',step)", changed_step)
                page.wait_for_function(
                    "id=>!document.getElementById(id).validity.valid", arg=field
                )
                target.evaluate("(e,step)=>e.setAttribute('step',step)", step)
                page.wait_for_function(
                    "id=>document.getElementById(id).validity.valid", arg=field
                )
                if field == "origin":
                    target.evaluate("e=>e.setAttribute('value','2026-11-10')")
                    page.wait_for_function(
                        "id=>!document.getElementById(id).validity.valid", arg=field
                    )
                    target.evaluate("e=>e.setAttribute('value','2026-11-09')")
                    page.wait_for_function(
                        "id=>document.getElementById(id).validity.valid", arg=field
                    )
                target.fill(
                    "2026-02-30" if field in ["date", "origin"] else "2026-11-08T25:00"
                )
                assert not target.evaluate("e=>e.validity.valid"), (
                    "Impossible date/time must remain invalid"
                )
                target.fill(valid_value)
                assert target.evaluate("e=>e.validity.valid")
                target.evaluate("e=>e.required=true")
                target.fill("")
                assert target.evaluate("e=>e.validity.valueMissing")
                target.evaluate("e=>e.required=false")
                assert target.evaluate("e=>e.validity.valid")
                records.append(
                    {
                        "engine": engine,
                        "width": width,
                        "field": field,
                        "nativeParity": True,
                        "submitValidity": True,
                        "dynamicStep": True,
                        "invalidAndRequired": True,
                    }
                )
                page.close()
        assert not errors, "Date control fixture must not raise browser errors"
        browser.close()
        print(json.dumps({"cases": records, "errors": errors}))
finally:
    server.shutdown()
    server.server_close()
