// Run after npm run build. Requires Express in the surrounding example project.
import express from "express";
import { installCore } from "../dist/node/kagnode-core.mjs";
const app = express();
installCore(app, { appId: "example" });
app.get("/", (_q, r) =>
  r.send(
    `<!doctype html><html><head><title>KagNode Core example</title><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><aside class="sidebar"><a class="brand" href="/">KagNode.</a><nav><a href="/">Overview</a><a href="#controls">Controls</a></nav></aside><div class="workspace"><main style="padding:28px"><h1>Components</h1><section id="controls"><label>Plan<select><option>Draft</option><option>Review</option></select></label><label>Quantity<input type="number" value="1" min="1" max="9"></label><label>Date<input type="date"></label></section></main></div></body></html>`,
  ),
);
app.listen(8120, "127.0.0.1");
