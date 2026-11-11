import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { iconCatalog } from "../assets/icon-library/source.mjs";
import { validateIcon } from "../tools/icon-validation.mjs";
import { renderIcon } from "../packages/icons/render.mjs";
const root = path.resolve(import.meta.dirname, "..");
test("320 distinct original icons and complete optional local inventory", async () => {
  assert.equal(iconCatalog.length, 320);
  assert.equal(new Set(iconCatalog.map((i) => i.id)).size, 320);
  assert.equal(new Set(iconCatalog.map((i) => i.body)).size, 320);
  const categories = new Set(iconCatalog.map((i) => i.category));
  assert.equal(categories.size, 16);
  const metadata = JSON.parse(
    fs.readFileSync(path.join(root, "dist/icons/catalog.json")),
  );
  assert.equal(metadata.count, 320);
  for (const category of categories)
    assert.equal(iconCatalog.filter((i) => i.category === category).length, 20);
  for (const icon of iconCatalog) {
    validateIcon(icon);
    const { default: generated } = await import(
      `../dist/icons/glyphs/${icon.id}.mjs`
    );
    assert.equal(generated.body, icon.body);
    assert.ok(Object.isFrozen(generated));
    assert.ok(Object.isFrozen(generated.tags));
    assert.equal(
      fs.readFileSync(path.join(root, `dist/icons/svg/${icon.id}.svg`), "utf8"),
      renderIcon(generated, { title: icon.title }) + "\n",
    );
    assert.ok(
      fs.existsSync(path.join(root, `dist/icons/glyphs/${icon.id}.d.mts`)),
    );
  }
});
test("closed SVG grammar rejects executable, external and malformed geometry", () => {
  const good = iconCatalog[0];
  for (const body of [
    "<script/>",
    "<foreignObject/>",
    '<path onclick="alert(1)" d="M1 1"/>',
    '<use href="https://example.test/x"/>',
    '<path style="fill:url(x)" d="M1 1"/>',
    '<path id="x" d="M1 1"/>',
    '<path d="M1 1L2"/>',
    '<path d="M1 1A2 2 0 3 0 2 2"/>',
    '<circle cx="NaN" cy="1" r="2"/>',
  ])
    assert.throws(() => validateIcon({ ...good, body }));
  assert.throws(() => validateIcon({ ...good, id: "../unsafe" }));
});
test("decorative and titled rendering escapes labels and avoids duplicate IDs", () => {
  const icon = { ...iconCatalog[0], viewBox: "0 0 24 24" };
  assert.match(renderIcon(icon), /aria-hidden="true"/);
  assert.doesNotMatch(renderIcon(icon), /<title|role="img"|id=/);
  const titled = renderIcon(icon, {
    title: 'A < B & "C"',
    className: 'x" onload="bad',
  });
  assert.match(titled, /role="img"/);
  assert.match(titled, /A &lt; B &amp; &quot;C&quot;/);
  assert.doesNotMatch(titled, /< B| class="x" onload=/);
  assert.throws(() => renderIcon(icon, { decorative: false }));
  assert.throws(() => renderIcon(icon, { title: " " }));
  for (const size of [NaN, Infinity, 0, -1, 1025, "24"])
    assert.throws(() => renderIcon(icon, { size }));
});
test("Core components use the selected original glyphs without importing the full catalog", () => {
  const current = JSON.parse(
    fs.readFileSync(path.join(root, "dist/manifest.json")),
  );
  const aliases = JSON.parse(
    fs.readFileSync(path.join(root, "assets/icon-aliases.json")),
  );
  assert.deepEqual(current.icon_sources, aliases);
  assert.ok(Object.keys(aliases).length >= 50);
  for (const [alias, id] of Object.entries(aliases)) {
    assert.equal(
      current.icons[alias],
      iconCatalog.find((i) => i.id === id).body,
    );
  }
  assert.equal(Object.keys(current.files).length, 4);
  assert.doesNotMatch(
    fs.readFileSync(path.join(root, "dist/node/kagnode-core.mjs"), "utf8"),
    /shield-alert.*person-verified|catalog\.json/,
  );
});
