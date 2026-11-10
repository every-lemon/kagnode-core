// Reproduce optional-load cost without including the catalog in an application.
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { execFileSync } from "node:child_process";
const root = path.resolve(import.meta.dirname, ".."),
  out = path.join(root, "test-artifacts/icons");
fs.mkdirSync(out, { recursive: true });
const builder =
  process.env.ESBUILD || path.join(root, "node_modules/.bin/esbuild");
const report = { defaultUIIncrementalBytes: 0, sourceIcons: 320 };
for (const [name, imports] of Object.entries({
  individual: "import icon from '../../dist/icons/glyphs/shield-check.mjs';",
  category:
    "import {shieldCheck as icon} from '../../dist/icons/categories/security.mjs';",
})) {
  const entry = path.join(out, name + ".mjs");
  fs.writeFileSync(
    entry,
    imports +
      "\nimport {renderIcon} from '../../dist/icons/render.mjs';\nexport const verified = renderIcon(icon,{title:'Verified'});\n",
  );
  const bytes = execFileSync(builder, [
    entry,
    "--bundle",
    "--format=esm",
    "--minify",
    "--target=es2020",
  ]);
  report[name] = {
    bundledBytes: bytes.length,
    gzipBytes: zlib.gzipSync(bytes).length,
  };
  if (
    bytes.toString().includes("shield-alert") ||
    bytes.toString().includes("catalog.json")
  )
    throw new Error("Unrequested glyphs retained");
}
report.svgBytes = fs.statSync(
  path.join(root, "dist/icons/svg/shield-check.svg"),
).size;
report.metadataBytes = fs.statSync(
  path.join(root, "dist/icons/catalog.json"),
).size;
report.individualModuleBytes = fs.statSync(
  path.join(root, "dist/icons/glyphs/shield-check.mjs"),
).size;
report.rendererBytes = fs.statSync(
  path.join(root, "dist/icons/render.mjs"),
).size;
fs.writeFileSync(
  path.join(out, "byte-cost.json"),
  JSON.stringify(report, null, 2) + "\n",
);
console.log(JSON.stringify(report));
