export function mergeMaterialBodies(bodies: string[]): string {
  return bodies
    .map((body) => body.trim())
    .filter((body) => body.length > 0)
    .join("\n\n");
}
