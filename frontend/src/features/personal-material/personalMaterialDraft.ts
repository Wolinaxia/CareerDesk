import type {
  MaterialBlock,
  MaterialBlockInput,
  MaterialBlockType,
  MaterialLanguage,
} from "./personalMaterialContract";

export type MaterialDraft = {
  block_type: MaterialBlockType;
  language: MaterialLanguage;
  title: string;
  organization: string;
  period_start: string;
  period_end: string;
  body: string;
  tagsText: string;
};

export type DraftField =
  | "title"
  | "organization"
  | "period_start"
  | "period_end"
  | "body"
  | "tags";

export type DraftErrorCode =
  | "title_required"
  | "title_too_long"
  | "organization_too_long"
  | "body_required"
  | "body_too_long"
  | "period_start_invalid"
  | "period_end_invalid"
  | "period_end_without_start"
  | "period_end_before_start"
  | "tag_too_long"
  | "too_many_tags";

export type DraftErrorCodes = Partial<Record<DraftField, DraftErrorCode>>;

export const MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;

export function codePointLength(value: string): number {
  return Array.from(value).length;
}

export function emptyDraft(): MaterialDraft {
  return {
    block_type: "project",
    language: "zh",
    title: "",
    organization: "",
    period_start: "",
    period_end: "",
    body: "",
    tagsText: "",
  };
}

export function draftFromBlock(block: MaterialBlock | null): MaterialDraft {
  if (!block) return emptyDraft();
  return {
    block_type: block.block_type,
    language: block.language,
    title: block.title,
    organization: block.organization ?? "",
    period_start: block.period_start ?? "",
    period_end: block.period_end ?? "",
    body: block.body,
    tagsText: block.tags.join(", "),
  };
}

export function normalizeDraft(
  draft: MaterialDraft,
): { input: MaterialBlockInput; errors: DraftErrorCodes } {
  const errors: DraftErrorCodes = {};
  const title = draft.title.trim();
  const organization = draft.organization.trim();
  const body = draft.body.trim();
  const periodStart = draft.period_start.trim();
  const periodEnd = draft.period_end.trim();
  if (!title) errors.title = "title_required";
  else if (codePointLength(title) > 120) {
    errors.title = "title_too_long";
  }
  if (organization && codePointLength(organization) > 120) {
    errors.organization = "organization_too_long";
  }
  if (!body) errors.body = "body_required";
  else if (codePointLength(body) > 8_000) {
    errors.body = "body_too_long";
  }
  if (periodStart && !MONTH_PATTERN.test(periodStart)) {
    errors.period_start = "period_start_invalid";
  }
  if (periodEnd && !MONTH_PATTERN.test(periodEnd)) {
    errors.period_end = "period_end_invalid";
  } else if (periodEnd && !periodStart) {
    errors.period_end = "period_end_without_start";
  } else if (
    periodStart
    && periodEnd
    && MONTH_PATTERN.test(periodStart)
    && periodEnd < periodStart
  ) {
    errors.period_end = "period_end_before_start";
  }

  const tags: string[] = [];
  const seenTags = new Set<string>();
  for (const rawTag of draft.tagsText.split(/[,，]/)) {
    const tag = rawTag.trim();
    if (!tag) continue;
    if (codePointLength(tag) > 24) {
      errors.tags = "tag_too_long";
      break;
    }
    const key = tag.toLocaleLowerCase();
    if (!seenTags.has(key)) {
      seenTags.add(key);
      tags.push(tag);
    }
  }
  if (!errors.tags && tags.length > 12) {
    errors.tags = "too_many_tags";
  }

  return {
    errors,
    input: {
      block_type: draft.block_type,
      language: draft.language,
      title,
      organization: organization || null,
      period_start: periodStart || null,
      period_end: periodEnd || null,
      body,
      tags,
    },
  };
}

export function formatPeriod(block: MaterialBlock, ongoingLabel: string): string | null {
  const format = (value: string) => value.replace("-", ".");
  if (block.period_start && block.period_end) {
    return `${format(block.period_start)} - ${format(block.period_end)}`;
  }
  if (block.period_start) {
    return `${format(block.period_start)} - ${ongoingLabel}`;
  }
  return null;
}
