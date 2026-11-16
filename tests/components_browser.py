"""Administration folder, shared data components and the confirmation form dialog.
Fixture page only; no live account or application data."""

import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "tests/browser.py").read_text().split("server = ThreadingHTTPServer")[0]
ns = {"__file__": str(ROOT / "tests/browser.py"), "__name__": "fixture"}
exec(compile(src, "fixture", "exec"), ns)

WIDE = "".join(f"<th>Column {i}</th>" for i in range(12))
ROW = "".join(f"<td>Value {i}</td>" for i in range(12))
CONTENT = f"""<div id="components">
<div class="kn-table-wrap"><table class="kn-table"><caption>Wide fixture table</caption>
<thead><tr>{WIDE}</tr></thead><tbody><tr>{ROW}</tr></tbody></table></div>
<p><span class="kn-badge" data-tone="ok">ok</span> <span class="kn-badge" data-tone="warn">warn</span>
<span class="kn-badge" data-tone="bad">bad</span> <span class="kn-badge" data-tone="info">info</span>
<span class="kn-badge">neutral</span></p>
<dl class="kn-facts"><div><dt>Site</dt><dd>home</dd></div><div><dt>Server</dt><dd>main</dd></div></dl>
<progress class="kn-meter" data-tone="warn" max="100" value="80" aria-label="Storage used"></progress>
<div class="kn-state" data-tone="bad" role="alert"><strong>Could not load</strong><p>Try again.</p></div>
</div><div style="height:1500px"></div>"""
ns["HTML"] = ns["HTML"].replace('<div style="height:1500px"></div>', CONTENT)

CONTRAST = """()=>{
  const bg=(()=>{let n=document.documentElement;const c=getComputedStyle(document.body).backgroundColor;return c})();
  const parse=(c)=>c.match(/[\\d.]+/g).map(Number);
  const lum=([r,g,b])=>{const f=(v)=>{v/=255;return v<=.03928?v/12.92:((v+.055)/1.055)**2.4};return .2126*f(r)+.7152*f(g)+.0722*f(b)};
  const page=parse(bg).slice(0,3);
  return [...document.querySelectorAll('.kn-badge')].map((e)=>{
    const s=getComputedStyle(e),t=parse(s.color).slice(0,3),b=parse(s.backgroundColor),a=b.length>3?b[3]:1;
    const mix=b.slice(0,3).map((v,i)=>v*a+page[i]*(1-a));
    const l1=lum(t),l2=lum(mix),hi=Math.max(l1,l2),lo=Math.min(l1,l2);
    return [e.textContent,+((hi+.05)/(lo+.05)).toFixed(2)]})
}"""


class Admin(ns["Handler"]):
    """Adds pages whose server-side context asks Core for the Administration folder."""

    def do_GET(self):
        if self.path in ("/with-admin", "/signed-out-with-admin"):
            session = {
                "authenticated": self.path == "/with-admin",
                "subject": "fixture",
            }
            context = dict(
                session, adminFolder={"url": "/admin", "label": "Administration"}
            )
            data = ns["core"].inject(ns["HTML"], "example", context).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Admin)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
    exe = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
    errors = []
    with sync_playwright() as p:
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": exe} if exe else {})
        )

        def open_page(width, scheme="light"):
            page = browser.new_page(
                viewport={"width": width, "height": 900}, color_scheme=scheme
            )
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            page.wait_for_function("!!window.KagNodeCore")
            page.wait_for_timeout(300)
            return page

        # ---- Administration folder
        page = open_page(1440)
        folder = ".kn-core-sidebar-navigation [data-core-admin-folder]"
        assert page.locator(folder).count() == 0, (
            "no folder unless the application opts in"
        )
        assert (
            page.evaluate(
                "KagNodeCore.setAdminFolder({url:'https://daemon.example.invalid/admin'})"
            )
            is True
        )
        assert page.locator(folder).count() == 1
        summary = page.locator(folder + " > summary")
        assert summary.inner_text().strip() == "Administration"
        link = page.locator(folder + " .submenu a")
        assert link.get_attribute("href") == "https://daemon.example.invalid/admin"
        assert link.text_content() == "Daemon administration"
        assert (
            page.evaluate(
                "document.querySelector('[data-core-admin-folder] .submenu').inert"
            )
            is True
        )
        summary.focus()
        page.keyboard.press("Enter")
        page.wait_for_timeout(450)
        assert summary.get_attribute("aria-expanded") == "true"
        assert (
            page.evaluate(
                "document.querySelector('[data-core-admin-folder] .submenu').inert"
            )
            is False
        )
        assert link.is_visible()
        # unsafe destinations are refused and nothing is rendered
        for bad in ["javascript:alert(1)", "data:text/html,x", "vbscript:x", "//"]:
            ok = page.evaluate("(u)=>KagNodeCore.setAdminFolder({url:u})", bad)
            assert ok is False and page.locator(folder).count() == 0, bad
        # a relative path resolves against the page; extra items are capped; labels trimmed
        items = [
            {"label": f"Item {i} " + "x" * 80, "href": f"/admin/{i}"} for i in range(12)
        ]
        assert (
            page.evaluate(
                "(i)=>KagNodeCore.setAdminFolder({url:'/admin',items:i})", items
            )
            is True
        )
        assert page.locator(folder + " .submenu a").count() == 8
        assert len(page.locator(folder + " .submenu a").first.text_content()) <= 40
        assert (
            page.evaluate("KagNodeCore.setAdminFolder({url:'/admin',enabled:false})")
            is False
        )
        assert page.locator(folder).count() == 0
        # never for a signed-out visitor, and removed when the session ends
        page.evaluate("KagNodeCore.setAdminFolder({url:'/admin'})")
        assert page.locator(folder).count() == 1
        page.evaluate("KagNodeCore.setSession({authenticated:false})")
        page.wait_for_timeout(150)
        assert page.locator(folder).count() == 0, "removed when signed out"
        assert page.evaluate("KagNodeCore.setAdminFolder({url:'/admin'})") is False
        assert page.locator(folder).count() == 0
        page.evaluate("KagNodeCore.setSession({authenticated:true,subject:'fixture'})")
        assert page.evaluate("KagNodeCore.setAdminFolder({url:'/admin'})") is True
        # the sidebar keeps its width contract with the folder present
        page.locator("[data-core-toggle]").click()
        page.wait_for_timeout(450)
        assert round(page.locator("#sidebar").bounding_box()["width"]) == 57
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.locator("[data-core-toggle]").click()
        page.close()

        # ---- the application opts in through the adapter context
        for path, expected in [("/with-admin", 1), ("/signed-out-with-admin", 0)]:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url + path)
            page.wait_for_function("!!window.KagNodeCore")
            page.wait_for_timeout(300)
            assert page.locator(folder).count() == expected, (path, expected)
            page.close()

        # ---- components: both themes, contrast and overflow
        for scheme in ["light", "dark"]:
            page = open_page(1440, scheme)
            for label, ratio in page.evaluate(CONTRAST):
                if label != "neutral":
                    assert ratio >= 4.5, (engine, scheme, label, ratio)
            assert (
                page.locator("progress.kn-meter").evaluate(
                    "e=>e.getBoundingClientRect().height"
                )
                <= 9
            )
            assert page.locator(".kn-state[role=alert]").is_visible()
            assert page.locator(".kn-table > caption").count() == 1
            page.close()
        page = open_page(390)
        wrap = page.locator(".kn-table-wrap")
        assert wrap.evaluate("e=>e.scrollWidth>e.clientWidth"), (
            "wide table scrolls inside its wrapper"
        )
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (
            "no page overflow"
        )
        page.close()

        # ---- confirmation form dialog
        page = open_page(1440)
        page.evaluate(
            """()=>{window.__result=null;window.__calls=0;
            KagNodeDialogs.form({title:'Revoke alpha',intro:'The node stops working.',submit:'Revoke',danger:true,
              fields:[{name:'password',label:'Your password',type:'password',autocomplete:'current-password'}],
              onSubmit:async(v)=>{window.__calls++;if(v.password!=='right')throw Error('Password is incorrect')}
            }).then((v)=>window.__result=v)}"""
        )
        dialog = page.get_by_role("dialog", name="Revoke alpha")
        dialog.wait_for()
        field = dialog.get_by_label("Your password")
        assert field.get_attribute("type") == "password"
        assert field.get_attribute("autocomplete") == "current-password"
        assert page.evaluate("document.activeElement.name") == "password"
        field.fill("wrong")
        dialog.get_by_role("button", name="Revoke").click()
        dialog.get_by_role("alert").filter(has_text="Password is incorrect").wait_for()
        assert dialog.is_visible() and page.evaluate("window.__result") is None
        field.fill("right")
        dialog.get_by_role("button", name="Revoke").click()
        page.wait_for_function("window.__result===true")
        page.wait_for_timeout(300)
        assert page.locator("dialog input[type=password]").count() == 0, (
            "typed value removed from the DOM"
        )
        # cancel resolves false and clears
        page.evaluate(
            """()=>{window.__result=null;KagNodeDialogs.form({title:'Second',submit:'Go',
              fields:[{name:'phrase',label:'Phrase'}],onSubmit:()=>{}}).then((v)=>window.__result=v)}"""
        )
        second = page.get_by_role("dialog", name="Second")
        second.wait_for()
        second.get_by_role("button", name="Cancel").click()
        page.wait_for_function("window.__result===false")
        page.wait_for_timeout(300)
        assert page.locator("dialog").filter(has_text="Second").count() == 0
        page.close()
        browser.close()
    assert not errors, errors
    print(f"PASS: {engine} admin folder, data components and confirmation dialog")


if __name__ == "__main__":
    main()
