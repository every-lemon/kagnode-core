/*! KagNode Core. Added for 5.0.20. */
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const FORMAT = 1;
export const EDITIONS = ["ce", "be"];
export const CHANNELS = ["alpha", "beta", ""];
const NAME = /^core-(ce|be)-(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta))?$/;
const ROLE = /^[a-z][a-z0-9]*(?:\/[a-z0-9][a-z0-9-]*)?$/;
const HASH = /^sha256:[0-9a-f]{64}$/;
const SAFE = /^[a-z][a-z0-9-]{0,40}$/;
const SERVER =
  /^https:\/\/[a-z0-9]([a-z0-9.-]*[a-z0-9])?(:\d{1,5})?(\/[A-Za-z0-9._~/-]*)?$/i;
const KEY = /^ed25519:[A-Za-z0-9+/]{43}=$/;

export function coreName({ edition, version, channel = "" }) {
  if (!EDITIONS.includes(edition)) throw new Error("edition must be ce or be");
  if (!/^\d+\.\d+\.\d+$/.test(version))
    throw new Error("version must be x.x.x");
  if (!CHANNELS.includes(channel))
    throw new Error("channel must be alpha, beta or blank");
  return `core-${edition}-${version}${channel ? "-" + channel : ""}`;
}

export function parseName(name) {
  const m = NAME.exec(name);
  if (!m) throw new Error(`not a Core name: ${name}`);
  return {
    edition: m[1],
    version: `${m[2]}.${m[3]}.${m[4]}`,
    channel: m[5] || "",
  };
}

const rank = { alpha: 0, beta: 1, "": 2 };
export function compareNames(a, b) {
  const x = parseName(a),
    y = parseName(b);
  const nx = x.version.split(".").map(Number),
    ny = y.version.split(".").map(Number);
  for (let i = 0; i < 3; i++) if (nx[i] !== ny[i]) return nx[i] - ny[i];
  return rank[x.channel] - rank[y.channel];
}

/** Parse a corereq.txt. Unknown keys are an error so a typo can never widen a request. */
export function parse(text) {
  if (typeof text !== "string" || text.length > 65536)
    throw new Error("corereq.txt is missing or too large");
  const req = {
    format: 0,
    name: "",
    product: "",
    fallback: "",
    server: "",
    signingKey: "",
    need: [],
    have: {},
  };
  const seen = new Set();
  for (const [index, raw] of text
    .replace(/\r\n/g, "\n")
    .split("\n")
    .entries()) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const at = `line ${index + 1}`;
    const [key, ...rest] = line.split(/\s+/);
    const value = rest.join(" ");
    if (key === "corereq") {
      if (Number(value) !== FORMAT)
        throw new Error(`${at}: unsupported format ${value}`);
      req.format = FORMAT;
    } else if (key === "name") {
      parseName(value);
      if (req.name) throw new Error(`${at}: name given twice`);
      req.name = value;
    } else if (key === "fallback") {
      if (parseName(value).edition !== "ce")
        throw new Error(`${at}: a fallback must be a community core`);
      req.fallback = value;
    } else if (key === "server") {
      if (!SERVER.test(value))
        throw new Error(
          `${at}: server must be an https address without credentials`,
        );
      req.server = value;
    } else if (key === "signing-key") {
      if (!KEY.test(value))
        throw new Error(
          `${at}: signing-key must be ed25519:<base64 of 32 bytes>`,
        );
      req.signingKey = value;
    } else if (key === "product") {
      if (!SAFE.test(value)) throw new Error(`${at}: bad product id`);
      req.product = value;
    } else if (key === "need") {
      if (!ROLE.test(value)) throw new Error(`${at}: bad file role ${value}`);
      if (seen.has(value)) throw new Error(`${at}: ${value} listed twice`);
      seen.add(value);
      req.need.push(value);
    } else if (key === "have") {
      const [role, hash] = rest;
      if (!ROLE.test(role || "") || !HASH.test(hash || ""))
        throw new Error(`${at}: have needs a role and a sha256`);
      req.have[role] = hash;
    } else throw new Error(`${at}: unknown key ${key}`);
  }
  if (req.format !== FORMAT) throw new Error("first line must be: corereq 1");
  if (!req.name) throw new Error("name is required");
  if (!req.need.length) throw new Error("at least one need line is required");
  const parsed = { ...req, ...parseName(req.name) };
  if (parsed.edition === "be" && (!req.server || !req.signingKey))
    throw new Error("a business core needs a server and a signing-key");
  if (parsed.edition === "ce" && (req.server || req.signingKey))
    throw new Error("a community core never carries a server or a key");
  return parsed;
}

export function format(req) {
  const lines = [
    "# KagNode. Core request. Lists the files a deployment needs, nothing else.",
    `corereq ${FORMAT}`,
    `name ${coreName(req)}`,
  ];
  if (req.product) lines.push(`product ${req.product}`);
  if (req.fallback) lines.push(`fallback ${req.fallback}`);
  if (req.server) lines.push(`server ${req.server}`);
  if (req.signingKey) lines.push(`signing-key ${req.signingKey}`);
  for (const role of [...new Set(req.need)].sort()) lines.push(`need ${role}`);
  for (const [role, hash] of Object.entries(req.have || {}).sort())
    lines.push(`have ${role} ${hash}`);
  const text = lines.join("\n") + "\n";
  parse(text);
  return text;
}

/**
 * Work out what to download. `index` maps each role to {file, sha256, size} for the requested
 * version (the signed index the server publishes). `store` is the set of sha256 values already
 * held by other deployments. Files whose hash is already stored are reused, never fetched twice.
 */
export function plan({ req, index, store }) {
  const held = new Set(store || []);
  const fetch = [],
    reuse = [],
    unknown = [];
  for (const role of req.need) {
    const entry = index[role];
    if (!entry) unknown.push(role);
    else if (held.has(entry.sha256)) reuse.push({ role, sha256: entry.sha256 });
    else fetch.push({ role, ...entry });
  }
  return {
    fetch,
    reuse,
    unknown,
    bytes: fetch.reduce((n, f) => n + (f.size || 0), 0),
  };
}

/** The request the Daemon sends: the same corereq.txt, plus a have line for every file it already holds. */
export function request({ req, index, store }) {
  const held = new Set(store || []);
  const have = {};
  for (const role of req.need)
    if (index[role] && held.has(index[role].sha256))
      have[role] = index[role].sha256;
  return format({ ...req, need: req.need.filter((r) => !have[r]), have });
}

const sha256 = (buffer) =>
  "sha256:" + createHash("sha256").update(buffer).digest("hex");

/** Build the role index from a Core dist folder. */
export function indexDist(dist) {
  const manifest = JSON.parse(
    readFileSync(join(dist, "manifest.json"), "utf8"),
  );
  const roles = {
    theme: manifest.entrypoints.theme,
    script: manifest.entrypoints.script,
    style: manifest.entrypoints.style,
    mark: "mark.svg",
    bundle: "bundle.json",
  };
  const categories = join(dist, "icons", "categories");
  try {
    for (const f of readdirSync(categories))
      if (f.endsWith(".mjs"))
        roles[`icons/${f.slice(0, -4)}`] = `icons/categories/${f}`;
  } catch {}
  const index = {};
  for (const [role, file] of Object.entries(roles)) {
    const path = join(dist, file);
    try {
      statSync(path);
    } catch {
      continue;
    }
    const data = readFileSync(path);
    index[role] = { file, sha256: sha256(data), size: data.length };
  }
  return index;
}

function cli(args) {
  const [command, ...rest] = args;
  const opt = {};
  for (let i = 0; i < rest.length; i += 2)
    opt[rest[i].replace(/^--/, "")] = rest[i + 1];
  if (command === "make") {
    const text = format({
      edition: opt.edition,
      version: opt.version,
      channel: opt.channel || "",
      product: opt.product,
      fallback: opt.fallback,
      server: opt.server,
      signingKey: opt["signing-key"],
      need: (opt.need || "theme,script,style,mark").split(","),
    });
    if (opt.out) writeFileSync(opt.out, text);
    else process.stdout.write(text);
  } else if (command === "index") {
    process.stdout.write(
      JSON.stringify(indexDist(resolve(opt.dist || "dist")), null, 2) + "\n",
    );
  } else if (command === "plan") {
    const req = parse(readFileSync(opt.req, "utf8"));
    const index = JSON.parse(readFileSync(opt.index, "utf8"));
    const store = opt.store
      ? readFileSync(opt.store, "utf8").split(/\s+/).filter(Boolean)
      : [];
    process.stdout.write(
      JSON.stringify(plan({ req, index, store }), null, 2) + "\n",
    );
  } else {
    process.stderr.write(
      "usage: corereq.mjs make|index|plan --help-in docs/CORE-DELIVERY.md\n",
    );
    process.exit(2);
  }
}

if (
  process.argv[1] &&
  pathToFileURL(process.argv[1]).href === import.meta.url
) {
  try {
    cli(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(`corereq: ${error.message}\n`);
    process.exit(1);
  }
}

export const here = dirname(fileURLToPath(import.meta.url));
