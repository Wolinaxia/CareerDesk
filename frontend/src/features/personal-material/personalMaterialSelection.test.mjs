import assert from "node:assert/strict";
import { test } from "node:test";

import { mergeMaterialBodies } from "./personalMaterialSelection.ts";

test("multiple material bodies are joined with one blank line", () => {
  assert.equal(mergeMaterialBodies(["First", "Second", "Third"]), "First\n\nSecond\n\nThird");
});

test("empty and whitespace-only material bodies are omitted", () => {
  assert.equal(mergeMaterialBodies(["", "  ", "First", "\n\t", "Second"]), "First\n\nSecond");
});

test("one material body has no extra blank lines", () => {
  assert.equal(mergeMaterialBodies(["  Only body  "]), "Only body");
});

test("an empty material selection returns empty text", () => {
  assert.equal(mergeMaterialBodies([]), "");
});

test("line breaks inside a material body are preserved", () => {
  assert.equal(
    mergeMaterialBodies(["  First line\nSecond line\n\nFourth line  ", "Next body"]),
    "First line\nSecond line\n\nFourth line\n\nNext body",
  );
});
