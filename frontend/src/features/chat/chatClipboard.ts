const IMAGE_EXTENSION_BY_MIME: Readonly<Record<string, string>> = {
  "image/gif": "gif",
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};

const SUPPORTED_IMAGE_NAME = /\.(?:gif|jpe?g|png|webp)$/i;

export function normalizeClipboardImage(file: File, index: number, now = new Date()): File | null {
  if (!file.type.toLowerCase().startsWith("image/")) return null;
  if (SUPPORTED_IMAGE_NAME.test(file.name)) return file;
  const extension = IMAGE_EXTENSION_BY_MIME[file.type.toLowerCase()];
  if (!extension) return null;
  const timestamp = now.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
  return new File([file], `pasted-image-${timestamp}-${index + 1}.${extension}`, {
    type: file.type,
    lastModified: file.lastModified,
  });
}

export function clipboardImages(items: Iterable<DataTransferItem>, now = new Date()): File[] {
  const images: File[] = [];
  for (const item of items) {
    if (item.kind !== "file" || !item.type.toLowerCase().startsWith("image/")) continue;
    const file = item.getAsFile();
    if (!file) continue;
    const normalized = normalizeClipboardImage(file, images.length, now);
    if (normalized) images.push(normalized);
  }
  return images;
}
