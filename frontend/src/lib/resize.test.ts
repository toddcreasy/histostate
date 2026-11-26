// The website's resize must give the same bytes as Pillow, or the model sees a different tile
// in the browser than in `histostate ask`. Fixtures come from scripts/make_resize_fixtures.py.
//   npm test

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { gunzipSync } from "node:zlib";

import { resizeBicubic } from "./resize.ts";

type Case = { name: string; width: number; height: number; input: string; output: string };

const cases: Case[] = JSON.parse(
  gunzipSync(readFileSync(new URL("./resize.fixtures.json.gz", import.meta.url))).toString(),
);

for (const c of cases) {
  test(`matches Pillow: ${c.name}`, () => {
    const input = new Uint8Array(Buffer.from(c.input, "base64"));
    const expected = new Uint8Array(Buffer.from(c.output, "base64"));
    const got = resizeBicubic(input, c.width, c.height, 64, 64);
    let differ = 0;
    for (let i = 0; i < expected.length; i++) if (got[i] !== expected[i]) differ++;
    assert.equal(differ, 0, `${differ} of ${expected.length} bytes differ from Pillow`);
  });
}
