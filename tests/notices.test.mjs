import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";
import { readNotice, dismissNotice } from "../dist/node/kagnode-core.mjs";

test("public Node summaries isolate subjects and refuse malformed or private manager output", async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "kn-notices-"));
  fs.mkdirSync(path.join(directory, "run"));
  const previous = process.env.KAGNODE_CORE_ROOT;
  process.env.KAGNODE_CORE_ROOT = directory;
  const notice = {
    id: "a".repeat(64),
    version: "5.0.7",
    title: "Refined navigation",
    items: ["Clearer controls."],
  };
  let payload = { available: true, notice };
  const requests = [];
  const server = http.createServer((request, response) => {
    let body = "";
    request.on("data", (part) => {
      body += part;
    });
    request.on("end", () => {
      requests.push(JSON.parse(body));
      response.setHeader("Content-Type", "application/json");
      response.end(JSON.stringify(payload));
    });
  });
  await new Promise((resolve) =>
    server.listen(path.join(directory, "run/fixture.sock"), resolve),
  );
  try {
    const receipts = new Set();
    const read = (subject) =>
      readNotice("fixture", subject, (user, id) =>
        receipts.has(user + ":" + id),
      );
    assert.deepEqual(await read("alice"), { available: true, notice });
    await dismissNotice("fixture", "alice", notice.id, (user, id) => {
      receipts.add(user + ":" + id);
    });
    assert.deepEqual(await read("alice"), { available: true, notice: null });
    assert.deepEqual(await read("bob"), { available: true, notice });
    await assert.rejects(
      dismissNotice("fixture", "bob", "b".repeat(64), () =>
        assert.fail("Stale ID persisted"),
      ),
      /no longer available/,
    );
    assert.ok(requests.every((request) => request.action === "summary"));
    for (const invalid of [
      { ...notice, secret: "/private/path" },
      { ...notice, title: "<script>" },
      { ...notice, items: [] },
    ]) {
      payload = { available: true, notice: invalid };
      assert.deepEqual(await read("bob"), { available: false, notice: null });
    }
    assert.deepEqual(await read(""), { available: false, notice: null });
  } finally {
    await new Promise((resolve) => server.close(resolve));
    if (previous === undefined) delete process.env.KAGNODE_CORE_ROOT;
    else process.env.KAGNODE_CORE_ROOT = previous;
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
