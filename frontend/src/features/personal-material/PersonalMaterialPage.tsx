import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocalizer, type Localize } from "../../i18n/useLocalizer";
import { HttpError } from "../../shared/api/transport";
import { copyToClipboard } from "./copyToClipboard";
import {
  archiveMaterialBlock,
  createMaterialBlock,
  getMaterialBlocks,
  restoreMaterialBlock,
  updateMaterialBlock,
} from "./personalMaterialApi";
import {
  type MaterialBlock,
  type MaterialBlockInput,
  type MaterialBlockType,
  type MaterialLanguage,
} from "./personalMaterialContract";
import {
  draftFromBlock,
  formatPeriod,
  normalizeDraft,
  type DraftErrorCode,
  type DraftField,
  type MaterialDraft,
} from "./personalMaterialDraft";
import { mergeMaterialBodies } from "./personalMaterialSelection";

const BLOCK_TYPES: MaterialBlockType[] = [
  "project",
  "work",
  "education",
  "skill",
  "intro",
  "other",
];

type LanguageFilter = "all" | MaterialLanguage;
type DraftErrors = Partial<Record<DraftField, string>>;
type EditorState = { key: string; block: MaterialBlock | null };
type CopyFallback = { key: string; text: string };

function localizeDraftError(error: DraftErrorCode, l: Localize): string {
  switch (error) {
    case "title_required":
      return l("请输入标题", "Enter a title");
    case "title_too_long":
      return l("标题不能超过 120 个字符", "Title cannot exceed 120 characters");
    case "organization_too_long":
      return l("组织名称不能超过 120 个字符", "Organization cannot exceed 120 characters");
    case "body_required":
      return l("请输入正文", "Enter the body text");
    case "body_too_long":
      return l("正文不能超过 8000 个字符", "Body cannot exceed 8,000 characters");
    case "period_start_invalid":
      return l("开始月份必须使用 YYYY-MM 格式", "Start month must use YYYY-MM format");
    case "period_end_invalid":
      return l("结束月份必须使用 YYYY-MM 格式", "End month must use YYYY-MM format");
    case "period_end_without_start":
      return l("填写结束月份前必须先填写开始月份", "Enter a start month before the end month");
    case "period_end_before_start":
      return l("结束月份不能早于开始月份", "End month cannot be before start month");
    case "tag_too_long":
      return l("单个标签不能超过 24 个字符", "Each tag cannot exceed 24 characters");
    case "too_many_tags":
      return l("每块素材最多 12 个标签", "Each material block can have at most 12 tags");
  }
}

function useMaterialLabels() {
  const l = useLocalizer();
  return {
    type: {
      project: l("项目", "Project"),
      work: l("工作", "Work"),
      education: l("教育", "Education"),
      skill: l("技能", "Skill"),
      intro: l("简介", "Introduction"),
      other: l("其他", "Other"),
    } satisfies Record<MaterialBlockType, string>,
  };
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <span className="mt-1 block text-xs text-bad">{message}</span>;
}

function MaterialEditor({
  block,
  busy,
  onCancel,
  onSave,
}: {
  block: MaterialBlock | null;
  busy: boolean;
  onCancel: () => void;
  onSave: (input: MaterialBlockInput) => Promise<void>;
}) {
  const l = useLocalizer();
  const labels = useMaterialLabels();
  const [draft, setDraft] = useState<MaterialDraft>(() => draftFromBlock(block));
  const [errors, setErrors] = useState<DraftErrors>({});
  const field = "input mt-1 w-full";

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const result = normalizeDraft(draft);
    const localizedErrors = Object.fromEntries(
      Object.entries(result.errors).map(([fieldName, error]) => [
        fieldName,
        localizeDraftError(error, l),
      ]),
    );
    setErrors(localizedErrors);
    if (Object.keys(result.errors).length > 0) return;
    await onSave(result.input);
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="card mb-6 p-5 sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">
            {block ? l("编辑素材", "Edit material") : l("新建素材", "New material")}
          </h2>
          <p className="mt-1 text-sm text-ink-3">
            {l("把可复用的经历整理成独立素材块。", "Save reusable experience as a focused block.")}
          </p>
        </div>
        <button type="button" className="btn btn-sm" onClick={onCancel} disabled={busy}>
          {l("取消", "Cancel")}
        </button>
      </div>

      <fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2 disabled:opacity-70">
        <label className="text-xs font-medium text-ink-2">
          {l("类型", "Type")}
          <select
            className={field}
            value={draft.block_type}
            onChange={(event) => setDraft({
              ...draft,
              block_type: event.target.value as MaterialBlockType,
            })}
          >
            {BLOCK_TYPES.map((type) => (
              <option key={type} value={type}>{labels.type[type]}</option>
            ))}
          </select>
        </label>
        <label className="text-xs font-medium text-ink-2">
          {l("语言", "Language")}
          <select
            className={field}
            value={draft.language}
            onChange={(event) => setDraft({
              ...draft,
              language: event.target.value as MaterialLanguage,
            })}
          >
            <option value="zh">{l("中文", "Chinese")}</option>
            <option value="en">English</option>
          </select>
        </label>
        <label className="text-xs font-medium text-ink-2 sm:col-span-2">
          {l("标题", "Title")}
          <input
            autoFocus
            className={field}
            value={draft.title}
            onChange={(event) => setDraft({ ...draft, title: event.target.value })}
          />
          <FieldError message={errors.title} />
        </label>
        <label className="text-xs font-medium text-ink-2 sm:col-span-2">
          {l("组织（可选）", "Organization (optional)")}
          <input
            className={field}
            value={draft.organization}
            onChange={(event) => setDraft({ ...draft, organization: event.target.value })}
          />
          <FieldError message={errors.organization} />
        </label>
        <label className="text-xs font-medium text-ink-2">
          {l("开始月份（可选）", "Start month (optional)")}
          <input
            type="month"
            className={field}
            value={draft.period_start}
            onChange={(event) => setDraft({ ...draft, period_start: event.target.value })}
          />
          <FieldError message={errors.period_start} />
        </label>
        <label className="text-xs font-medium text-ink-2">
          {l("结束月份（留空表示至今）", "End month (leave empty for present)")}
          <input
            type="month"
            className={field}
            value={draft.period_end}
            onChange={(event) => setDraft({ ...draft, period_end: event.target.value })}
          />
          <FieldError message={errors.period_end} />
        </label>
        <label className="text-xs font-medium text-ink-2 sm:col-span-2">
          {l("正文", "Body")}
          <textarea
            className={`${field} min-h-40 resize-y`}
            value={draft.body}
            onChange={(event) => setDraft({ ...draft, body: event.target.value })}
          />
          <FieldError message={errors.body} />
        </label>
        <label className="text-xs font-medium text-ink-2 sm:col-span-2">
          {l("标签（用逗号分隔）", "Tags (comma separated)")}
          <input
            className={field}
            value={draft.tagsText}
            onChange={(event) => setDraft({ ...draft, tagsText: event.target.value })}
          />
          <FieldError message={errors.tags} />
        </label>
      </fieldset>

      <div className="mt-5 flex justify-end gap-2">
        <button type="button" className="btn" onClick={onCancel} disabled={busy}>
          {l("取消", "Cancel")}
        </button>
        <button type="submit" className="btn-primary" disabled={busy}>
          {busy ? l("保存中…", "Saving…") : l("保存", "Save")}
        </button>
      </div>
    </form>
  );
}

export function PersonalMaterialPage() {
  const l = useLocalizer();
  const labels = useMaterialLabels();
  const [blocks, setBlocks] = useState<MaterialBlock[]>([]);
  const [showArchived, setShowArchived] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [search, setSearch] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<Set<MaterialBlockType>>(
    () => new Set(),
  );
  const [languageFilter, setLanguageFilter] = useState<LanguageFilter>("all");
  const [selectedTags, setSelectedTags] = useState<Set<string>>(() => new Set());
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(() => new Set());
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [editorBusy, setEditorBusy] = useState(false);
  const [busyBlockId, setBusyBlockId] = useState<number | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [copyAnnouncement, setCopyAnnouncement] = useState("");
  const [copyFallback, setCopyFallback] = useState<CopyFallback | null>(null);
  const refreshEpochRef = useRef(0);
  const refreshControllerRef = useRef<AbortController | null>(null);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    refreshControllerRef.current?.abort();
    const controller = new AbortController();
    const epoch = ++refreshEpochRef.current;
    refreshControllerRef.current = controller;
    setLoading(true);
    setLoadError("");
    try {
      const items = await getMaterialBlocks(showArchived, controller.signal);
      if (epoch !== refreshEpochRef.current || controller.signal.aborted) return;
      setBlocks(items);
      setSelectedIds((current) => current.filter(
        (id) => items.some((item) => item.id === id),
      ));
    } catch (caught) {
      if (epoch !== refreshEpochRef.current || controller.signal.aborted) return;
      setLoadError(
        caught instanceof Error
          ? caught.message
          : l("素材加载失败", "Could not load materials"),
      );
    } finally {
      if (epoch === refreshEpochRef.current && !controller.signal.aborted) setLoading(false);
    }
  }, [l, showArchived]);

  useEffect(() => {
    void refresh();
    return () => refreshControllerRef.current?.abort();
  }, [refresh]);

  useEffect(() => () => {
    if (copyTimerRef.current !== null) clearTimeout(copyTimerRef.current);
  }, []);

  const availableTags = useMemo(() => {
    const byKey = new Map<string, string>();
    for (const block of blocks) {
      for (const tag of block.tags) {
        const key = tag.toLocaleLowerCase();
        if (!byKey.has(key)) byKey.set(key, tag);
      }
    }
    return [...byKey].sort((left, right) => left[1].localeCompare(right[1]));
  }, [blocks]);

  const filterTags = useMemo(() => {
    const byKey = new Map(availableTags);
    for (const tag of selectedTags) {
      if (!byKey.has(tag)) byKey.set(tag, tag);
    }
    return [...byKey].sort((left, right) => left[1].localeCompare(right[1]));
  }, [availableTags, selectedTags]);

  const availableTagKeys = useMemo(
    () => new Set(availableTags.map(([key]) => key)),
    [availableTags],
  );

  const hasActiveFilters = search.trim() !== ""
    || selectedTypes.size > 0
    || languageFilter !== "all"
    || selectedTags.size > 0;

  const filteredBlocks = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return blocks.filter((block) => {
      if (selectedTypes.size > 0 && !selectedTypes.has(block.block_type)) return false;
      if (languageFilter !== "all" && block.language !== languageFilter) return false;
      const blockTags = block.tags.map((tag) => tag.toLocaleLowerCase());
      if (![...selectedTags].every((tag) => blockTags.includes(tag))) return false;
      if (!query) return true;
      return [block.title, block.body, block.organization ?? "", ...block.tags]
        .some((value) => value.toLocaleLowerCase().includes(query));
    });
  }, [blocks, languageFilter, search, selectedTags, selectedTypes]);

  const selectedBlocks = useMemo(
    () => selectedIds
      .map((id) => blocks.find((block) => block.id === id))
      .filter((block): block is MaterialBlock => block !== undefined),
    [blocks, selectedIds],
  );

  function toggleType(type: MaterialBlockType) {
    setSelectedTypes((current) => {
      const next = new Set(current);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  function toggleTag(tag: string) {
    setSelectedTags((current) => {
      const next = new Set(current);
      if (next.has(tag)) next.delete(tag);
      else next.add(tag);
      return next;
    });
  }

  function toggleSelected(blockId: number) {
    setSelectedIds((current) => current.includes(blockId)
      ? current.filter((id) => id !== blockId)
      : [...current, blockId]);
  }

  function toggleExpanded(blockId: number) {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(blockId)) next.delete(blockId);
      else next.add(blockId);
      return next;
    });
  }

  function markCopied(key: string, announcement: string) {
    if (copyTimerRef.current !== null) clearTimeout(copyTimerRef.current);
    setCopiedKey(key);
    setCopyAnnouncement(announcement);
    copyTimerRef.current = setTimeout(() => {
      setCopiedKey(null);
      setCopyAnnouncement("");
    }, 2_000);
  }

  async function copyText(key: string, text: string, announcement: string) {
    setActionError("");
    if (await copyToClipboard(text)) {
      setCopyFallback(null);
      markCopied(key, announcement);
      return;
    }
    setCopiedKey(null);
    setCopyFallback({ key, text });
    setActionError(l(
      "无法写入剪贴板，请在下方文本框中全选并复制。",
      "Could not access the clipboard. Select and copy the text below.",
    ));
  }

  async function handleWriteError(caught: unknown) {
    if (caught instanceof HttpError && caught.status === 409) {
      setEditor(null);
      await refresh();
      setActionError(l(
        "这块素材已在另一个窗口被修改，已刷新，请重新编辑。",
        "This material was changed in another window. The list was refreshed; edit it again.",
      ));
      return;
    }
    if (caught instanceof HttpError && caught.status === 404) {
      setEditor(null);
      await refresh();
      setActionError(l(
        "这块素材已不存在。",
        "This material no longer exists.",
      ));
      return;
    }
    setActionError(
      caught instanceof Error ? caught.message : l("操作失败", "The operation failed"),
    );
  }

  async function saveMaterial(input: MaterialBlockInput) {
    setEditorBusy(true);
    setActionError("");
    try {
      const saved = editor?.block
        ? await updateMaterialBlock(editor.block.id, input, editor.block.revision)
        : await createMaterialBlock(input);
      setBlocks((current) => {
        if (saved.archived && !showArchived) {
          return current.filter((item) => item.id !== saved.id);
        }
        return [saved, ...current.filter((item) => item.id !== saved.id)];
      });
      setEditor(null);
    } catch (caught) {
      await handleWriteError(caught);
    } finally {
      setEditorBusy(false);
    }
  }

  async function changeArchived(block: MaterialBlock) {
    setBusyBlockId(block.id);
    setActionError("");
    try {
      const saved = block.archived
        ? await restoreMaterialBlock(block.id, block.revision)
        : await archiveMaterialBlock(block.id, block.revision);
      setBlocks((current) => {
        if (saved.archived && !showArchived) {
          return current.filter((item) => item.id !== saved.id);
        }
        return [saved, ...current.filter((item) => item.id !== saved.id)];
      });
      if (saved.archived) {
        setSelectedIds((current) => current.filter((id) => id !== saved.id));
      }
    } catch (caught) {
      await handleWriteError(caught);
    } finally {
      setBusyBlockId(null);
    }
  }

  return (
    <div className="pb-24">
      <span className="sr-only" aria-live="polite">{copyAnnouncement}</span>

      <div className="card mb-6 p-4 sm:p-5">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder={l("搜索标题、正文、组织或标签", "Search title, body, organization, or tags")}
              aria-label={l("搜索素材", "Search materials")}
              className="input min-w-0 flex-1"
            />
            <label className="flex shrink-0 items-center gap-2 text-sm text-ink-2">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(event) => setShowArchived(event.target.checked)}
              />
              {l("显示已归档", "Show archived")}
            </label>
            <button
              type="button"
              className="btn-primary shrink-0"
              onClick={() => {
                setActionError("");
                setEditor({ key: `new-${Date.now()}`, block: null });
              }}
            >
              {l("新建素材", "New material")}
            </button>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium text-ink-3">{l("类型", "Type")}</p>
            <div className="flex flex-wrap gap-2">
              {BLOCK_TYPES.map((type) => (
                <button
                  key={type}
                  type="button"
                  aria-pressed={selectedTypes.has(type)}
                  className={`btn btn-sm ${selectedTypes.has(type) ? "border-accent bg-accent-soft text-accent" : ""}`}
                  onClick={() => toggleType(type)}
                >
                  {labels.type[type]}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="mb-2 text-xs font-medium text-ink-3">{l("语言", "Language")}</p>
              <div className="segmented inline-grid grid-cols-3">
                {(["all", "zh", "en"] as LanguageFilter[]).map((language) => (
                  <button
                    key={language}
                    type="button"
                    aria-pressed={languageFilter === language}
                    className={`segmented-item ${languageFilter === language ? "segmented-on" : ""}`}
                    onClick={() => setLanguageFilter(language)}
                  >
                    {language === "all"
                      ? l("全部", "All")
                      : language === "zh"
                        ? l("中文", "Chinese")
                        : "English"}
                  </button>
                ))}
              </div>
            </div>
            {(availableTags.length > 0 || selectedTags.size > 0) && (
              <div className="sm:max-w-[65%]">
                <p className="mb-2 text-xs font-medium text-ink-3">
                  {l("标签（多选为同时包含）", "Tags (multiple selections narrow results)")}
                </p>
                <div className="flex flex-wrap gap-2">
                  {filterTags.map(([key, tag]) => (
                    <button
                      key={key}
                      type="button"
                      aria-pressed={selectedTags.has(key)}
                      aria-label={!availableTagKeys.has(key)
                        ? l(`移除不可用标签“${tag}”`, `Remove unavailable tag “${tag}”`)
                        : undefined}
                      className={`rounded-full border px-2.5 py-1 text-xs transition-colors ${
                        !availableTagKeys.has(key)
                          ? "border-dashed border-line bg-panel-2 text-ink-3"
                          : selectedTags.has(key)
                          ? "border-accent bg-accent-soft text-accent"
                          : "border-line bg-panel-2 text-ink-2 hover:border-line-strong"
                      }`}
                      onClick={() => toggleTag(key)}
                    >
                      {tag}
                      {!availableTagKeys.has(key) && (
                        <span aria-hidden="true" className="ml-1">×</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {hasActiveFilters && (
            <div className="flex justify-end">
              <button
                type="button"
                className="btn btn-sm"
                onClick={() => {
                  setSearch("");
                  setSelectedTypes(new Set());
                  setLanguageFilter("all");
                  setSelectedTags(new Set());
                }}
              >
                {l("清空筛选", "Clear filters")}
              </button>
            </div>
          )}
        </div>
      </div>

      {editor && (
        <MaterialEditor
          key={editor.key}
          block={editor.block}
          busy={editorBusy}
          onCancel={() => setEditor(null)}
          onSave={saveMaterial}
        />
      )}

      {(loadError || actionError) && (
        <div role="alert" className="mb-5 rounded-xl border border-bad/25 bg-bad-soft px-4 py-3 text-sm text-bad">
          {actionError || loadError}
        </div>
      )}

      {copyFallback && (
        <div className="card mb-5 p-4">
          <p className="text-sm font-medium">
            {l("复制兜底（聚焦后可全选）", "Copy fallback (focus to select all)")}
          </p>
          <textarea
            readOnly
            value={copyFallback.text}
            onFocus={(event) => event.currentTarget.select()}
            aria-label={l("可选择并复制的素材正文", "Material text available to select and copy")}
            className="input mt-2 min-h-32 w-full resize-y font-mono text-xs"
          />
        </div>
      )}

      {loading && blocks.length === 0 ? (
        <div role="status" className="card p-8 text-center text-sm text-ink-3">
          {l("正在加载素材…", "Loading materials…")}
        </div>
      ) : filteredBlocks.length === 0 ? (
        <div className="card p-8 text-center">
          <p className="font-medium">{l("没有符合条件的素材", "No materials match")}</p>
          <p className="mt-1 text-sm text-ink-3">
            {blocks.length === 0
              ? l("新建第一块素材，之后投递时就能快速复用。", "Create your first block to reuse in future applications.")
              : l("调整搜索或筛选条件后再试。", "Try changing the search or filters.")}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {filteredBlocks.map((block) => {
            const expanded = expandedIds.has(block.id);
            const selectionIndex = selectedIds.indexOf(block.id);
            const period = formatPeriod(block, l("至今", "Present"));
            const metadata = [block.organization, period].filter(Boolean).join(" · ");
            const copyKey = `block-${block.id}`;
            return (
              <article
                key={block.id}
                className={`card p-5 ${block.archived ? "opacity-65" : ""}`}
              >
                <div className="flex items-start gap-3">
                  <label className="relative mt-0.5 flex h-6 w-6 shrink-0 cursor-pointer items-center justify-center">
                    <input
                      type="checkbox"
                      checked={selectionIndex >= 0}
                      onChange={() => toggleSelected(block.id)}
                      aria-label={l(`选择素材“${block.title}”`, `Select material “${block.title}”`)}
                      className="h-4 w-4"
                    />
                    {selectionIndex >= 0 && (
                      <span className="pointer-events-none absolute -right-2 -top-2 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[9px] font-semibold text-accent-ink">
                        {selectionIndex + 1}
                      </span>
                    )}
                  </label>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-info/30 bg-info-soft px-2 py-0.5 text-xs font-medium text-info">
                        {labels.type[block.block_type]}
                      </span>
                      <span className="text-xs text-ink-3">
                        {block.language === "zh" ? l("中文", "Chinese") : "English"}
                      </span>
                      {block.archived && (
                        <span className="rounded-full bg-panel-2 px-2 py-0.5 text-xs text-ink-3">
                          {l("已归档", "Archived")}
                        </span>
                      )}
                    </div>
                    <h2 className="mt-2 text-base font-semibold">{block.title}</h2>
                    {metadata && <p className="mt-1 text-xs text-ink-3">{metadata}</p>}
                  </div>
                </div>

                <p className={`mt-4 text-sm leading-6 text-ink-2 ${expanded ? "whitespace-pre-wrap" : "line-clamp-3 whitespace-pre-wrap"}`}>
                  {block.body}
                </p>
                <button
                  type="button"
                  className="mt-1 text-xs font-medium text-accent hover:underline"
                  aria-expanded={expanded}
                  onClick={() => toggleExpanded(block.id)}
                >
                  {expanded ? l("收起", "Collapse") : l("展开", "Expand")}
                </button>

                {block.tags.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {block.tags.map((tag) => (
                      <span key={tag.toLocaleLowerCase()} className="rounded-full bg-panel-2 px-2 py-1 text-xs text-ink-2">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-3">
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => void copyText(
                      copyKey,
                      block.body,
                      l(`已复制“${block.title}”`, `Copied “${block.title}”`),
                    )}
                  >
                    {copiedKey === copyKey ? l("已复制", "Copied") : l("复制", "Copy")}
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm"
                    disabled={busyBlockId === block.id}
                    onClick={() => {
                      setActionError("");
                      setEditor({ key: `edit-${block.id}-${block.revision}`, block });
                    }}
                  >
                    {l("编辑", "Edit")}
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm"
                    disabled={busyBlockId === block.id}
                    onClick={() => void changeArchived(block)}
                  >
                    {busyBlockId === block.id
                      ? l("处理中…", "Working…")
                      : block.archived
                        ? l("恢复", "Restore")
                        : l("归档", "Archive")}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="fixed bottom-4 left-1/2 z-30 flex w-[min(calc(100%-2rem),42rem)] -translate-x-1/2 items-center justify-between gap-3 rounded-2xl border border-line bg-panel/95 px-4 py-3 shadow-xl backdrop-blur">
        <span className="text-sm font-medium">
          {l(`已选 ${selectedBlocks.length} 块`, `${selectedBlocks.length} selected`)}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            className="btn btn-sm"
            disabled={selectedBlocks.length === 0}
            onClick={() => setSelectedIds([])}
          >
            {l("清空", "Clear")}
          </button>
          <button
            type="button"
            className="btn-primary btn-sm"
            disabled={selectedBlocks.length === 0}
            onClick={() => void copyText(
              "merged",
              mergeMaterialBodies(selectedBlocks.map((block) => block.body)),
              l("已合并复制所选素材", "Copied selected materials"),
            )}
          >
            {copiedKey === "merged" ? l("已复制", "Copied") : l("合并复制", "Copy combined")}
          </button>
        </div>
      </div>
    </div>
  );
}
