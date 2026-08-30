export type MaterialBlockType =
  | "project"
  | "work"
  | "education"
  | "skill"
  | "intro"
  | "other";

export type MaterialLanguage = "zh" | "en";

export type MaterialBlock = {
  id: number;
  block_type: MaterialBlockType;
  language: MaterialLanguage;
  title: string;
  organization: string | null;
  period_start: string | null;
  period_end: string | null;
  body: string;
  tags: string[];
  archived: boolean;
  revision: number;
  created_time: string;
  updated_time: string;
};

export type MaterialBlockInput = Omit<
  MaterialBlock,
  "id" | "archived" | "revision" | "created_time" | "updated_time"
>;

const BLOCK_TYPES: ReadonlySet<string> = new Set([
  "project",
  "work",
  "education",
  "skill",
  "intro",
  "other",
]);
const LANGUAGES: ReadonlySet<string> = new Set(["zh", "en"]);

function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} has an invalid response shape`);
  }
  return value as Record<string, unknown>;
}

function text(value: unknown, label: string): string {
  if (typeof value !== "string") throw new Error(`${label} must be text`);
  return value;
}

function nullableText(value: unknown, label: string): string | null {
  return value === null ? null : text(value, label);
}

function integer(value: unknown, label: string, minimum = 1): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < minimum) {
    throw new Error(`${label} must be an integer`);
  }
  return value;
}

function boolean(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") throw new Error(`${label} must be boolean`);
  return value;
}

function blockType(value: unknown): MaterialBlockType {
  if (typeof value !== "string" || !BLOCK_TYPES.has(value)) {
    throw new Error("material block type is invalid");
  }
  return value as MaterialBlockType;
}

function language(value: unknown): MaterialLanguage {
  if (typeof value !== "string" || !LANGUAGES.has(value)) {
    throw new Error("material language is invalid");
  }
  return value as MaterialLanguage;
}

function tags(value: unknown): string[] {
  if (!Array.isArray(value)) throw new Error("material tags must be an array");
  return value.map((item) => text(item, "material tag"));
}

export function parseMaterialBlock(value: unknown): MaterialBlock {
  const item = object(value, "material block");
  return {
    id: integer(item.id, "material block id"),
    block_type: blockType(item.block_type),
    language: language(item.language),
    title: text(item.title, "material title"),
    organization: nullableText(item.organization, "material organization"),
    period_start: nullableText(item.period_start, "material start period"),
    period_end: nullableText(item.period_end, "material end period"),
    body: text(item.body, "material body"),
    tags: tags(item.tags),
    archived: boolean(item.archived, "material archive state"),
    revision: integer(item.revision, "material revision"),
    created_time: text(item.created_time, "material created time"),
    updated_time: text(item.updated_time, "material updated time"),
  };
}

export function parseMaterialBlocks(value: unknown): MaterialBlock[] {
  const response = object(value, "material blocks response");
  if (!Array.isArray(response.items)) throw new Error("material block items are invalid");
  return response.items.map(parseMaterialBlock);
}
