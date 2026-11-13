"""Real keyboard browsing and automatic tracking; no application/user data."""

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
links = "".join(f'<a href="#s{i}">Heading {i}</a>' for i in range(20))
sections = "".join(
    f'<section style="height:800px"><h2 id="s{i}">Heading {i}</h2></section>'
    for i in range(20)
)
HTML = f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>#toc{{position:fixed;right:20px;top:40px;width:240px}}#list{{position:relative;height:160px;overflow:auto}}#list>a{{display:block;min-height:32px}}main{{padding:100px 300px 0 20px}}#start{{position:fixed;top:0;left:0}}</style></head><body><button id="start">Start keyboard navigation</button><nav id="toc" data-core-toc><div id="list" data-core-toc-links>{links}</div></nav><main>{sections}</main></body></html>"""


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
        errors = []
        records = []
        for motion in ["reduce", "no-preference"]:
            page = browser.new_page(
                viewport={"width": 1440, "height": 1000}, reduced_motion=motion
            )
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://127.0.0.1:" + str(server.server_port))
            page.wait_for_function('()=>document.querySelector("#list").tabIndex===0')
            page.locator("#start").focus()
            page.keyboard.press("Tab")
            assert page.locator("#list").evaluate(
                'e=>e===document.activeElement&&e.matches(":focus-visible")'
            )
            page.keyboard.press("PageDown")
            page.wait_for_function('()=>document.querySelector("#list").scrollTop>30')
            page.wait_for_timeout(400)
            before = page.locator("#list").evaluate("e=>e.scrollTop")
            assert page.evaluate("()=>scrollY") == 0
            page.evaluate(
                """()=>{const list=document.querySelector('#list');const a=document.createElement('a');a.href='#s20';a.textContent='New heading';list.append(a);const invalid=document.createElement('a');invalid.href='#%GG';invalid.textContent='Malformed target';list.append(invalid);const section=document.createElement('section');section.innerHTML='<h2 id="s20">New heading</h2>';document.querySelector('main').append(section)}"""
            )
            page.wait_for_timeout(500)
            assert abs(page.locator("#list").evaluate("e=>e.scrollTop") - before) < 2
            assert page.locator("#list [aria-current]").get_attribute("href") == "#s0"
            # Keyboard focus on an anchor also keeps deliberate list browsing.
            for _ in range(9):
                page.keyboard.press("Tab")
            focused = page.evaluate("()=>document.activeElement.getAttribute('href')")
            assert focused == "#s8"
            page.wait_for_timeout(400)
            before_anchor = page.locator("#list").evaluate("e=>e.scrollTop")
            page.evaluate(
                """()=>{const a=document.createElement('a');a.href='#s19';a.textContent='Another entry';document.querySelector('#list').append(a)}"""
            )
            page.wait_for_timeout(500)
            assert (
                abs(page.locator("#list").evaluate("e=>e.scrollTop") - before_anchor)
                < 2
            )
            assert (
                page.evaluate("()=>document.activeElement.getAttribute('href')")
                == focused
            )
            # Tracking resumes when focus leaves the list and the page advances.
            page.locator("#start").focus()
            page.evaluate(
                "()=>window.scrollTo(0,document.getElementById('s12').getBoundingClientRect().top+scrollY-70)"
            )
            page.wait_for_function(
                '()=>document.querySelector("#list [aria-current]")?.getAttribute("href")==="#s12"'
            )
            page.wait_for_timeout(500)
            distance = page.locator("#list").evaluate(
                """e=>{const a=e.querySelector('[aria-current]').getBoundingClientRect(),b=e.getBoundingClientRect();return Math.abs((a.top+a.height/2)-(b.top+b.height/2))}"""
            )
            assert distance < 3, distance
            assert page.locator("#list .plan-toc-indicator").count() == 1
            # A wheel gesture keeps the user's chosen list position while new
            # content or page movement changes the current heading.
            page.evaluate(
                """()=>{const list=document.querySelector('#list');list.dispatchEvent(new WheelEvent('wheel',{deltaY:20,bubbles:true}));list.scrollTop=90;window.scrollTo(0,document.getElementById('s15').getBoundingClientRect().top+scrollY-70);KagNodeToc.refresh()}"""
            )
            page.wait_for_timeout(120)
            assert abs(page.locator("#list").evaluate("e=>e.scrollTop") - 90) < 2
            page.evaluate(
                "document.querySelector('#list').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));dispatchEvent(new PointerEvent('pointercancel'));document.querySelector('#list').scrollTop=0"
            )
            page.wait_for_timeout(850)
            page.evaluate(
                "window.scrollTo(0,document.getElementById('s17').getBoundingClientRect().top+scrollY-70)"
            )
            page.wait_for_function(
                "()=>document.querySelector('#list [aria-current]')?.hash==='#s17'&&document.querySelector('#list').scrollTop>300"
            )
            records.append(
                {
                    "engine": engine,
                    "motion": motion,
                    "container": True,
                    "anchor": True,
                    "automaticTracking": True,
                }
            )
            page.close()
        assert not errors, errors
        browser.close()
        print("PASS:", json.dumps(records))
finally:
    server.shutdown()
