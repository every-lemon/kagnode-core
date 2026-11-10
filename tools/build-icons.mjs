import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { iconCatalog } from "../assets/icon-library/source.mjs";
import { renderIcon } from "../packages/icons/render.mjs";
const root = path.resolve(import.meta.dirname, "..");
const out = path.join(root, "dist/icons");
const ids = new Set(),
  shapes = new Set();
import { validateIcon } from "./icon-validation.mjs";
for (const icon of iconCatalog) {
  validateIcon(icon);
  if (ids.has(icon.id) || shapes.has(icon.body))
    throw new Error(`Duplicate ID or shape: ${icon.id}`);
  ids.add(icon.id);
  shapes.add(icon.body);
}
// Build only the optional directory. Default bundle.json and core.js never import it.
fs.rmSync(out, { recursive: true, force: true });
for (const dir of ["svg", "glyphs", "categories"])
  fs.mkdirSync(path.join(out, dir), { recursive: true });
const write = (file, data) => fs.writeFileSync(path.join(out, file), data);
for (const icon of iconCatalog) {
  const definition = { ...icon, viewBox: "0 0 24 24" };
  write(
    `svg/${icon.id}.svg`,
    renderIcon(definition, { title: icon.title }) + "\n",
  );
  write(
    `glyphs/${icon.id}.mjs`,
    "// AGPL-3.0-only; original KagNode Core geometry.\nexport default Object.freeze(" +
      JSON.stringify(definition).replace(
        '"tags":' + JSON.stringify(definition.tags),
        '"tags":Object.freeze(' + JSON.stringify(definition.tags) + ")",
      ) +
      ");\n",
  );
  write(
    `glyphs/${icon.id}.d.mts`,
    "import type {IconDefinition} from '../types.d.mts';\ndeclare const icon: IconDefinition & {readonly id: '" +
      icon.id +
      "'};\nexport default icon;\n",
  );
}
for (const category of [...new Set(iconCatalog.map((i) => i.category))]) {
  const icons = iconCatalog.filter((i) => i.category === category);
  const camel = (id) => id.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
  const module =
    icons
      .map(
        (i) =>
          `export {default as ${camel(i.id)}} from '../glyphs/${i.id}.mjs';`,
      )
      .join("\n") + "\n";
  write(`categories/${category}.mjs`, module);
  write(`categories/${category}.d.mts`, module);
}
for (const file of ["render.mjs", "render.d.mts", "types.d.mts"])
  write(file, fs.readFileSync(path.join(root, "packages/icons", file)));
const metadata = iconCatalog.map(({ body, ...i }) => ({
  ...i,
  svg: `svg/${i.id}.svg`,
  module: `glyphs/${i.id}.mjs`,
}));
write(
  "catalog.json",
  JSON.stringify(
    {
      schema: 1,
      grid: 24,
      strokeWidth: 1.7,
      count: metadata.length,
      license: "AGPL-3.0-only",
      icons: metadata,
    },
    null,
    2,
  ) + "\n",
);
write(
  "catalog.d.mts",
  `export type IconId = ${metadata.map((i) => JSON.stringify(i.id)).join(" | ")};\nexport type IconCategory = ${[...new Set(metadata.map((i) => i.category))].map((c) => JSON.stringify(c)).join(" | ")};\n`,
);
for (const file of ["index.html", "gallery.mjs", "gallery.css"])
  write(file, fs.readFileSync(path.join(root, "examples/icons", file)));
write("LICENSE", fs.readFileSync(path.join(root, "LICENSE")));
write("README.md", fs.readFileSync(path.join(root, "docs/ICONS.md")));
write(
  "package.json",
  JSON.stringify(
    {
      name: "@kagnode/core-icons",
      version: JSON.parse(fs.readFileSync(path.join(root, "package.json")))
        .version,
      type: "module",
      license: "AGPL-3.0-only",
      sideEffects: false,
      exports: {
        "./render": { types: "./render.d.mts", import: "./render.mjs" },
        "./glyphs/*": { types: "./glyphs/*.d.mts", import: "./glyphs/*.mjs" },
        "./categories/*": {
          types: "./categories/*.d.mts",
          import: "./categories/*.mjs",
        },
        "./catalog.json": "./catalog.json",
        "./catalog": "./catalog.d.mts",
        "./svg/*": "./svg/*",
      },
    },
    null,
    2,
  ) + "\n",
);
const inventory = Object.fromEntries(
  fs
    .readdirSync(path.join(out, "svg"))
    .sort()
    .map((name) => {
      const bytes = fs.readFileSync(path.join(out, "svg", name));
      return [
        name,
        {
          size: bytes.length,
          sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
        },
      ];
    }),
);
write("svg-inventory.json", JSON.stringify(inventory, null, 2) + "\n");
console.log(
  `Built ${iconCatalog.length} original optional Core icons in ${Object.keys(groupsForLog()).length} categories.`,
);
function groupsForLog() {
  return Object.fromEntries(iconCatalog.map((i) => [i.category, true]));
}
