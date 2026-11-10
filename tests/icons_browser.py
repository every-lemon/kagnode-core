"""Local gallery, SVG geometry, raster uniqueness and keyboard/mobile acceptance."""

import functools
import hashlib
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "dist/icons"
OUT = ROOT / "test-artifacts/icons"
OUT.mkdir(parents=True, exist_ok=True)
CATALOG = json.loads((ASSETS / "catalog.json").read_text())
for icon in CATALOG["icons"]:
    svg = ET.parse(ASSETS / icon["svg"]).getroot()
    assert svg.attrib["viewBox"] == "0 0 24 24"
    assert svg.attrib["stroke-width"] == "1.7"
    assert svg.attrib["aria-label"] == icon["title"]
    assert not any("id" in el.attrib for el in svg.iter())


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


server = ThreadingHTTPServer(
    ("127.0.0.1", 0), functools.partial(Quiet, directory=str(ASSETS))
)
threading.Thread(target=server.serve_forever, daemon=True).start()
origin = f"http://127.0.0.1:{server.server_port}"
errors = []
capturing = False
stage = "start"
screenshot_csp_messages = []


def console_message(msg):
    if msg.type != "error":
        return
    # WebKit rejects Playwright's screenshot-preparation stylesheet under this
    # strict CSP. Record only that known harness message during screenshot calls;
    # actual gallery interactions retain strict CSP and fail on console errors.
    if (
        capturing
        and msg.text
        == "Refused to apply a stylesheet because its hash, its nonce, or 'unsafe-inline' does not appear in the style-src directive of the Content Security Policy."
    ):
        screenshot_csp_messages.append(msg.text)
    else:
        errors.append(f"{stage}: {msg.text}")


def capture(page, filename):
    global capturing
    capturing = True
    try:
        page.screenshot(path=str(filename), full_page=True, caret="initial")
    finally:
        capturing = False


evidence = {
    "count": 320,
    "categories": 16,
    "externalRequests": [],
    "geometry": [],
    "screenshots": [],
}
try:
    with sync_playwright() as p:
        engine = os.environ.get("KAGNODE_BROWSER_ENGINE", "chromium")
        executable = os.environ.get("KAGNODE_BROWSER_EXECUTABLE")
        browser = getattr(p, engine).launch(
            headless=True, **({"executable_path": executable} if executable else {})
        )
        for width in [1440, 390]:
            page = browser.new_page(
                viewport={"width": width, "height": 1000}, reduced_motion="reduce"
            )
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", console_message)
            page.on(
                "request",
                lambda req: evidence["externalRequests"].append(req.url)
                if not req.url.startswith(origin)
                else None,
            )
            stage = "goto"
            page.goto(origin)
            page.wait_for_function(
                "() => document.querySelectorAll('.card').length===320"
            )
            assert page.locator("#count").inner_text() == "320 of 320 icons"
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            stage = "keyboard"
            page.keyboard.press("Tab")
            assert page.locator(".skip").evaluate("(el)=>el===document.activeElement")
            page.keyboard.press("Tab")
            assert page.locator("#search").evaluate("(el)=>el===document.activeElement")
            page.keyboard.type("shield-check")
            page.wait_for_function(
                "() => document.querySelectorAll('.card').length===1"
            )
            assert page.locator(".card h2").inner_text() == "shield-check"
            for _ in range(3):
                page.keyboard.press("Tab")
            assert page.locator(".card>a").evaluate("(el)=>el===document.activeElement")
            stage = "download"
            with page.expect_download() as dl:
                page.keyboard.press("Enter")
            assert dl.value.suggested_filename == "shield-check.svg"
            stage = "search"
            page.locator("#search").focus()
            page.keyboard.press("ControlOrMeta+A")
            page.keyboard.type("no-such-icon-zzzz")
            page.wait_for_function(
                "() => document.querySelectorAll('.card').length===0"
            )
            assert page.locator("#empty").is_visible()
            stage = "search"
            page.locator("#search").focus()
            page.keyboard.press("ControlOrMeta+A")
            page.keyboard.press("Backspace")
            page.wait_for_function(
                "() => document.querySelectorAll('.card').length===320"
            )
            categories = sorted({i["category"] for i in CATALOG["icons"]})
            stage = "categories"
            for category in categories:
                page.locator("#category").select_option(category)
                assert page.locator(".card").count() == 20
                assert page.locator('.samples img[width="16"]').count() == 20
                assert page.locator('.samples img[width="20"]').count() == 20
                assert page.locator('.samples img[width="24"]').count() == 20
                # Force image loads before capturing representative sheets.
                page.locator("img").evaluate_all(
                    "els=>els.forEach(i=>i.loading='eager')"
                )
                page.wait_for_function(
                    "() => [...document.images].every(i=>i.complete&&i.naturalWidth>0)"
                )
                if width == 1440 or category in [
                    "actions",
                    "security",
                    "accessibility",
                    "developer",
                ]:
                    filename = f"{engine}-{width}-{category}.png"
                    capture(page, OUT / filename)
                    evidence["screenshots"].append(filename)
            page.locator("#appearance").select_option("dark")
            capture(page, OUT / f"{engine}-{width}-dark.png")
            stage = "geometry"
            if width == 1440:
                # Check native parser path bounds and exact rendered distinctness.
                geometry = page.evaluate(
                    """async icons=>{
                  const results=[];
                  for(const icon of icons){
                    const text=await (await fetch(icon.svg)).text();
                    const el=new DOMParser().parseFromString(text,'image/svg+xml').documentElement;
                    document.body.append(document.importNode(el,true));
                    const svg=document.body.lastElementChild;const b=svg.getBBox();
                    results.push({id:icon.id,x:b.x,y:b.y,width:b.width,height:b.height});svg.remove();
                  }return results;
                }""",
                    CATALOG["icons"],
                )
                evidence["geometry"] = geometry
                outside = [
                    g
                    for g in geometry
                    if min(g["x"], g["y"]) < 0.7
                    or g["x"] + g["width"] > 23.3
                    or g["y"] + g["height"] > 23.3
                ]
                assert not outside, outside
                stage = "canvas"
                page.set_content('<canvas width="48" height="48"></canvas>')
                hashes = {}
                for icon in CATALOG["icons"]:
                    pixels = page.evaluate(
                        """async url=>{const image=new Image();image.src=url;await image.decode();const ctx=document.querySelector('canvas').getContext('2d');ctx.clearRect(0,0,48,48);ctx.drawImage(image,0,0,48,48);return [...ctx.getImageData(0,0,48,48).data]}""",
                        origin + "/" + icon["svg"],
                    )
                    digest = hashlib.sha256(bytes(pixels)).hexdigest()
                    assert digest not in hashes, (icon["id"], hashes.get(digest))
                    hashes[digest] = icon["id"]
                evidence["uniqueRasters"] = len(hashes)
            stage = "close"
            page.close()
        browser.close()
    evidence["screenshotHarnessCSPMessages"] = len(screenshot_csp_messages)
    assert not errors, errors
    assert not evidence["externalRequests"], evidence["externalRequests"]
    (OUT / f"{engine}-results.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        f"{engine}: 320 unique SVGs, local-only gallery, desktop/mobile keyboard/download/filter checks passed"
    )
finally:
    server.shutdown()
