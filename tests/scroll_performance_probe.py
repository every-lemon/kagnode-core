"""Manual frame-paced navigation profile; run before and after on the same host."""

import json, os, time
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.set_content(
        '<aside id="sidebar" class="sidebar"><a class="brand">KagNode</a><nav>'
        + "".join('<a href="#">Item %s</a>' % i for i in range(20))
        + "</nav></aside><main>"
        + "".join("<p>Content %s</p>" % i for i in range(1000))
        + "</main>"
    )
    page.add_style_tag(content=(root / "web/core.css").read_text())
    page.evaluate("window.KagNodeIcons=" + (root / "assets/icons.json").read_text())
    page.add_script_tag(content=(root / "web/core.js").read_text())
    page.add_script_tag(content=(root / "web/scroll.js").read_text())
    page.wait_for_timeout(300)
    page.evaluate(
        """()=>{window.probe={styles:0,rects:0,scans:0,dimensions:0};for(const k of ['clientHeight','clientWidth','scrollHeight','scrollWidth']){const d=Object.getOwnPropertyDescriptor(Element.prototype,k);if(d?.get)Object.defineProperty(Element.prototype,k,{...d,get(){probe.dimensions++;return d.get.call(this)}})}const css=window.getComputedStyle;window.getComputedStyle=(...args)=>{probe.styles++;return css(...args)};const rect=Element.prototype.getBoundingClientRect;Element.prototype.getBoundingClientRect=function(){probe.rects++;return rect.call(this)};const query=Element.prototype.querySelectorAll;Element.prototype.querySelectorAll=function(s){if(s==='*')probe.scans++;return query.call(this,s)};const dq=Document.prototype.querySelectorAll;Document.prototype.querySelectorAll=function(s){if(s==='*')probe.scans++;return dq.call(this,s)}}"""
    )
    start = time.monotonic()
    page.evaluate(
        """async()=>{for(let i=0;i<20;i++){document.querySelector('[data-core-toggle]').click();await new Promise(requestAnimationFrame)}await new Promise(requestAnimationFrame)}"""
    )
    result = page.evaluate(
        "({...probe,collapsed:document.documentElement.dataset.coreCollapsed})"
    )
    result["wall_ms"] = round((time.monotonic() - start) * 1000, 2)
    print(json.dumps(result))
    browser.close()
