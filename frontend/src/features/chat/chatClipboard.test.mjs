import assert from "node:assert/strict";
import test from "node:test";
import { clipboardImages, normalizeClipboardImage } from "./chatClipboard.ts";

test("clipboard screenshots receive a stable supported filename", () => {
  const image = new File(["pixels"], "image", { type: "image/png", lastModified: 123 });
  const normalized = normalizeClipboardImage(image, 0, new Date("2026-08-20T02:30:45.000Z"));

  assert.equal(normalized?.name, "pasted-image-20260820T023045Z-1.png");
  assert.equal(normalized?.type, "image/png");
  assert.equal(normalized?.lastModified, 123);
});

test("clipboard image extraction ignores text and unsupported image types", () => {
  const png = new File(["png"], "", { type: "image/png" });
  const items = [
    { kind: "string", type: "text/plain", getAsFile: () => null },
    { kind: "file", type: "image/tiff", getAsFile: () => new File(["tiff"], "", { type: "image/tiff" }) },
    { kind: "file", type: "image/png", getAsFile: () => png },
  ];

  const images = clipboardImages(items, new Date("2026-08-20T02:30:45.000Z"));
  assert.equal(images.length, 1);
  assert.match(images[0].name, /\.png$/);
});

test("an existing supported image filename is preserved", () => {
  const image = new File(["pixels"], "screenshot.webp", { type: "image/webp" });
  assert.equal(normalizeClipboardImage(image, 0), image);
});
