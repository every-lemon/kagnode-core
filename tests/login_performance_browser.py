"""Shared login and repeated navigation checks using local assets and fake sessions."""

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
LOGIN = core.render_template(
    "login-frame",
    {
        "product": "KagNode Example",
        "heading": "Welcome back",
        "description": "Sign in to your workspace.",
        "content": '<form action="/local-login" method="post"><input type="hidden" name="csrf" value="fixture"><label for="user">User name</label><input id="user" name="user" autocomplete="username"><label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password"><button>Sign in locally</button></form>',
        "provider": '<a data-core-login-provider href="/authorized-connect">Login with KagNode</a><p role="status" data-core-login-status>Connection cancelled. You can try again or sign in locally.</p>',
    },
)
SHELL = (
    '<aside id="sidebar" class="sidebar"><a class="brand">KagNode</a><nav><details><summary>Products</summary><div><a href="#content">Example</a></div></details>'
    + "".join('<a href="#content">Item %s</a>' % i for i in range(20))
    + '</nav></aside><div class="workspace"><header class="topbar" style="display:flex;justify-content:flex-end;padding:20px;height:60px"><div class="topbar-right"></div></header><main id="content">'
    + "".join("<p>Content %s</p>" % i for i in range(1000))
    + '</main></div><button id="lock-button">Lock</button><dialog><button>Close</button></dialog>'
)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        asset = core.asset(self.path)
        if asset:
            data, mime = asset
        else:
            login = self.path.startswith("/login")
            content = LOGIN if login else SHELL
            if self.path == "/login-local":
                content = content.replace(
                    '<a data-core-login-provider href="/authorized-connect">Login with KagNode</a>',
                    "",
                )
            html = (
                '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body data-core-settings="/profile">'
                + content
                + "</body></html>"
            )
            data = core.inject(
                html,
                "fixture",
                {
                    "authenticated": not login,
                    "subject": "fixture",
                    "name": "Example",
                    "email": "before@example.test",
                },
            ).encode()
            mime = "text/html"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
origin = "http://127.0.0.1:" + str(server.server_port)
errors = []
try:
    with sync_playwright() as p:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": executable} if executable else {})
        )
        for width in [390, 768, 1440]:
            page = browser.new_page(
                viewport={"width": width, "height": 900}, reduced_motion="reduce"
            )
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route(
                "**/*",
                lambda route: route.continue_()
                if route.request.url.startswith(origin)
                else route.abort(),
            )
            page.goto(origin + "/login")
            page.wait_for_function("!!window.KagNodeCore")
            assert page.locator("form").get_attribute("action") == "/local-login"
            assert page.locator("[name=csrf]").input_value() == "fixture"
            assert (
                page.locator("[data-core-login-provider]").inner_text()
                == "Login with KagNode"
            )
            assert (
                page.locator("[data-core-login-provider]").get_attribute("href")
                == "/authorized-connect"
            )
            assert (
                page.locator("[role=status]")
                .filter(has_text="Connection cancelled")
                .count()
                == 1
            )
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert (
                page.locator(".kn-core-login-card").evaluate(
                    "e=>getComputedStyle(e).borderRadius"
                )
                == "12px"
            )
            assert page.locator(".kn-core-login-mark").count() == 1
            assert (
                page.locator("#user").evaluate("e=>getComputedStyle(e).borderRadius")
                == "8px"
            )
            assert (
                page.locator("#password").evaluate("e=>getComputedStyle(e).minHeight")
                == "44px"
            )
            assert (
                page.locator("form button").evaluate(
                    "e=>getComputedStyle(e).backgroundColor"
                )
                == "rgb(37, 99, 235)"
            )
            assert (
                page.locator("form button").evaluate(
                    "e=>getComputedStyle(e).borderRadius"
                )
                == "8px"
            )
            assert page.evaluate(
                "KagNodeCore.iconSources.copy === 'copy' && KagNodeCore.iconSources.community === 'people'"
            )
            assert 'data-core-icon-name="eye-off"' in page.evaluate(
                "KagNodeCore.icon('eye-off')"
            )
            page.evaluate("""() => {
              const button=document.createElement('button');button.id='icon-fixture';button.type='button';button.setAttribute('aria-label','Copy');
              button.innerHTML='<span data-core-icon="copy" aria-hidden="true"></span>';
              document.querySelector('.kn-core-login-content').append(button);
            }""")
            page.locator('#icon-fixture svg[data-core-icon-name="copy"]').wait_for()
            page.evaluate(
                "document.querySelector('#icon-fixture span').dataset.coreIcon='eye-off'"
            )
            page.locator('#icon-fixture svg[data-core-icon-name="eye-off"]').wait_for()
            page.evaluate("KagNodeCore.refresh();KagNodeCore.refresh()")
            assert page.locator("#icon-fixture svg").count() == 1
            assert page.locator("#icon-fixture").get_attribute("aria-label") == "Copy"
            page.evaluate("""() => {
              const host=document.createElement('div');host.id='field-fixture';
              host.innerHTML='<label>Nested<input id="nested-input"></label><div class="kn-core-login-field"><label for="secret-input">Password</label><div class="kn-core-login-secret"><input id="secret-input" type="password" autocomplete="current-password"><button type="button" aria-label="Show password"><span data-core-icon="eye"></span></button></div></div>';
              document.querySelector('.kn-core-login-content').append(host);
            }""")
            assert (
                page.locator("#nested-input").evaluate(
                    "e=>getComputedStyle(e).fontWeight"
                )
                == "400"
            )
            assert (
                page.locator("#user").evaluate("e=>getComputedStyle(e).fontWeight")
                == "400"
            )
            assert page.locator(".kn-core-login-secret").evaluate(
                "e=>{const [i,b]=[...e.children].map(n=>n.getBoundingClientRect());return Math.abs(i.top-b.top)<1&&Math.abs(i.height-b.height)<1&&b.width===44&&b.left>=i.right-1}"
            )
            assert (
                page.locator(".kn-core-login-secret button").get_attribute("type")
                == "button"
            )
            page.locator("[data-core-login-provider]").focus()
            assert page.locator("[data-core-login-provider]").evaluate(
                "e=>e===document.activeElement"
            )
            page.evaluate("""() => {
              const a=document.querySelector('[data-core-login-provider]');
              const b=document.createElement('button');b.type='button';b.dataset.coreLoginProvider='';b.textContent=a.textContent;a.replaceWith(b);
              window.loginCalls=[];
              window.KagNodeLoginHost={state:()=>({enabled:window.loginEnabled!==false}),request:async(action,data)=>{loginCalls.push({action,data});if(action==='status')return new Promise(resolve=>window.pollResolve=resolve);return {pending:true,attempt_id:'fixture-attempt',user_code:'ABCD',verification_uri:'https://issuer.example.test/approve',expires_in:30,interval:1}},complete:async()=>{window.loginCompleted=true}};
            }""")
            page.evaluate("window.loginEnabled=false;KagNodeLogin.refresh()")
            assert page.locator("[data-core-login-provider]").is_disabled()
            page.evaluate(
                "window.loginEnabled=true;document.dispatchEvent(new Event('kagnode:login-ready'))"
            )
            page.locator("[data-core-login-provider]").click()
            page.get_by_role("button", name="Cancel connection").wait_for()
            assert (
                page.get_by_role("link", name="Open KagNode to approve").get_attribute(
                    "href"
                )
                == "https://issuer.example.test/approve"
            )
            page.wait_for_function("typeof window.pollResolve==='function'")
            page.get_by_role("button", name="Cancel connection").click()
            page.evaluate("pollResolve({authorized:true,continuation:'signed_in'})")
            assert page.evaluate("window.loginCompleted!==true")
            assert page.locator("[data-core-login-provider]").is_enabled()
            page.wait_for_function("loginCalls.some(x=>x.action==='cancel')")
            page.evaluate(
                "KagNodeLoginHost.request=async()=>({authorized:true,continuation:'unlock'})"
            )
            page.locator("[data-core-login-provider]").click()
            page.wait_for_function("window.loginCompleted===true")
            assert page.locator("[data-core-login-provider]").is_disabled()
            page.evaluate(
                "KagNodeLogin.reset(document.querySelector('[data-core-login-provider]'))"
            )
            assert page.locator("[data-core-login-provider]").is_enabled()
            page.evaluate(
                "KagNodeLoginHost.request=async(action,data)=>{loginCalls.push({action,data});return {pending:true,attempt_id:'expiry-fixture',user_code:'ABCD',verification_uri:'https://issuer.example.test/approve',expires_in:1,interval:1}}"
            )
            page.locator("[data-core-login-provider]").click()
            page.wait_for_function(
                "loginCalls.some(x=>x.action==='cancel'&&x.data.attempt_id==='expiry-fixture')"
            )
            assert "expired" in page.locator("[data-core-login-status]").inner_text()
            assert page.locator("[data-core-login-provider]").is_enabled()
            page.goto(origin + "/login-local")
            assert page.locator("[data-core-login-provider]").count() == 0
            assert page.locator("form").is_visible()
            page.goto(origin + "/shell")
            page.wait_for_function(
                '!!document.querySelector("[data-core-account-trigger]")'
            )
            if width < 1024:
                page.locator("[data-core-mobile]").click()
                assert page.locator("html").get_attribute("data-core-drawer") == "true"
                page.keyboard.press("Escape")
                assert page.locator("html").get_attribute("data-core-drawer") == "false"
            else:
                page.evaluate(
                    """() => {window.layoutReads=0;for(const key of ['clientHeight','clientWidth','scrollHeight','scrollWidth']){const d=Object.getOwnPropertyDescriptor(Element.prototype,key);if(d?.get)Object.defineProperty(Element.prototype,key,{...d,get(){layoutReads++;return d.get.call(this)}})}}"""
                )
                page.evaluate(
                    """async()=>{for(let i=0;i<20;i++){document.querySelector('[data-core-toggle]').click();await new Promise(requestAnimationFrame)}await new Promise(requestAnimationFrame)}"""
                )
                reads = page.evaluate("layoutReads")
                assert reads < 10000, reads
                print(
                    json.dumps(
                        {
                            "engine": engine,
                            "toggles": 20,
                            "layout_dimension_reads": reads,
                        }
                    )
                )
                assert (
                    page.locator("[data-core-toggle]").get_attribute("aria-expanded")
                    == "true"
                )
                page.locator(".kn-core-nav-group summary").click()
                assert (
                    page.locator(".kn-core-nav-group").get_attribute("open") is not None
                )
                page.locator(".kn-core-nav-group summary").click()
                assert page.locator(".kn-core-nav-group").get_attribute("open") is None
            page.evaluate("""() => {
              const region=document.createElement('div');region.id='dynamic-scroll';region.style='height:80px;overflow:auto';
              region.innerHTML='<div id="dynamic-child"></div>';document.querySelector('main').prepend(region);
            }""")
            page.wait_for_function("document.querySelector('#dynamic-child')!==null")
            page.evaluate(
                "document.querySelector('#dynamic-child').innerHTML='<div style=height:1000px>Added content</div>'"
            )
            page.wait_for_function(
                "document.querySelector('.kn-core-rail[aria-controls=dynamic-scroll]')!==null"
            )
            trigger = page.locator("[data-core-account-trigger]")
            trigger.click()
            assert (
                page.locator("#kn-core-account-menu a").get_attribute("href")
                == "/profile"
            )
            page.keyboard.press("Escape")
            assert trigger.evaluate("e=>e===document.activeElement")
            page.evaluate(
                'KagNodeCore.setSession({authenticated:true,subject:"fixture",name:"Changed",email:"after@example.test"})'
            )
            trigger.click()
            assert (
                page.locator(".kn-core-account-identity strong").inner_text()
                == "Changed"
            )
            assert (
                page.locator(".kn-core-account-identity small").inner_text()
                == "after@example.test"
            )
            page.keyboard.press("Escape")
            for edge in ["left", "right"]:
                trigger.evaluate(
                    "(node,edge)=>{node.style.position='fixed';node.style.top='80px';node.style.zIndex='13000';node.style.left=edge==='left'?'12px':'auto';node.style.right=edge==='right'?'12px':'auto'}",
                    edge,
                )
                trigger.click()
                box = page.locator("#kn-core-account-menu").bounding_box()
                assert box["x"] >= 11, (width, edge, box)
                assert box["x"] + box["width"] <= width - 11, (width, edge, box)
                page.mouse.click(width // 2, 880)
                page.wait_for_function(
                    'document.querySelector("#kn-core-account-menu").hidden'
                )
            trigger.evaluate("node=>node.removeAttribute('style')")
            trigger.click()
            page.evaluate(
                """() => {const frame=document.createElement('iframe');frame.id='outside-frame';frame.title='Outside interaction fixture';frame.srcdoc='<button>Outside frame</button>';frame.style='position:fixed;left:12px;bottom:12px;width:160px;height:60px;z-index:14000';document.body.append(frame)}"""
            )
            page.frame_locator("#outside-frame").get_by_role(
                "button", name="Outside frame"
            ).click()
            page.wait_for_function(
                'document.querySelector("#kn-core-account-menu").hidden'
            )
            assert page.evaluate("document.activeElement.tagName==='IFRAME'")
            trigger.click()
            page.evaluate('document.querySelector("dialog").showModal()')
            page.wait_for_function(
                'document.querySelector("#kn-core-account-menu").hidden'
            )
            page.close()
        browser.close()
    assert not errors, errors
    print(
        "Shared login, offline assets, account focus/session and navigation checks passed"
    )
finally:
    server.shutdown()
