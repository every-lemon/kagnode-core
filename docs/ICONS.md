# Original Core icon library

Core 5.0 includes **320 original UI icons in 16 categories**. Each category contains 20 symbols: actions, navigation, accounts, security, mail, files, media, cloud, network, devices, developer, calendar, status, accessibility, layout and commerce. Stable kebab-case IDs, English titles and search tags are in `dist/icons/catalog.json`. All icons use `viewBox="0 0 24 24"`, unfilled 1.7-unit strokes and rounded caps/joins. Review them at 16, 20 and 24 pixels in the responsive, searchable gallery at `dist/icons/index.html`.

## Optional local delivery

The expanded catalog is **not** imported into Core's default script, UI manifest, embedded Node/Python adapters or automatic UI archives. Its incremental default browser payload is zero bytes. Install the separate `kagnode-core-V-icons.tgz` npm-compatible package, or extract `kagnode-core-V-icons.zip` / `-icons.tar.gz` and serve only the glyphs your application uses from its own static directory. No browser GitHub requests are needed. The existing compact `assets/icons.json` and adapter `icon()` contracts remain available independently.

```js
// Using the optional package; individual ESM modules have no side effects.
import shieldCheck from "@kagnode/core-icons/glyphs/shield-check";
import { renderIcon } from "@kagnode/core-icons/render";
const decorative = renderIcon(shieldCheck); // aria-hidden, focusable=false
const informative = renderIcon(shieldCheck, {
  title: "Verified connection",
  size: 20,
});
```

Use an individual module for minimum bytes. Alternatively import named icons from `@kagnode/core-icons/categories/security`; a bundler can tree-shake these static re-exports. Do not import a whole category namespace when you only need one icon. Types accompany each glyph and category; `IconId` and `IconCategory` unions are available through the type-only `@kagnode/core-icons/catalog` entry. `IconDefinition` and `IconOptions` are described in `types.d.mts`. All exported definitions and their tag arrays are frozen.

For direct browser ESM without a bundler, copy `render.mjs` and the required `glyphs/*.mjs` under your application's static assets, and import them with local URLs. Do not point production browser imports at GitHub or a release download. Category re-exports without a bundler load the selected category's 20 glyph modules; use individual glyphs when that is unnecessary.

```html
<!-- Static locally served SVG beside an accessible text label. -->
<button type="button">
  <img src="/static/icons/add.svg" width="20" height="20" alt="" /> Add item
</button>
<!-- An informative standalone external SVG needs its host image alternative. -->
<img
  src="/static/icons/shield-check.svg"
  width="24"
  height="24"
  alt="Verified connection"
/>
```

Each downloaded SVG has a title and an `aria-label` for standalone/inline use. An external `<img>` needs its own `alt`. Icon-only buttons need an accessible button name. Decorative inline icons should use the renderer's default or be given `aria-hidden="true"`; adjacent text supplies the meaning. `renderIcon` escapes titles and classes; informative rendering requires a nonempty title, never an inferred filename. It accepts a trusted generated definition, not arbitrary user SVG. It does not sanitize untrusted artwork. Sizes are finite values from 1 to 1024 pixels. CSS can override size and stroke color on inline SVG; external images use their own SVG color (black), so use inline rendering when an icon must inherit foreground color.

## Gallery and downloads

After `npm run build`, run `python3 -m http.server 8124 --directory dist/icons` and open `http://127.0.0.1:8124/`. Search IDs, titles and tags, filter categories, choose light/dark appearance, and download each original SVG. The gallery loads metadata only on its own route; SVG previews use native lazy loading. It uses no external fonts, scripts, images or network endpoints. All filters and download links are keyboard accessible; results are announced through a polite status region.

## Editing, safety and licensing

Edit the geometry in `assets/icon-library/source.mjs`, then run `npm run build`. The generator validates the closed SVG grammar and unique IDs/shapes before producing individual modules, SVGs, metadata, type declarations and SHA-256 SVG inventory. No scripts, event attributes, styles, external references, `foreignObject`, reused SVG IDs or runtime fetch loader are accepted. Tests parse every SVG and check paths, viewBox, safe attributes and nonduplicate raster geometry.

These UI symbols were drawn for Core and are licensed **AGPL-3.0-only**, like the software; see `LICENSE`. They do not incorporate third-party icon libraries or brand marks. Keep the license and corresponding editable source when redistributing. The separate [KagNode Logos repository](https://github.com/every-lemon/kagnode-logos) remains the canonical brand artwork collection, with its existing artwork permission and provenance unchanged. This library is generic UI geometry, not a brand-logo replacement.

## Measured payload

The selected component set is recorded in `assets/icon-aliases.json` and the signed bundle's `icon_sources`. Sidebar and common action aliases render those original library glyphs through `icon(name)` in Node/Python or `KagNodeCore.icon(name)` in the browser. Unknown names use the document fallback. Icons are decorative; their enclosing controls need an accessible name. The panel-divider toggle retains its animated divider geometry.

Only selected component glyphs enter the default bundle; the full 320-glyph catalog is never imported by it. Additional application-specific icons can use individual modules plus `renderIcon`, preserving source provenance and excluding unrequested glyphs. Run `node tools/icon-cost.mjs` for the current measured individual/category cost; the old 1.4 optional-only zero-byte measurement is historical and does not describe 5.0's integrated component set.

For explicit static or dynamically inserted controls use `<span data-core-icon="refresh" aria-hidden="true"></span>`. Core replaces its children with the canonical decorative glyph, observes changes to the name, and does not guess actions outside the sidebar. Unknown names use the document fallback. Do not put the marker on a button whose text or accessible name would be replaced; use a child span. Repeated refreshes do not stack SVG elements. Browser code can use `KagNodeCore.icon(alias)` to obtain the same SVG. Add an enclosing button label or visible text.
