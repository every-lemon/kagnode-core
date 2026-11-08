"""Quick-search intent races and IME behavior in actual browser engines."""

import json
import os
from pathlib import Path
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = b"""<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><button data-command>Search</button><div hidden data-core-search-source data-endpoint="/api/search"><a href="/settings">Account settings</a></div><script src="/search.js"></script>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        from urllib.parse import parse_qs, urlsplit

        if self.path == "/search.js":
            data = (ROOT / "web/search.js").read_bytes()
            mime = "text/javascript"
        elif self.path.startswith("/api/search"):
            term = parse_qs(urlsplit(self.path).query)["q"][0]
            data = json.dumps(
                {"results": [{"title": term, "url": "/result/" + term}]}
            ).encode()
            mime = "application/json"
        else:
            data, mime = HTML, "text/html"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
failures = []
try:
    with sync_playwright() as p:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": executable} if executable else {})
        )
        for width in [390, 1440]:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.goto(f"http://127.0.0.1:{server.server_port}/")
            page.locator("[data-command]").click()
            field = page.locator("#command-query")
            field.fill("alpha")
            page.locator('.kn-core-search-row[href="/result/alpha"]').wait_for()
            field.press("ArrowDown")
            state = page.evaluate(
                """()=>{const i=document.querySelector('#command-query');i.value='beta';i.dispatchEvent(new Event('input',{bubbles:true}));return {active:i.getAttribute('aria-activedescendant'),rows:document.querySelectorAll('.kn-core-search-row').length,more:document.querySelector('.kn-core-search-footer a').getAttribute('href')}}"""
            )
            if state != {"active": None, "rows": 0, "more": "/search?q=beta"}:
                failures.append(f"{engine}/{width}: stale input intent: {state}")
            with page.expect_navigation():
                field.press("Enter")
            if not page.url.endswith("/search?q=beta"):
                failures.append(
                    f"{engine}/{width}: Enter navigated to old query: {page.url}"
                )
            page.locator("[data-command]").click()
            field = page.locator("#command-query")
            field.dispatch_event(
                "keydown", {"key": "Escape", "isComposing": True, "bubbles": True}
            )
            if not page.locator("#command-palette").evaluate("(e)=>e.open"):
                failures.append(f"{engine}/{width}: IME Escape closed search")
            page.close()

            page = browser.new_page(viewport={"width": width, "height": 900})
            page.add_init_script(
                """(()=>{window.__deadlines=[];window.__requests=[];const timeout=window.setTimeout;window.setTimeout=(f,ms,...args)=>ms===8000?(window.__deadlines.push(f),900000+window.__deadlines.length):timeout(f,ms,...args);window.fetch=(url,options)=>new Promise(resolve=>window.__requests.push({url:String(url),signal:options.signal,resolve}));})();"""
            )
            page.goto(f"http://127.0.0.1:{server.server_port}/")
            page.locator("[data-command]").click()
            field = page.locator("#command-query")
            field.fill("alpha")
            page.wait_for_function("window.__requests.length===1")
            field.fill("beta")
            page.wait_for_function("window.__requests.length===2")
            state = page.evaluate(
                """()=>{window.__deadlines[0]();return {old:window.__requests[0].signal.aborted,current:window.__requests[1].signal.aborted}}"""
            )
            if state != {"old": True, "current": False}:
                failures.append(
                    f"{engine}/{width}: old deadline aborted newer request: {state}"
                )
            page.evaluate(
                """()=>window.__requests[1].resolve({ok:true,headers:new Headers({'Content-Type':'application/json'}),json:async()=>({results:[{title:'beta','url':'/result/beta'}]})})"""
            )
            page.locator('.kn-core-search-row[href="/result/beta"]').wait_for()
            page.evaluate(
                """()=>window.__requests[0].resolve({ok:true,headers:new Headers({'Content-Type':'application/json'}),json:async()=>({results:[{title:'alpha','url':'/result/alpha'}]})})"""
            )
            page.wait_for_timeout(30)
            if page.locator('.kn-core-search-row[href="/result/alpha"]').count():
                failures.append(
                    f"{engine}/{width}: old response replaced newer results"
                )
            page.close()
        browser.close()
finally:
    server.shutdown()
assert not failures, "\n".join(failures)
print(
    f"{engine}: quick-search intent, IME, timeout ownership and stale response checks passed at 2 widths"
)
