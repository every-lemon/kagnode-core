import test from "node:test";
import assert from "node:assert/strict";
import { inject, asset, active } from "../dist/node/kagnode-core.mjs";
test("Core serves only integrity checked local assets", () => {
  const m = active("example");
  assert.equal(m.version, "1.0.0");
  for (const file of Object.keys(m.files))
    assert.ok(asset("/kagnode-core/1.0.0/" + file));
  for (const p of [
    "/kagnode-core/1.0.0/../LICENSE",
    "/kagnode-core/../../etc/passwd",
    "/kagnode-core/1.0.0/core.map",
    "/kagnode-core/99.0.0/mark.svg",
  ])
    assert.equal(asset(p), null);
});
test("injection is idempotent, escapes context and retires old controllers", () => {
  const html =
    '<html><head><script src="/static/theme.js"></script><script defer src="/inputs.js?v=1"></script></head><body data-authenticated="true"></body></html>';
  const result = inject(html, "example", {
    subject: '\"><script>alert(1)</script>',
  });
  assert.equal((result.match(/name="kagnode-core"/g) || []).length, 1);
  assert.ok(!result.includes("/static/theme.js"));
  assert.ok(!result.includes("/inputs.js"));
  assert.ok(!result.includes("<script>alert"));
  assert.ok(!result.includes("raw.githubusercontent"));
  assert.equal(inject(result, "example"), result);
});

test("canonical server partials accept only known templates", async () => {
  const { renderTemplate } = await import("../dist/node/kagnode-core.mjs");
  assert.match(
    renderTemplate("sidebar", {
      brand: "<a>KagNode.</a>",
      navigation: "<nav>Authorized links</nav>",
    }),
    /Authorized links/,
  );
  assert.throws(() => renderTemplate("private-config"));
});
