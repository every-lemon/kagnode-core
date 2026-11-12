"""Progressive native forms and browser-return protocol using fictional local hosts."""

import importlib.util
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "core", ROOT / "dist/python/kagnode_core.py"
)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
CALLS = []
POSTS = []

FORM = """<form action="/local" method="post" data-core-login-progressive>
<input type="hidden" name="csrf" value="fictional-csrf">
<div class="kn-core-login-field"><label for="identity">Email</label><input id="identity" type="email" name="email" autocomplete="username" required></div>
<div class="kn-core-login-field"><label for="password">Password</label><div class="kn-core-login-secret"><input id="password" type="password" name="password" autocomplete="current-password" required><button type="button" aria-label="Show password"><span data-core-icon="eye"></span></button></div></div>
<button type="submit">Sign in locally</button></form>"""
HOST = """<script>
window.completed=[];window.calls=[];window.ready=false;
window.fixtureReady=()=>{window.ready=true;KagNodeLogin.refresh()};
window.KagNodeLoginHost={issuer:'https://nebulacoder.com',state:()=>({enabled:true,ready:window.ready}),
request:async(action,data)=>{calls.push({action,data});const result=await fetch('/api/'+action+'?case='+new URL(location.href).searchParams.get('case'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).then(r=>r.json());if(action==='status'&&window.holdStatus)return await new Promise(resolve=>window.resolveStatus=()=>resolve(result));return result},
complete:async(result)=>{completed.push(result)}};
document.addEventListener('DOMContentLoaded',()=>KagNodeLogin.refresh());
</script>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, content, mime="text/html"):
        data = content.encode() if isinstance(content, str) else content
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        asset = core.asset(path)
        if asset:
            return self.send(*asset)
        form = FORM
        if path == "/key":
            form = '<form data-core-login-progressive><label for="key">Administrator key</label><input id="key" type="password" autocomplete="current-password"><button>Sign in</button></form>'
        elif path == "/combined":
            form = FORM.replace(
                '<div class="kn-core-login-field"><label for="password">',
                '<div data-core-login-credentials><div class="kn-core-login-field"><label for="password">',
            ).replace(
                '<button type="submit">Sign in locally</button>',
                '<div class="kn-core-login-field"><label for="otp">Verification code</label><input id="otp" name="code" autocomplete="one-time-code" required></div></div><button type="submit">Sign in locally</button>',
            )
        elif path == "/mfa":
            form = '<form><label for="otp">Verification code</label><input id="otp" autocomplete="one-time-code"><button>Verify</button></form>'
        elif path == "/confirmation":
            form = FORM.replace(
                '<button type="submit">Sign in locally</button>',
                '<label for="confirm">Confirm password</label><input id="confirm" type="password" autocomplete="new-password" disabled hidden><button type="submit">Sign in locally</button>',
            )
        elif path == "/new-password":
            form = FORM.replace(
                'autocomplete="current-password"', 'autocomplete="new-password"'
            )
        login = core.render_template(
            "login-frame",
            {
                "product": "KagNode Example",
                "heading": "Sign in",
                "description": "Use your existing account.",
                "content": form,
                "provider": '<button type="button" data-core-login-provider>Login with KagNode</button><p data-core-login-status role="status"></p>',
            },
        )
        html = (
            '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><script>window.headURL=location.href</script></head><body data-core-auth-page>'
            + login
            + HOST
            + "</body></html>"
        )
        self.send(core.inject(html, "fixture", {"authenticated": False}))

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        path = urlparse(self.path)
        case = parse_qs(path.query).get("case", [""])[0]
        if path.path == "/local":
            POSTS.append(parse_qs(body))
            return self.send("Local credentials received")
        action = path.path.rsplit("/", 1)[-1]
        CALLS.append({"case": case, "action": action, "data": json.loads(body)})
        if action == "start":
            target = {
                "unsafe": "https://elsewhere.example/authorize",
                "http": "http://nebulacoder.com/authorize",
                "userinfo": "https://user@nebulacoder.com/authorize",
                "fragment": "https://nebulacoder.com/authorize#fragment",
            }.get(case, "https://nebulacoder.com/authorize?state=fictional")
            result = {
                "pending": True,
                "attempt_id": "fictional-local-attempt",
                "authorization_uri": target,
                "expires_in": 600,
            }
        elif action == "status":
            result = {
                "authorized": case != "denied",
                "pending": False,
                "continuation": "local-unlock",
            }
        else:
            result = {"cancelled": True}
        self.send(json.dumps(result), "application/json")


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
origin = f"http://127.0.0.1:{server.server_port}"
try:
    with sync_playwright() as p:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": executable} if executable else {})
        )
        for width in [390, 820, 1440]:
            page = browser.new_page(viewport={"width": width, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/login")
            expect(page.locator("#identity")).to_be_visible()
            expect(page.locator("#password")).to_be_hidden()
            page.get_by_role("button", name="Continue", exact=True).click()
            expect(page.locator("#password")).to_be_hidden()
            assert not POSTS
            page.locator("#identity").fill("fictional@example.test")
            page.locator("#identity").press("Enter")
            expect(page.locator("#password")).to_be_focused()
            expect(page.locator(".kn-core-login-identity")).to_contain_text(
                "fictional@example.test"
            )
            page.get_by_role("button", name="Change sign-in identity").click()
            expect(page.locator("#identity")).to_be_focused()
            page.get_by_role("button", name="Continue", exact=True).click()
            page.locator("#password").fill("fictional-password")
            assert page.locator('input[name="csrf"]').input_value() == "fictional-csrf"
            assert not page.locator("#password").is_disabled()
            assert (
                page.locator("#password").get_attribute("autocomplete")
                == "current-password"
            )
            page.locator("#password").press("Enter")
            page.wait_for_url("**/local")
            assert POSTS[-1] == {
                "csrf": ["fictional-csrf"],
                "email": ["fictional@example.test"],
                "password": ["fictional-password"],
            }
            POSTS.clear()
            page.goto(origin + "/login")
            page.evaluate(
                """()=>{document.querySelector('#identity').value='autofill@example.test';document.querySelector('#password').value='fictional-autofill';document.querySelector('form').requestSubmit()}"""
            )
            page.wait_for_url("**/local")
            assert POSTS[-1]["password"] == ["fictional-autofill"]
            POSTS.clear()
            page.goto(origin + "/login")
            page.evaluate(
                """()=>{const i=document.querySelector('#identity');i.value='linked@example.test';i.readOnly=true;KagNodeLogin.refresh()}"""
            )
            expect(page.locator("#password")).to_be_visible()
            expect(
                page.get_by_role("button", name="Change sign-in identity")
            ).to_be_hidden()
            assert page.evaluate(
                "KagNodeLogin.advance(document.querySelector('form'),{focus:true})"
            )
            expect(page.locator("#password")).to_be_focused()
            page.evaluate(
                """()=>{document.querySelector('#password').autocomplete='new-password';KagNodeLogin.refresh()}"""
            )
            expect(page.locator("#identity")).to_be_visible()
            expect(page.locator("#password")).to_be_visible()
            assert page.get_by_role("button", name="Continue", exact=True).count() == 0
            for _ in range(3):
                page.evaluate(
                    """()=>{document.querySelector('#identity').readOnly=false;document.querySelector('#password').autocomplete='current-password';KagNodeLogin.refresh()}"""
                )
                assert (
                    page.get_by_role("button", name="Continue", exact=True).count() == 1
                )
                page.evaluate(
                    """()=>{document.querySelector('#password').autocomplete='new-password';KagNodeLogin.refresh()}"""
                )
            assert not page.locator("form").evaluate("e=>e.noValidate")
            page.goto(origin + "/confirmation")
            expect(page.locator("#password")).to_be_hidden()
            assert page.get_by_role("button", name="Continue", exact=True).count() == 1
            page.evaluate(
                """()=>{document.querySelector('#confirm').disabled=false;KagNodeLogin.refresh()}"""
            )
            expect(page.locator("#identity")).to_be_visible()
            expect(page.locator("#password")).to_be_visible()
            assert page.get_by_role("button", name="Continue", exact=True).count() == 0
            page.goto(origin + "/combined")
            expect(page.locator("#password")).to_be_hidden()
            expect(page.locator("#otp")).to_be_hidden()
            page.locator("#identity").fill("fictional@example.test")
            page.get_by_role("button", name="Continue", exact=True).click()
            expect(page.locator("#password")).to_be_visible()
            expect(page.locator("#otp")).to_be_visible()
            page.locator("#password").fill("fictional-password")
            page.locator("#otp").fill("123456")
            page.get_by_role("button", name="Sign in locally").click()
            page.wait_for_url("**/local")
            assert POSTS[-1]["code"] == ["123456"]
            POSTS.clear()
            for path, field in [
                ("/key", "#key"),
                ("/mfa", "#otp"),
                ("/new-password", "#password"),
            ]:
                page.goto(origin + path)
                expect(page.locator(field)).to_be_visible()
                assert (
                    page.get_by_role("button", name="Continue", exact=True).count() == 0
                )
            page.emulate_media(reduced_motion="reduce")
            page.goto(origin + "/login")
            page.locator("#identity").fill("fictional@example.test")
            page.get_by_role("button", name="Continue", exact=True).click()
            assert (
                page.locator(".kn-core-login-card").evaluate(
                    "e=>getComputedStyle(e).animationName"
                )
                == "none"
            )
            assert (
                page.locator("#password").evaluate(
                    "e=>e.parentElement.parentElement.getAnimations().length"
                )
                == 0
            )
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
            assert not errors, errors
            page.close()
        page = browser.new_page()
        page.route(
            "https://nebulacoder.com/**",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html",
                body=f"<script>location.replace({json.dumps(origin + '/login?case=redirect&keep=1&kagnode_attempt=fictional-local-attempt#preserved')})</script>",
            ),
        )
        page.goto(origin + "/login?case=redirect")
        page.evaluate("fixtureReady()")
        page.get_by_role("button", name="Login with KagNode").click()
        page.wait_for_url("**/*keep=1#preserved")
        page.wait_for_function(
            "typeof window.fixtureReady==='function'&&location.hash==='#preserved'"
        )
        assert "kagnode_attempt" not in page.url
        assert "kagnode_attempt" not in page.evaluate("window.headURL")
        assert "keep=1" in page.url and page.url.endswith("#preserved")
        assert len(page.context.pages) == 1
        assert not any(
            x["case"] == "redirect" and x["action"] == "cancel" for x in CALLS
        )
        assert not page.evaluate("calls.some(x=>x.action==='status')")
        page.evaluate("fixtureReady()")
        page.wait_for_function("completed.length===1")
        assert page.evaluate("calls") == [
            {"action": "status", "data": {"attempt_id": "fictional-local-attempt"}}
        ]
        assert (
            "fictional-local-attempt"
            not in page.locator("[data-core-login-status]").inner_text()
        )
        for case in ["unsafe", "http", "userinfo", "fragment"]:
            page.goto(origin + "/login?case=" + case)
            page.evaluate("fixtureReady()")
            page.get_by_role("button", name="Login with KagNode").click()
            expect(page.locator("[data-core-login-status]")).to_contain_text(
                "Unable to connect"
            )
            assert page.url.startswith(origin)
            expect(page.locator("[data-core-login-provider]")).to_be_enabled()
        page.goto(origin + "/login?case=stale&kagnode_attempt=stale-local-attempt")
        page.evaluate("window.holdStatus=true;fixtureReady()")
        page.wait_for_function("typeof resolveStatus==='function'")
        assert page.evaluate("KagNodeLogin.hasPendingReturn")
        page.evaluate("KagNodeLogin.reset();resolveStatus()")
        page.wait_for_timeout(100)
        assert page.evaluate("completed.length") == 0
        assert not page.evaluate("KagNodeLogin.hasPendingReturn")
        page.goto(
            origin + "/login?case=duplicate&kagnode_attempt=one&kagnode_attempt=two"
        )
        page.evaluate("fixtureReady()")
        expect(page.locator("[data-core-login-status]")).to_contain_text("not approved")
        assert not page.evaluate("calls.length")
        page.goto(origin + "/login?case=reset&kagnode_attempt=reset-attempt")
        assert page.evaluate("KagNodeLogin.hasPendingReturn")
        page.evaluate("KagNodeLogin.reset();fixtureReady()")
        assert not page.evaluate("calls.length")
        page.goto(
            origin
            + "/login?case=denied&kagnode_attempt=denied-attempt&kagnode_error=%3Cscript%3Eraw-error%3C%2Fscript%3E"
        )
        page.evaluate("fixtureReady()")
        expect(page.locator("[data-core-login-status]")).to_contain_text("not approved")
        assert "raw-error" not in page.locator("body").inner_text()
        assert page.evaluate("completed.length") == 0
        page.close()
        context = browser.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto(origin + "/login")
        expect(page.locator("#identity")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
        context.close()
        browser.close()
finally:
    server.shutdown()
print(
    json.dumps(
        {
            "engine": engine,
            "progressiveWidths": [390, 820, 1440],
            "nativePostAndCsrf": True,
            "autofill": True,
            "reducedMotion": True,
            "mfaAndKeyUnchanged": True,
            "browserRedirectResume": True,
            "trustedIssuer": True,
            "staleResume": True,
            "deviceFlow": "separate existing regression",
            "javascriptFallback": True,
        }
    )
)
