"""Actual browser coverage for panels, loading, avatar, sheets and safe summaries."""

import importlib.util
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "core", ROOT / "dist/python/kagnode_core.py"
)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
NOTICE = {
    "available": True,
    "notice": {
        "id": "a" * 64,
        "version": "5.0.7",
        "title": "Clearer controls",
        "items": ["Improved navigation.", "More useful loading messages."],
    },
}
DISMISSED = []
HTML = (
    """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><script>window.noticeReady=false;window.KagNodeWhatsNewHost={ready:()=>noticeReady,headers:async()=>({'X-CSRF-Token':'fixture'})};</script></head><body style="margin:0"><aside id="sidebar" class="sidebar"><a class="brand">KagNode</a><nav>"""
    + "".join('<a href="#content">Navigation ' + str(i) + "</a>" for i in range(75))
    + """</nav></aside><div class="workspace"><header class="topbar"><div class="topbar-right"><button class="avatar" data-kn-account-avatar><img id="photo" src="/logo.svg" width="30" height="30" alt=""></button></div></header><main id="content"><h1>Shared controls</h1><div data-core-panels><div id="segments" data-core-segments data-core-url-param="view" data-core-history="push" aria-label="View"><button data-core-segment="overview">Overview</button><button data-core-segment="activity">Activity</button><button data-core-segment="disabled" disabled>Disabled</button><button data-core-segment="settings">Settings</button></div><section data-core-panel="overview">Overview content</section><section data-core-panel="activity">Activity content</section><section data-core-panel="settings">Settings content</section></div><div data-core-panels><nav id="routes" data-core-segments><a href="/route-a" data-core-segment="a">Route A</a><a href="/route-b" data-core-segment="b">Route B</a></nav></div><button id="sheet-open" data-core-dialog-open="sheet">Open details</button><dialog id="sheet" data-core-sheet aria-label="Details"><h2>Details</h2><button data-core-dismiss>Done</button></dialog><form id="edit"><label for="field">A preference</label><input id="field"><button type="reset">Reset</button></form><div id="inline"></div>"""
    + "".join("<p>Long content " + str(i) + "</p>" for i in range(160))
    + """</main></div></body></html>"""
)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, value, status=200, mime="application/json"):
        raw = (
            value
            if isinstance(value, bytes)
            else (
                json.dumps(value).encode()
                if mime == "application/json"
                else value.encode()
            )
        )
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        asset = core.asset(self.path)
        if asset:
            return self.send(asset[0], mime=asset[1])
        if self.path == "/logo.svg":
            return self.send(
                (ROOT / "assets/mark.svg").read_bytes(), mime="image/svg+xml"
            )
        if self.path == "/api/v1/kagnode-core/whats-new":
            return self.send(NOTICE)
        if self.path.startswith("/api/"):
            return self.send({"error": "Not an administrator"}, 403)
        self.send(
            core.inject(
                HTML,
                "fixture",
                {
                    "authenticated": True,
                    "subject": "user-a",
                    "name": "Example User",
                    "email": "fixture@example.test",
                },
            ),
            mime="text/html",
        )

    def do_POST(self):
        if (
            self.path == "/api/v1/kagnode-core/whats-new/dismiss"
            and self.headers.get("X-CSRF-Token") == "fixture"
        ):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            DISMISSED.append(body)
            return self.send({"dismissed": True})
        self.send({"error": "Denied"}, 403)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
origin = f"http://127.0.0.1:{server.server_port}"
try:
    with sync_playwright() as p:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        exe = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": exe} if exe else {})
        )
        for width in [390, 820, 1440]:
            page = browser.new_page(viewport={"width": width, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(origin + "/?keep=1&view=activity#preserved")
            page.wait_for_function("!!window.KagNodeSegments")
            assert page.locator('[data-core-panel="activity"]').is_visible()
            page.get_by_role("tab", name="Activity", exact=True).focus()
            page.keyboard.press("ArrowRight")
            expect(page.get_by_role("tab", name="Settings", exact=True)).to_be_focused()
            assert (
                "view=settings" in page.url
                and "keep=1" in page.url
                and page.url.endswith("#preserved")
            )
            page.go_back()
            expect(page.locator('[data-core-panel="activity"]')).to_be_visible()
            page.get_by_role("tab", name="Activity", exact=True).focus()
            page.keyboard.press("Home")
            expect(page.get_by_role("tab", name="Overview", exact=True)).to_be_focused()
            page.wait_for_function(
                "()=>{const e=document.querySelector('#segments'),c=e.querySelector('[data-active=true]').getBoundingClientRect(),i=e.querySelector('.kn-core-segment-indicator').getBoundingClientRect();return Math.abs(c.x-i.x)<=1.1&&Math.abs(c.width-i.width)<1}"
            )
            for _ in range(3):
                page.evaluate("KagNodeSegments.refresh()")
            assert page.locator("#segments .kn-core-segment-indicator").count() == 1
            assert page.evaluate(
                """()=>{const link=document.querySelector('#routes a:last-child');let changes=0;const observer=()=>changes++;document.querySelector('#routes').addEventListener('kagnode:segment-change',observer);let allowed=true;for(const modifier of ['ctrlKey','metaKey','shiftKey','altKey']){link.addEventListener('click',e=>{allowed=allowed&&!e.defaultPrevented;e.preventDefault()},{once:true});link.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,[modifier]:true}));}document.querySelector('#routes').removeEventListener('kagnode:segment-change',observer);return allowed&&changes===0}"""
            )
            page.evaluate(
                "document.querySelector('#routes').addEventListener('kagnode:segment-change',e=>{window.routeURL=e.detail.url;e.preventDefault()},{once:true})"
            )
            page.get_by_role("link", name="Route B", exact=True).click()
            assert page.evaluate("routeURL") == "/route-b"
            assert "/route-b" not in page.url
            page.evaluate(
                "window.opA=KagNodeLoading.begin({label:'Opening plan…',mode:'overlay'});window.opB=KagNodeLoading.begin({label:'Fetching activity…',mode:'overlay'});opB.update('Rendering activity…');opA()"
            )
            expect(page.locator("#kn-core-loading")).to_be_visible()
            expect(page.locator(".kn-core-loading-label")).to_have_text(
                "Rendering activity…"
            )
            assert (
                page.locator(".kn-core-spinner-layer").evaluate(
                    "e=>getComputedStyle(e).animationName"
                )
                == "kn-core-orbit"
            )
            page.evaluate("opB();opB()")
            expect(page.locator("#kn-core-loading")).to_be_hidden()
            page.evaluate(
                "()=>{window.inlineOp=KagNodeLoading.begin({label:'Checking…',mode:'inline',target:document.querySelector('#inline')})}"
            )
            assert page.locator("#inline").get_attribute("aria-busy") == "true", (
                page.evaluate(
                    "({html:document.querySelector('#inline').outerHTML,pending:KagNodeLoading.pending})"
                )
            )
            page.evaluate("inlineOp()")
            assert page.locator("#inline").get_attribute("aria-busy") is None
            assert page.locator("[data-core-account-trigger]").count() == 1
            assert (
                page.locator("[data-core-account-trigger]").evaluate(
                    "e=>getComputedStyle(e).borderRadius"
                )
                == "50%"
            ), page.locator("[data-core-account-trigger]").evaluate(
                "e=>({html:e.outerHTML,radius:getComputedStyle(e).borderRadius})"
            )
            page.evaluate(
                "document.dispatchEvent(new CustomEvent('kagnode:avatar-changed',{detail:{subject:'wrong-user',url:'/untrusted.svg'}}))"
            )
            assert "/untrusted.svg" not in page.locator("#photo").get_attribute("src")
            page.evaluate(
                "document.dispatchEvent(new CustomEvent('kagnode:avatar-changed',{detail:{subject:'user-a',url:''}}))"
            )
            expect(page.locator("#photo")).to_be_hidden()
            expect(page.locator(".kn-core-avatar-fallback")).to_be_visible()
            for bar in page.locator(".kn-core-rail").all():
                assert not page.locator(
                    '#sidebar [id="' + str(bar.get_attribute("aria-controls")) + '"]'
                ).count()
            page.locator("#sheet-open").click()
            expect(
                page.get_by_role("dialog", name="Details", exact=True)
            ).to_be_visible()
            page.evaluate(
                "()=>{document.body.append(document.createElement('dialog'));window.modalOp=KagNodeLoading.begin({label:'Reading details…',mode:'overlay'})}"
            )
            assert page.locator("#sheet > #kn-core-loading").count() == 1
            page.evaluate("modalOp()")
            if width <= 700:
                page.wait_for_function(
                    "Math.abs(document.querySelector('#sheet').getBoundingClientRect().bottom-innerHeight)<2"
                )
            page.keyboard.press("Escape")
            expect(page.locator("#sheet")).to_be_hidden()
            assert page.locator("body > #kn-core-loading").count() == 1
            expect(page.locator("#sheet-open")).to_be_focused()
            page.locator("#field").fill("Unsaved work")
            page.evaluate("noticeReady=true;KagNodeWhatsNew.refresh()")
            page.wait_for_timeout(100)
            assert page.get_by_role("dialog", name="What's new").count() == 0
            page.locator("#sheet-open").focus()
            page.evaluate(
                "document.querySelector('#edit').dispatchEvent(new CustomEvent('kagnode:form-saved',{bubbles:true}))"
            )
            expect(page.get_by_role("dialog", name="What's new")).to_be_visible()
            page.get_by_role("button", name="Got it", exact=True).click()
            expect(page.get_by_role("dialog", name="What's new")).to_have_count(0)
            assert DISMISSED[-1] == {"id": "a" * 64}
            page.emulate_media(reduced_motion="reduce")
            page.get_by_role("tab", name="Settings", exact=True).click()
            assert (
                page.locator(".kn-core-segment-indicator").first.evaluate(
                    "e=>getComputedStyle(e).transitionDuration"
                )
                == "0s"
            )
            assert not errors, errors
            page.close()
        browser.close()
finally:
    server.shutdown()
print(
    json.dumps(
        {
            "engine": engine,
            "widths": [390, 820, 1440],
            "segments": True,
            "loadingConcurrency": True,
            "sheets": True,
            "avatar": True,
            "sidebarRailsSuppressed": True,
            "safeSummaries": True,
        }
    )
)
