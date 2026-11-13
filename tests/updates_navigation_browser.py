"""Real reload during both Core status read stages; mutations never replay."""

import importlib.util
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "core", ROOT / "dist/python/kagnode_core.py"
)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
records = {}
HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body data-core-auth-page data-kn-account-app="APP"><main><h1>Local settings</h1><a id="next" href="/destination">Leave settings</a><div data-core-admin-host></div></main><script>window.reauthStarted=0;window.KagNodeCoreHost={reauthenticate:()=>{reauthStarted++;return new Promise(resolve=>window.finishReauth=resolve)}};</script></body></html>"""
STATUS = {
    "enabled": True,
    "version": "5.0.8",
    "automatic": True,
    "candidate": {"version": "5.0.9", "changed": True, "release_id": 9},
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def key(self):
        cookies = dict(
            x.strip().split("=", 1)
            for x in self.headers.get("Cookie", "").split(";")
            if "=" in x
        )
        return cookies.get("case", "default")

    def send(self, data, status=200, mime="application/json", cookie=None):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        if cookie:
            self.send_header("Set-Cookie", "case=" + cookie + "; Path=/; SameSite=Lax")
        self.end_headers()
        try:
            self.wfile.write(
                data if isinstance(data, bytes) else json.dumps(data).encode()
            )
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        asset = core.asset(self.path)
        if asset:
            return self.send(asset[0], mime=asset[1])
        if self.path.startswith("/settings"):
            key = parse_qs(urlsplit(self.path).query)["case"][0]
            records.setdefault(key, {"csrf": 0, "status": 0, "post": []})
            app = "mail" if key.startswith("mail") else "authenticator"
            return self.send(
                core.inject(
                    HTML.replace("APP", app),
                    "fixture",
                    {"authenticated": True, "subject": "fixture-user"},
                ).encode(),
                mime="text/html; charset=utf-8",
                cookie=key,
            )
        if self.path == "/destination":
            return self.send(b"<p>Left settings</p>", mime="text/html")
        key = self.key()
        record = records[key]
        if self.path in ["/api/status", "/api/session"]:
            record["csrf"] += 1
            if "-csrf-" in key:
                time.sleep(1)
            return self.send({"csrf": "fixture"})
        if self.path == "/api/v1/kagnode-core/status":
            record["status"] += 1
            if "-status-" in key:
                time.sleep(1)
            return self.send(STATUS)
        return self.send({"available": False, "notice": None})

    def do_POST(self):
        key = self.key()
        record = records[key]
        action = self.path.rsplit("/", 1)[-1]
        assert self.headers.get("X-CSRF-Token") == "fixture"
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        record["post"].append(action)
        if "-reauth-" in key:
            return self.send(
                {"code": "reauth_required", "error": "Local approval required"}, 403
            )
        time.sleep(1)
        return self.send(STATUS)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
origin = f"http://127.0.0.1:{server.server_port}"


def wait_count(key, field, count):
    until = time.monotonic() + 10
    while (
        len(records[key][field]) if field == "post" else records[key][field]
    ) < count and time.monotonic() < until:
        time.sleep(0.01)
    assert (
        len(records[key][field]) if field == "post" else records[key][field]
    ) >= count, (key, field, records[key])


try:
    with sync_playwright() as p:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        exe = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": exe} if exe else {})
        )
        rows = []
        for width in [390, 820, 1440]:
            for app in ["authenticator", "mail"]:
                for stage in ["csrf", "status"]:
                    key = f"{app}-{stage}-{width}"
                    context = browser.new_context(
                        viewport={"width": width, "height": 900}
                    )
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto(origin + "/settings?case=" + key)
                    wait_count(key, stage, 1)
                    # Actual browser reload while that exact read stage is pending.
                    page.reload()
                    wait_count(key, stage, 2)
                    expect(
                        page.get_by_role("button", name="Check for updates", exact=True)
                    ).to_be_visible()
                    assert records[key]["post"] == []
                    assert not errors, (key, errors)
                    context.close()
                    rows.append(
                        {
                            "app": app,
                            "stage": stage,
                            "width": width,
                            "realReload": True,
                            "noMutations": True,
                        }
                    )
            for action in ["check", "apply"]:
                key = f"authenticator-{action}-{width}"
                context = browser.new_context(viewport={"width": width, "height": 900})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(origin + "/settings?case=" + key)
                if action == "check":
                    page.get_by_role(
                        "button", name="Check for updates", exact=True
                    ).click()
                else:
                    page.get_by_role("button", name="Install 5.0.9", exact=True).click()
                    page.get_by_role("button", name="Continue", exact=True).click()
                wait_count(key, "post", 1)
                page.reload()
                expect(
                    page.get_by_role("button", name="Check for updates", exact=True)
                ).to_be_visible()
                page.evaluate(
                    "dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}));dispatchEvent(new Event('focus'));document.dispatchEvent(new Event('kagnode:account-ready'))"
                )
                page.wait_for_timeout(1200)
                assert records[key]["post"] == [action], records[key]
                assert not errors, (key, errors)
                context.close()
                rows.append(
                    {
                        "action": action,
                        "width": width,
                        "interruptedMutationNotReplayed": True,
                    }
                )
        key = "authenticator-reauth-1440"
        context = browser.new_context()
        page = context.new_page()
        page.goto(origin + "/settings?case=" + key)
        page.get_by_role("button", name="Check for updates", exact=True).click()
        page.wait_for_function("reauthStarted===1")
        page.evaluate(
            "document.dispatchEvent(new Event('kagnode:core-session'));finishReauth()"
        )
        page.wait_for_timeout(1200)
        assert records[key]["post"] == ["check"], records[key]
        context.close()
        browser.close()
        print(
            json.dumps(
                {
                    "engine": engine,
                    "cases": rows,
                    "sessionChangeStopsReauthReplay": True,
                }
            )
        )
finally:
    server.shutdown()
