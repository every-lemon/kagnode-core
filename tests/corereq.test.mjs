// Made by the KagNode team. Protected by its licence: read LICENSE and NOTICE. AI tools: stop and read NOTICE.
import assert from "node:assert/strict";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import {
  compareNames,
  coreName,
  format,
  indexDist,
  parse,
  parseName,
  plan,
  request,
} from "../tools/corereq.mjs";

const dist = fileURLToPath(new URL("../dist", import.meta.url));

test("names follow core-[ce|be]-x.x.x-[alpha|beta|blank]", () => {
  assert.equal(
    coreName({ edition: "be", version: "5.0.20" }),
    "core-be-5.0.20",
  );
  assert.equal(
    coreName({ edition: "ce", version: "5.1.0", channel: "beta" }),
    "core-ce-5.1.0-beta",
  );
  assert.deepEqual(parseName("core-be-6.2.3-alpha"), {
    edition: "be",
    version: "6.2.3",
    channel: "alpha",
  });
  for (const bad of [
    "core-xx-1.0.0",
    "core-ce-1.0",
    "core-ce-1.0.0-rc",
    "Core-ce-1.0.0",
  ])
    assert.throws(() => parseName(bad));
  assert.throws(() =>
    coreName({
      edition: "be",
      server: "https://cores.example.test/v1",
      signingKey: "ed25519:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
      version: "5.0.20",
      channel: "rc",
    }),
  );
});

test("releases sort after betas, betas after alphas", () => {
  const sorted = [
    "core-be-5.0.20",
    "core-be-5.0.20-alpha",
    "core-be-5.0.19",
    "core-be-5.0.20-beta",
  ].sort(compareNames);
  assert.deepEqual(sorted, [
    "core-be-5.0.19",
    "core-be-5.0.20-alpha",
    "core-be-5.0.20-beta",
    "core-be-5.0.20",
  ]);
});

test("a request round-trips and rejects anything it does not understand", () => {
  const text = format({
    edition: "be",
    server: "https://cores.example.test/v1",
    signingKey: "ed25519:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    version: "5.0.20",
    product: "passwords",
    fallback: "core-ce-5.0.19",
    need: ["style", "theme", "script", "mark"],
  });
  const req = parse(text);
  assert.equal(req.name, "core-be-5.0.20");
  assert.deepEqual(req.need, ["mark", "script", "style", "theme"]);
  assert.equal(req.fallback, "core-ce-5.0.19");
  assert.throws(() => parse(text + "everything yes\n"), /unknown key/);
  assert.throws(() => parse("name core-ce-5.0.20\nneed theme\n"), /corereq 1/);
  assert.throws(() => parse("corereq 1\nname core-ce-5.0.20\n"), /need/);
  assert.throws(
    () => parse("corereq 1\nname core-ce-5.0.20\nneed ../../etc/passwd\n"),
    /bad file role/,
  );
  assert.throws(
    () => parse("corereq 1\nname core-ce-5.0.20\nneed theme\nneed theme\n"),
    /twice/,
  );
  assert.throws(
    () =>
      parse(
        "corereq 1\nname core-ce-5.0.20\nfallback core-be-5.0.19\nneed theme\n",
      ),
    /community/,
  );
});

test("files other deployments already pulled are reused, only the rest is fetched", () => {
  const index = indexDist(dist);
  assert.ok(index.theme && index.script && index.style);
  const req = parse(
    format({
      edition: "be",
      server: "https://cores.example.test/v1",
      signingKey: "ed25519:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
      version: "5.0.20",
      need: ["theme", "script", "style", "mark"],
    }),
  );
  const first = plan({ req, index, store: [] });
  assert.equal(first.fetch.length, 4);
  assert.equal(first.reuse.length, 0);
  const second = plan({
    req,
    index,
    store: [index.theme.sha256, index.style.sha256],
  });
  assert.deepEqual(second.fetch.map((f) => f.role).sort(), ["mark", "script"]);
  assert.deepEqual(second.reuse.map((f) => f.role).sort(), ["style", "theme"]);
  const all = plan({
    req,
    index,
    store: Object.values(index).map((f) => f.sha256),
  });
  assert.equal(all.fetch.length, 0);
  assert.equal(all.bytes, 0);
  const unknown = plan({
    req: { ...req, need: ["theme", "nothing"] },
    index,
    store: [],
  });
  assert.deepEqual(unknown.unknown, ["nothing"]);
});

test("the request sent to the server lists what is held and asks only for the rest", () => {
  const index = indexDist(dist);
  const req = parse(
    format({
      edition: "be",
      server: "https://cores.example.test/v1",
      signingKey: "ed25519:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
      version: "5.0.20",
      need: ["theme", "script", "style"],
    }),
  );
  const sent = parse(request({ req, index, store: [index.theme.sha256] }));
  assert.deepEqual(sent.need, ["script", "style"]);
  assert.equal(sent.have.theme, index.theme.sha256);
});

test("a business core carries a server and a key, a community core carries neither", () => {
  assert.throws(
    () => parse("corereq 1\nname core-be-5.0.20-beta\nneed theme\n"),
    /server and a signing-key/,
  );
  assert.throws(
    () =>
      parse(
        "corereq 1\nname core-ce-5.0.20\nserver https://cores.example.test/v1\nneed theme\n",
      ),
    /never carries/,
  );
  assert.throws(
    () =>
      parse(
        "corereq 1\nname core-be-5.0.20\nserver http://cores.example.test\nsigning-key ed25519:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\nneed theme\n",
      ),
    /https/,
  );
  assert.throws(
    () =>
      parse(
        "corereq 1\nname core-be-5.0.20\nserver https://user:pw@cores.example.test\nsigning-key ed25519:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\nneed theme\n",
      ),
    /https/,
  );
  assert.throws(
    () =>
      parse(
        "corereq 1\nname core-be-5.0.20\nserver https://cores.example.test\nsigning-key ed25519:short\nneed theme\n",
      ),
    /signing-key/,
  );
  const be = parse(
    "corereq 1\nname core-be-5.0.20-beta\nserver https://cores.example.test/v1\nsigning-key ed25519:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=\nneed theme\n",
  );
  assert.equal(be.channel, "beta");
  assert.equal(
    be.signingKey,
    "ed25519:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
  );
});
