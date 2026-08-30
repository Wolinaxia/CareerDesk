import assert from "node:assert/strict";
import { test } from "node:test";

import {
  codePointLength,
  draftFromBlock,
  emptyDraft,
  formatPeriod,
  normalizeDraft,
} from "./personalMaterialDraft.ts";

function validDraft(overrides = {}) {
  return {
    ...emptyDraft(),
    language: "en",
    title: "Title",
    body: "Body",
    ...overrides,
  };
}

test("empty drafts and block-backed drafts preserve editor field shapes", () => {
  assert.deepEqual(draftFromBlock(null), emptyDraft());
  assert.deepEqual(draftFromBlock({
    block_type: "work",
    language: "en",
    title: "Platform migration",
    organization: null,
    period_start: "2025-01",
    period_end: null,
    body: "Migrated the platform.",
    tags: ["Python", "FastAPI"],
  }), {
    block_type: "work",
    language: "en",
    title: "Platform migration",
    organization: "",
    period_start: "2025-01",
    period_end: "",
    body: "Migrated the platform.",
    tagsText: "Python, FastAPI",
  });
});

for (const { name, periods, field, error } of [
  {
    name: "a malformed start month",
    periods: { period_start: "2025-13" },
    field: "period_start",
    error: "period_start_invalid",
  },
  {
    name: "a malformed end month",
    periods: { period_start: "2025-01", period_end: "2025-00" },
    field: "period_end",
    error: "period_end_invalid",
  },
  {
    name: "an end month without a start month",
    periods: { period_end: "2025-02" },
    field: "period_end",
    error: "period_end_without_start",
  },
  {
    name: "an end month before the start month",
    periods: { period_start: "2025-02", period_end: "2025-01" },
    field: "period_end",
    error: "period_end_before_start",
  },
]) {
  test(`normalizeDraft distinguishes ${name}`, () => {
    const result = normalizeDraft(validDraft(periods));
    assert.equal(result.errors[field], error);
  });
}

test("normalizeDraft accepts valid full and ongoing month ranges", () => {
  const ongoing = normalizeDraft(validDraft({ period_start: "2025-01" }));
  assert.deepEqual(ongoing.errors, {});
  assert.equal(ongoing.input.period_start, "2025-01");
  assert.equal(ongoing.input.period_end, null);

  const full = normalizeDraft(validDraft({
    period_start: "2025-01",
    period_end: "2025-12",
  }));
  assert.deepEqual(full.errors, {});
  assert.equal(full.input.period_end, "2025-12");
});

test("normalizeDraft trims tags, drops empties, and deduplicates without changing first casing", () => {
  const result = normalizeDraft(validDraft({
    tagsText: "  Python, , python， TypeScript, TYPESCRIPT  ",
  }));
  assert.deepEqual(result.errors, {});
  assert.deepEqual(result.input.tags, ["Python", "TypeScript"]);
});

for (const { name, accepted, rejected, field, error } of [
  {
    name: "title length",
    accepted: { title: "a".repeat(120) },
    rejected: { title: "a".repeat(121) },
    field: "title",
    error: "title_too_long",
  },
  {
    name: "body length",
    accepted: { body: "a".repeat(8_000) },
    rejected: { body: "a".repeat(8_001) },
    field: "body",
    error: "body_too_long",
  },
  {
    name: "single tag length",
    accepted: { tagsText: "a".repeat(24) },
    rejected: { tagsText: "a".repeat(25) },
    field: "tags",
    error: "tag_too_long",
  },
  {
    name: "tag count",
    accepted: { tagsText: Array.from({ length: 12 }, (_, index) => `tag-${index}`).join(",") },
    rejected: { tagsText: Array.from({ length: 13 }, (_, index) => `tag-${index}`).join(",") },
    field: "tags",
    error: "too_many_tags",
  },
]) {
  test(`normalizeDraft enforces the exact ${name} boundary`, () => {
    assert.equal(normalizeDraft(validDraft(accepted)).errors[field], undefined);
    assert.equal(normalizeDraft(validDraft(rejected)).errors[field], error);
  });
}

test("title limits count astral-plane emoji as one code point", () => {
  const title = "😀".repeat(120);
  assert.equal(codePointLength(title), 120);
  assert.equal(normalizeDraft(validDraft({ title })).errors.title, undefined);
});

test("formatPeriod renders ongoing and complete ranges", () => {
  assert.equal(
    formatPeriod({ period_start: "2025-01", period_end: null }, "Present"),
    "2025.01 - Present",
  );
  assert.equal(
    formatPeriod({ period_start: "2025-01", period_end: "2025-12" }, "Present"),
    "2025.01 - 2025.12",
  );
});
