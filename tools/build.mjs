import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
const root = path.resolve(import.meta.dirname, ".."),
  out = path.join(root, "dist");
fs.mkdirSync(out, { recursive: true });
const version = JSON.parse(
  fs.readFileSync(path.join(root, "package.json")),
).version;
const builder =
  process.env.ESBUILD || path.join(root, "node_modules/.bin/esbuild");
const sha = (b) => crypto.createHash("sha256").update(b).digest("hex");
const files = {},
  entrypoints = {};
function compile(name, source, ext) {
  const input = path.join(out, "input." + ext),
    output = path.join(out, "output." + ext);
  fs.writeFileSync(input, source);
  execFileSync(
    builder,
    [
      input,
      "--minify",
      "--target=es2020",
      "--legal-comments=inline",
      "--charset=utf8",
      "--outfile=" + output,
    ],
    { stdio: "pipe" },
  );
  const data = fs.readFileSync(output),
    digest = sha(data),
    filename = name + "." + digest.slice(0, 16) + "." + ext;
  files[filename] = {
    sha256: digest,
    size: data.length,
    data: data.toString("base64"),
  };
  fs.writeFileSync(path.join(out, filename), data);
  fs.unlinkSync(input);
  fs.unlinkSync(output);
  return filename;
}
const read = (name) => fs.readFileSync(path.join(root, "web", name), "utf8");
entrypoints.theme = compile("theme", read("theme.js"), "js");
const icons = JSON.parse(
  fs.readFileSync(path.join(root, "assets/icons.json"), "utf8"),
);
entrypoints.script = compile(
  "core",
  "window.KagNodeIcons=" +
    JSON.stringify(icons) +
    ";\n" +
    [
      "core.js",
      "scroll.js",
      "toc.js",
      "controls.js",
      "appearance.js",
      "updates.js",
      "search.js",
    ]
      .map(read)
      .join("\n"),
  "js",
);
entrypoints.style = compile(
  "core",
  read("controls.css") +
    "\n" +
    read("dashboard.css") +
    "\n" +
    read("core.css") +
    "\n" +
    read("search.css"),
  "css",
);
const mark = fs.readFileSync(path.join(root, "assets/mark.svg"));
files["mark.svg"] = {
  sha256: sha(mark),
  size: mark.length,
  data: mark.toString("base64"),
};
fs.writeFileSync(path.join(out, "mark.svg"), mark);
let source = "";
try {
  source = execFileSync("git", ["rev-parse", "HEAD"], {
    cwd: root,
    encoding: "utf8",
  }).trim();
} catch {}
const templates = JSON.parse(
  fs.readFileSync(path.join(root, "packages/templates.json"), "utf8"),
);
const bundle = {
  schema: 1,
  version,
  ui_api: 1,
  adapter_api: 1,
  kind: "ui",
  entrypoints,
  source_commit: source,
  repository: "every-lemon/kagnode-core",
  icons,
  files,
};
fs.writeFileSync(
  path.join(out, "bundle.json"),
  JSON.stringify(bundle, null, 2) + "\n",
);
const published = {
  ...bundle,
  files: Object.fromEntries(
    Object.entries(files).map(([n, { data, ...v }]) => [n, v]),
  ),
};
fs.writeFileSync(
  path.join(out, "manifest.json"),
  JSON.stringify(published, null, 2) + "\n",
);
fs.mkdirSync(path.join(out, "python"), { recursive: true });
fs.writeFileSync(
  path.join(out, "python/kagnode_core.py"),
  fs
    .readFileSync(path.join(root, "packages/python/sdk.py"), "utf8")
    .replace(
      "TEMPLATES = {}",
      "TEMPLATES = json.loads(" +
        JSON.stringify(JSON.stringify(templates)) +
        ")",
    )
    .replace(
      "BUNDLE = {}",
      "BUNDLE = json.loads(" + JSON.stringify(JSON.stringify(bundle)) + ")",
    ),
);
fs.mkdirSync(path.join(out, "node"), { recursive: true });
fs.writeFileSync(
  path.join(out, "node/kagnode-core.mjs"),
  fs
    .readFileSync(path.join(root, "packages/node/index.mjs"), "utf8")
    .replace(
      "const TEMPLATES = {};",
      "const TEMPLATES = " + JSON.stringify(templates) + ";",
    )
    .replace(
      "const BUNDLE = {};",
      "const BUNDLE = " + JSON.stringify(bundle) + ";",
    ),
);
fs.copyFileSync(
  path.join(root, "packages/node/index.d.ts"),
  path.join(out, "node/kagnode-core.d.mts"),
);
console.log(
  "Built KagNode Core " +
    version +
    "; " +
    Object.keys(files).length +
    " local assets and Node/Python adapters.",
);

// Remove only prior generated local assets, never runtime cached release bundles.
for (const name of fs.readdirSync(out)) {
  if (
    /^(core|theme)\.[a-f0-9]{16}\.(js|css)$/.test(name) &&
    !Object.hasOwn(files, name)
  )
    fs.unlinkSync(path.join(out, name));
}
