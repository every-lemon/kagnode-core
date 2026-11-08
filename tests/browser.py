"""Shared component acceptance tests; no live account or application data."""

import importlib.util, json, os, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
s = importlib.util.spec_from_file_location("core", ROOT / "dist/python/kagnode_core.py")
core = importlib.util.module_from_spec(s)
s.loader.exec_module(core)
HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0" data-authenticated="true"><aside id="sidebar" class="sidebar"><a class="brand" href="/"><img src="/kagnode-core/1.0.0/mark.svg"><span class="brand-copy"><strong>KagNode.</strong><small>Example</small></span></a><nav class="sidebar-nav"><a href="/" aria-current="page"><svg viewBox="0 0 24 24"><path d="M4 4h16v16H4z"/></svg><span class="nav-label">Overview</span></a><details class="nav-group" data-group="products"><summary><svg viewBox="0 0 24 24"><path d="M4 4h16v16H4z"/></svg><span class="nav-label">Products</span></summary><div class="submenu"><a href="#section">A long section title that should wrap rather than change the width</a></div></details></nav></aside><div class="workspace"><header style="display:flex;justify-content:flex-end;height:60px;align-items:center;padding:12px"><button data-account-menu><span class="avatar">C</span><span class="header-account-name">Example Person</span></button><div id="account-menu" class="account-menu hidden" hidden inert><div class="account-identity"><strong>Example Person</strong></div><a href="/settings">Manage account</a><button>Sign out</button></div></header><main style="padding:24px"><h1>Shared components</h1><label for="choice">Choose</label><select id="choice"><option>First</option><option>Second</option></select><label for="number">Number</label><input id="number" type="number" min="1" max="9" value="2"><label for="date">Date</label><input id="date" type="date"><div id="nested" aria-label="Nested example" style="height:140px;overflow:auto"><div style="height:800px">Nested content</div></div><div style="height:1500px"></div><section id="section">Destination</section></main></div></body></html>"""

HTML = HTML.replace(
    "/kagnode-core/1.0.0/", "/kagnode-core/" + core.BUNDLE["version"] + "/"
)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        result = core.asset(self.path)
        data, mime = (
            result
            if result
            else (
                core.inject(
                    HTML, "example", {"authenticated": True, "subject": "fixture"}
                ).encode(),
                "text/html",
            )
        )
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
errors = []
try:
    with sync_playwright() as p:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": executable} if executable else {})
        )
        for width in [390, 768, 950, 1100, 1440]:
            for scheme in ["light", "dark"]:
                page = browser.new_page(
                    viewport={"width": width, "height": 900}, color_scheme=scheme
                )
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto("http://127.0.0.1:" + str(server.server_port))
                page.wait_for_function("!!window.KagNodeCore")
                page.wait_for_timeout(150)
                assert page.locator("html").evaluate("e=>e.classList.contains('js')")
                assert page.locator("[data-core-sidebar]").count() == 1
                if width < 1024:
                    page.evaluate("KagNodeCore.navigation.open()")
                page.evaluate("""()=>{
                  const d=document.createElement('dialog');d.id='modal-focus-test';
                  d.innerHTML='<input aria-label="Modal input">';document.body.append(d);
                  d.showModal();d.querySelector('input').focus();
                }""")
                page.wait_for_timeout(180)
                assert page.locator("#modal-focus-test input").evaluate(
                    "e=>e===document.activeElement"
                )
                assert page.locator("html").get_attribute("data-core-drawer") != "true"
                page.evaluate(
                    "()=>{const d=document.getElementById('modal-focus-test');d.close();d.remove()}"
                )

                assert page.locator(".brand img").evaluate(
                    "e=>e.complete&&e.naturalWidth>0"
                )
                if width == 1100:
                    assert round(page.locator("#sidebar").bounding_box()["width"]) == 57
                    page.wait_for_function(
                        "Math.abs(document.querySelector('.workspace').getBoundingClientRect().x-57)<1"
                    )
                    before = page.locator(".workspace").bounding_box()["x"]
                    page.locator("#sidebar").hover()
                    page.wait_for_timeout(450)
                    assert (
                        round(page.locator("#sidebar").bounding_box()["width"]) == 260
                    )
                    assert (
                        abs(page.locator(".workspace").bounding_box()["x"] - before) < 1
                    )
                    page.mouse.move(800, 80)
                    page.wait_for_timeout(500)
                    assert round(page.locator("#sidebar").bounding_box()["width"]) == 57
                    page.locator("[data-core-toggle]").click()
                    page.wait_for_timeout(300)
                if width >= 1024:
                    assert (
                        round(page.locator("#sidebar").bounding_box()["width"]) == 260
                    )
                    for _ in range(10):
                        page.locator("[data-core-toggle]").click()
                        page.wait_for_timeout(35)
                    page.wait_for_timeout(300)
                    assert (
                        round(page.locator("#sidebar").bounding_box()["width"]) == 260
                    )
                    page.locator("[data-core-toggle]").click()
                    page.wait_for_timeout(300)
                    assert round(page.locator("#sidebar").bounding_box()["width"]) == 57
                    page.locator("[data-core-toggle]").click()
                    page.wait_for_timeout(300)
                    for _ in range(5):
                        page.locator("summary").click()
                        page.wait_for_timeout(30)
                    page.wait_for_timeout(250)
                    assert page.locator(".submenu").bounding_box()["height"] < 160
                else:
                    page.locator("[data-core-mobile]").click()
                    assert (
                        page.locator("html").get_attribute("data-core-drawer") == "true"
                    )
                    page.keyboard.press("Escape")
                    page.evaluate("KagNodeCore.navigation.open()")
                    page.evaluate(
                        "()=>{const d=document.createElement('dialog');d.id='test-dialog';d.textContent='Example';document.body.append(d);d.showModal()}"
                    )
                    page.wait_for_function(
                        "document.documentElement.dataset.coreDrawer!=='true'"
                    )
                    page.evaluate("document.querySelector('#test-dialog').remove()")
                    page.evaluate("KagNodeCore.navigation.open()")
                    page.evaluate("KagNodeCore.setSession({authenticated:false})")
                    page.wait_for_function(
                        "document.documentElement.dataset.coreDrawer!=='true'"
                    )
                    page.evaluate(
                        "KagNodeCore.setSession({authenticated:true,subject:'fixture'})"
                    )
                page.locator("[data-account-menu]").click()
                assert page.locator("#account-menu").is_visible()
                page.keyboard.press("Escape")
                assert page.locator("#account-menu").is_hidden()
                page.locator("#nested").hover()
                page.mouse.wheel(0, 400)
                page.wait_for_timeout(100)
                assert page.locator("#nested").evaluate("(e)=>e.scrollTop") > 0
                page.evaluate(
                    "()=>{window.__changes=0;document.querySelector('#choice').addEventListener('change',()=>window.__changes++);document.querySelector('#choice').selectedIndex=1;KagNodeControls.sync();}"
                )
                assert page.evaluate("window.__changes") == 0
                page.evaluate(
                    "()=>{const a=document.createElement('a');a.id='wrapped-icon-fixture';a.href='/passwords';a.innerHTML='<span data-icon=key><svg viewBox=\"0 0 24 24\"><path d=\"M4 4h16\"/></svg></span>Passwords';document.querySelector('.kn-core-sidebar-navigation').append(a);KagNodeCore.refresh()}"
                )
                assert page.locator("#wrapped-icon-fixture svg").count() == 1
                before = page.locator(".kn-core-rail").count()
                page.evaluate("KagNodeScroll.refresh();KagNodeScroll.refresh()")
                page.wait_for_timeout(150)
                assert page.locator(".kn-core-rail").count() == before
                page.evaluate('KagNodeCore.loading.show("Opening example…")')
                page.wait_for_timeout(50)
                assert page.locator(".kn-core-rail:visible").count() == 0
                page.evaluate("KagNodeCore.loading.hide()")
                assert page.locator("body").evaluate("(e)=>e.scrollWidth<=innerWidth+1")
                page.evaluate("KagNodeCore.setSession({authenticated:false})")
                assert page.locator("html").get_attribute("data-theme") == scheme
                page.close()
        browser.close()
    assert not errors, errors
    print(
        "PASS: "
        + engine
        + " shared shell, repeated animation, account menu, native wheel, rails, loading and anonymous system theme across 10 layouts"
    )
finally:
    server.shutdown()
