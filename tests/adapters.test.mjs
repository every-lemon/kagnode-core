import test from "node:test";
import assert from "node:assert/strict";
import {
  inject,
  asset,
  active,
  installCore,
} from "../dist/node/kagnode-core.mjs";
test("Core serves only integrity checked local assets", () => {
  const m = active("example");
  assert.match(m.version, /^5\.0\.\d+$/);
  for (const file of Object.keys(m.files))
    assert.ok(asset("/kagnode-core/" + m.version + "/" + file));
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

test("JSON and plain text containing literal HTML are not rewritten by the server adapter", () => {
  let middleware;
  const app = {
    use(fn) {
      middleware = fn;
    },
  };
  installCore(app, { appId: "example" });
  for (const mime of ["application/json; charset=utf-8", "text/plain"]) {
    let actual;
    const response = {
      get: () => mime,
      send(value) {
        actual = value;
        return this;
      },
      set() {
        throw Error("Non-HTML response was modified");
      },
    };
    middleware({ path: "/api/v1/search" }, response, () => {});
    const body = JSON.stringify({
      results: [
        { title: "Literal <head> text and </head> in a search result" },
      ],
    });
    response.send(body);
    assert.equal(actual, body);
    assert.deepEqual(JSON.parse(actual), JSON.parse(body));
  }
});

test("canonical login owns the mark and selected original component icons", async () => {
  const { renderTemplate, icon, iconSources } =
    await import("../dist/node/kagnode-core.mjs");
  const frame = renderTemplate("login-frame", {
    product: "KagNode Example",
    heading: "Sign in",
    description: "Local credentials remain required.",
    content:
      '<form method="post"><input name="csrf" type="hidden" value="fixture"><button data-core-login-submit>Sign in</button></form>',
  });
  assert.equal((frame.match(/class="kn-core-login-mark"/g) || []).length, 1);
  assert.match(frame, /name="csrf" type="hidden" value="fixture"/);
  assert.equal(iconSources.security, "shield");
  assert.equal(iconSources["eye-off"], "eye-off");
  assert.match(icon("copy"), /data-core-icon-name="copy"/);
  assert.doesNotMatch(icon('bad" onclick="bad'), / onclick="bad/);
});
