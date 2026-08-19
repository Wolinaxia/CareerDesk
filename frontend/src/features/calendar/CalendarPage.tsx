import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocalizer } from "../../i18n/useLocalizer";
import {
  createCalendarEvent,
  deleteCalendarEvent,
  getCalendarApplications,
  getCalendarEvents,
  updateCalendarEvent,
} from "./calendarApi";
import {
  type CalendarApplication,
  type CalendarEvent,
  type CalendarEventInput,
  type CalendarEventType,
  type CalendarOccurrence,
  type CalendarPriority,
} from "./calendarContract";
import {
  addDays,
  fromDate,
  localDate,
  monthGrid,
  shiftAnchor,
  startOfWeek,
  type CalendarView,
  weekGrid,
} from "./calendarDate";

const PRIORITIES: CalendarPriority[] = ["high", "medium", "low"];
const EVENT_TYPES: CalendarEventType[] = [
  "course", "career_fair", "written_test", "interview", "deadline", "todo", "other",
];

function blankInput(date: string): CalendarEventInput {
  return {
    title: "",
    event_type: "course",
    priority: "medium",
    date,
    start_time: "09:00",
    end_time: "10:00",
    recurrence: "none",
    repeat_until: null,
    location: null,
    note: null,
    application_id: null,
    completed: false,
  };
}

function inputFromEvent(event: CalendarEvent): CalendarEventInput {
  return {
    title: event.title,
    event_type: event.event_type,
    priority: event.priority,
    date: event.date,
    start_time: event.start_time,
    end_time: event.end_time,
    recurrence: event.recurrence,
    repeat_until: event.repeat_until,
    location: event.location,
    note: event.note,
    application_id: event.application_id,
    completed: event.completed,
  };
}

function priorityStyle(priority: CalendarPriority): string {
  if (priority === "high") return "border-bad/45 bg-bad-soft text-ink";
  if (priority === "medium") return "border-warn/55 bg-warn-soft text-ink";
  return "border-info/40 bg-info-soft text-ink";
}

function useCalendarLabels() {
  const l = useLocalizer();
  return {
    priority: {
      high: l("高", "High"),
      medium: l("中", "Medium"),
      low: l("低", "Low"),
    } satisfies Record<CalendarPriority, string>,
    type: {
      course: l("课程", "Course"),
      career_fair: l("招聘活动", "Career event"),
      written_test: l("笔试", "Written test"),
      interview: l("面试", "Interview"),
      deadline: l("截止事项", "Deadline"),
      todo: l("待办", "To-do"),
      other: l("其他", "Other"),
    } satisfies Record<CalendarEventType, string>,
  };
}

function EventNote({ event, onOpen }: { event: CalendarOccurrence; onOpen: () => void }) {
  const l = useLocalizer();
  const labels = useCalendarLabels();
  return (
    <button
      type="button"
      onClick={onOpen}
      className={`w-full border px-2 py-1.5 text-left shadow-sm transition-transform hover:-translate-y-0.5 ${priorityStyle(event.priority)}`}
      style={{ borderRadius: 3 }}
      title={event.note ?? event.title}
    >
      <span className="flex min-w-0 items-center gap-1.5">
        <span className="shrink-0 text-[10px] font-semibold">{labels.priority[event.priority]}</span>
        <span className="min-w-0 flex-1 truncate text-xs font-semibold">{event.title}</span>
        {event.recurrence === "weekly" && <span aria-label={l("每周重复", "Repeats weekly")} className="text-[10px]">↻</span>}
      </span>
      <span className="mt-0.5 block truncate text-[10px] text-ink-2">
        {event.start_time ? `${event.start_time}–${event.end_time}` : l("全天", "All day")}
        {event.location ? ` · ${event.location}` : ""}
      </span>
    </button>
  );
}

function TodoNote({
  event,
  busy,
  onOpen,
  onToggle,
}: {
  event: CalendarOccurrence;
  busy: boolean;
  onOpen: () => void;
  onToggle: () => void;
}) {
  const l = useLocalizer();
  return (
    <div
      className={`flex min-h-8 w-full items-center gap-1.5 border border-l-2 px-1.5 py-1 shadow-sm ${priorityStyle(event.priority)} ${event.completed ? "opacity-55" : ""}`}
      style={{ borderRadius: 2 }}
    >
      <input
        type="checkbox"
        checked={event.completed}
        disabled={busy}
        onChange={onToggle}
        aria-label={event.completed
          ? l(`将待办“${event.title}”标为未完成`, `Mark “${event.title}” incomplete`)
          : l(`完成待办“${event.title}”`, `Complete “${event.title}”`)}
        className="h-3.5 w-3.5 shrink-0"
      />
      <button
        type="button"
        onClick={onOpen}
        className="min-w-0 flex-1 truncate text-left text-[11px] font-medium"
        title={event.note ?? event.title}
      >
        <span className={event.completed ? "line-through" : ""}>{event.title}</span>
      </button>
    </div>
  );
}

function ConflictStack({
  events,
  onExpand,
}: {
  events: CalendarOccurrence[];
  onExpand: () => void;
}) {
  const l = useLocalizer();
  const ordered = [...events].sort((left, right) =>
    (left.conflict_rank ?? 99) - (right.conflict_rank ?? 99));
  return (
    <button
      type="button"
      onClick={onExpand}
      className="relative block w-full text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      style={{ height: 62 + (ordered.length - 1) * 11 }}
      aria-label={l(`${ordered.length} 个冲突日程，展开比较`, `${ordered.length} conflicting events, compare`)}
    >
      {[...ordered].reverse().map((event, reverseIndex) => {
        const index = ordered.length - reverseIndex - 1;
        return (
          <span
            key={`${event.id}-${event.occurrence_date}`}
            className={`absolute inset-x-0 block h-[62px] border px-2 py-1.5 shadow-sm ${priorityStyle(event.priority)}`}
            style={{ top: index * 11, zIndex: ordered.length - index, borderRadius: 3 }}
          >
            <span className="flex min-w-0 items-center gap-1.5">
              <span className="shrink-0 text-[10px] font-semibold">
                {event.priority === "high" ? l("高", "High") : event.priority === "medium" ? l("中", "Medium") : l("低", "Low")}
              </span>
              <span className="min-w-0 flex-1 truncate text-xs font-semibold">{event.title}</span>
              {index === 0 && (
                <span className="shrink-0 rounded-full bg-panel/75 px-1.5 py-0.5 text-[9px] font-semibold">
                  {l(`${ordered.length} 项冲突`, `${ordered.length} conflicts`)}
                </span>
              )}
            </span>
            <span className="mt-0.5 block truncate text-[10px] text-ink-2">
              {event.start_time}–{event.end_time}{event.location ? ` · ${event.location}` : ""}
            </span>
          </span>
        );
      })}
    </button>
  );
}

type DayBlock = { key: string; events: CalendarOccurrence[] };

function blocksFor(events: CalendarOccurrence[]): DayBlock[] {
  const blocks: DayBlock[] = [];
  const seen = new Set<string>();
  for (const event of events) {
    const key = event.conflict_group ?? `event:${event.id}:${event.occurrence_date}`;
    if (seen.has(key)) continue;
    seen.add(key);
    blocks.push({ key, events: event.conflict_group
      ? events.filter((candidate) => candidate.conflict_group === event.conflict_group)
      : [event] });
  }
  return blocks;
}

function useModalDialog(onClose: () => void, closeEnabled = true) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  const closeEnabledRef = useRef(closeEnabled);
  const openerRef = useRef<HTMLElement | null>(
    document.activeElement instanceof HTMLElement ? document.activeElement : null,
  );
  onCloseRef.current = onClose;
  closeEnabledRef.current = closeEnabled;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const focusableSelector = "button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [href], [tabindex]:not([tabindex='-1'])";
    const focusable = () => Array.from(dialog.querySelectorAll<HTMLElement>(focusableSelector));
    const frame = window.requestAnimationFrame(() => {
      if (!dialog.contains(document.activeElement)) {
        (dialog.querySelector<HTMLElement>("[autofocus]") ?? focusable()[0] ?? dialog).focus();
      }
    });
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && closeEnabledRef.current) {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusable();
      if (items.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      window.cancelAnimationFrame(frame);
      document.removeEventListener("keydown", handleKeyDown);
      openerRef.current?.focus();
    };
  }, []);

  return dialogRef;
}

function EventDialog({
  initialDate,
  event,
  applications,
  onClose,
  onSaved,
  onDeleted,
}: {
  initialDate: string;
  event: CalendarEvent | null;
  applications: CalendarApplication[];
  onClose: () => void;
  onSaved: () => void;
  onDeleted: () => void;
}) {
  const l = useLocalizer();
  const labels = useCalendarLabels();
  const [form, setForm] = useState<CalendarEventInput>(() => event ? inputFromEvent(event) : blankInput(initialDate));
  const [allDay, setAllDay] = useState(event ? event.start_time === null : false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const dialogRef = useModalDialog(onClose, !busy);
  const isTodo = form.event_type === "todo";

  function changeType(eventType: CalendarEventType) {
    const todo = eventType === "todo";
    const wasTodo = form.event_type === "todo";
    if (todo) setAllDay(true);
    else if (wasTodo) setAllDay(false);
    setForm((current) => ({
      ...current,
      event_type: eventType,
      completed: todo ? current.completed : false,
      start_time: todo ? null : (wasTodo ? "09:00" : current.start_time),
      end_time: todo ? null : (wasTodo ? "10:00" : current.end_time),
      recurrence: todo ? "none" : current.recurrence,
      repeat_until: todo ? null : current.repeat_until,
    }));
  }

  async function save() {
    if (!form.title.trim() || busy) return;
    if (form.recurrence === "weekly" && !form.repeat_until) {
      setError(l("请选择重复截止日期", "Choose when the weekly series ends"));
      return;
    }
    setBusy(true);
    setError("");
    const payload = {
      ...form,
      title: form.title.trim(),
      start_time: isTodo || allDay ? null : form.start_time,
      end_time: isTodo || allDay ? null : form.end_time,
      recurrence: isTodo ? "none" as const : form.recurrence,
      repeat_until: !isTodo && form.recurrence === "weekly" ? (form.repeat_until || null) : null,
      location: form.location?.trim() || null,
      note: form.note?.trim() || null,
    };
    try {
      if (event) await updateCalendarEvent(event.id, payload, event.revision);
      else await createCalendarEvent(payload);
      onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : l("保存失败", "Could not save"));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    const noun = event?.event_type === "todo" ? l("待办", "to-do") : l("日程", "event");
    if (!event || busy || !window.confirm(l(`删除${noun}“${event.title}”？`, `Delete ${noun} “${event.title}”?`))) return;
    setBusy(true);
    setError("");
    try {
      await deleteCalendarEvent(event.id, event.revision);
      onDeleted();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : l("删除失败", "Could not delete"));
      setBusy(false);
    }
  }

  const field = "input w-full";
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/35 p-0 sm:items-center sm:p-6" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget && !busy) onClose(); }}>
      <div ref={dialogRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="calendar-editor-title" className="max-h-[92vh] w-full overflow-y-auto rounded-t-2xl border border-line bg-panel p-5 shadow-2xl sm:max-w-2xl sm:rounded-lg sm:p-6">
        <div className="mb-5 flex items-center justify-between gap-4">
          <h2 id="calendar-editor-title" className="text-lg font-semibold">
            {isTodo
              ? (event ? l("编辑待办", "Edit to-do") : l("新建待办", "New to-do"))
              : (event ? l("编辑日程", "Edit event") : l("新建日程", "New event"))}
          </h2>
          <button type="button" className="btn h-9 w-9 p-0" aria-label={l("关闭", "Close")} title={l("关闭", "Close")} onClick={onClose} disabled={busy}>×</button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="sm:col-span-2"><span className="mb-1 block text-xs font-medium text-ink-2">{l("标题", "Title")}</span><input autoFocus className={field} value={form.title} maxLength={120} onChange={(e) => setForm((current) => ({ ...current, title: e.target.value }))} /></label>
          <label><span className="mb-1 block text-xs font-medium text-ink-2">{l("类型", "Type")}</span><select className={field} value={form.event_type} onChange={(e) => changeType(e.target.value as CalendarEventType)}>{EVENT_TYPES.map((type) => <option key={type} value={type}>{labels.type[type]}</option>)}</select></label>
          <div><span className="mb-1 block text-xs font-medium text-ink-2">{l("优先级", "Priority")}</span><div className="segmented grid grid-cols-3">{PRIORITIES.map((priority) => <button key={priority} type="button" aria-pressed={form.priority === priority} className={`segmented-item ${form.priority === priority ? "segmented-on" : ""}`} onClick={() => setForm((current) => ({ ...current, priority }))}>{labels.priority[priority]}</button>)}</div></div>
          <label><span className="mb-1 block text-xs font-medium text-ink-2">{isTodo ? l("计划日期", "Planned date") : form.recurrence === "weekly" ? l("系列首次日期", "Series start date") : l("日期", "Date")}</span><input type="date" className={field} value={form.date} onChange={(e) => setForm((current) => ({ ...current, date: e.target.value }))} /></label>
          {isTodo && <label className="flex items-end gap-2 pb-2 text-sm"><input type="checkbox" checked={form.completed} onChange={(e) => setForm((current) => ({ ...current, completed: e.target.checked }))} />{l("已完成", "Completed")}</label>}
          {!isTodo && <label className="flex items-end gap-2 pb-2 text-sm"><input type="checkbox" checked={allDay} onChange={(e) => setAllDay(e.target.checked)} />{l("全天事项", "All-day event")}</label>}
          {!isTodo && !allDay && <><label><span className="mb-1 block text-xs font-medium text-ink-2">{l("开始时间", "Start")}</span><input type="time" className={field} value={form.start_time ?? "09:00"} onChange={(e) => setForm((current) => ({ ...current, start_time: e.target.value }))} /></label><label><span className="mb-1 block text-xs font-medium text-ink-2">{l("结束时间", "End")}</span><input type="time" className={field} value={form.end_time ?? "10:00"} onChange={(e) => setForm((current) => ({ ...current, end_time: e.target.value }))} /></label></>}
          {!isTodo && <label><span className="mb-1 block text-xs font-medium text-ink-2">{l("重复", "Repeat")}</span><select className={field} value={form.recurrence} onChange={(e) => setForm((current) => ({ ...current, recurrence: e.target.value as "none" | "weekly", repeat_until: e.target.value === "weekly" ? (current.repeat_until ?? addDays(current.date, 84)) : null }))}><option value="none">{l("不重复", "Does not repeat")}</option><option value="weekly">{l("每周", "Weekly")}</option></select></label>}
          {!isTodo && form.recurrence === "weekly" && <label><span className="mb-1 block text-xs font-medium text-ink-2">{l("重复至", "Repeat until")}</span><input type="date" min={form.date} className={field} value={form.repeat_until ?? form.date} onChange={(e) => setForm((current) => ({ ...current, repeat_until: e.target.value }))} /></label>}
          <label className="sm:col-span-2"><span className="mb-1 block text-xs font-medium text-ink-2">{l("关联岗位（可选）", "Linked role (optional)")}</span><select className={field} value={form.application_id ?? ""} onChange={(e) => setForm((current) => ({ ...current, application_id: e.target.value ? Number(e.target.value) : null }))}><option value="">{l("不关联岗位", "No linked role")}</option>{applications.map((application) => <option key={application.id} value={application.id}>{application.company} · {application.position}</option>)}</select></label>
          <label className="sm:col-span-2"><span className="mb-1 block text-xs font-medium text-ink-2">{l("地点", "Location")}</span><input className={field} value={form.location ?? ""} maxLength={2000} onChange={(e) => setForm((current) => ({ ...current, location: e.target.value }))} /></label>
          <label className="sm:col-span-2"><span className="mb-1 block text-xs font-medium text-ink-2">{l("备注", "Notes")}</span><textarea className={`${field} min-h-20 resize-y`} value={form.note ?? ""} maxLength={2000} onChange={(e) => setForm((current) => ({ ...current, note: e.target.value }))} /></label>
        </div>
        {form.recurrence === "weekly" && <p className="mt-3 text-xs text-ink-3">{l("修改会应用到整组每周日程，不能只修改当前这一次。", "Changes apply to the full weekly series, not only this occurrence.")}</p>}
        {error && <p role="alert" className="mt-3 text-sm text-bad">{error}</p>}
        <div className="mt-5 flex items-center justify-between gap-3">
          <div>{event && <button type="button" className="btn btn-danger" onClick={() => void remove()} disabled={busy}>{l("删除", "Delete")}</button>}</div>
          <div className="flex gap-2"><button type="button" className="btn" onClick={onClose} disabled={busy}>{l("取消", "Cancel")}</button><button type="button" className="btn-primary" onClick={() => void save()} disabled={busy || !form.title.trim()}>{busy ? l("保存中…", "Saving…") : l("保存", "Save")}</button></div>
        </div>
      </div>
    </div>
  );
}

function ConflictDialog({ events, onClose, onEdit }: { events: CalendarOccurrence[]; onClose: () => void; onEdit: (event: CalendarOccurrence) => void }) {
  const l = useLocalizer();
  const labels = useCalendarLabels();
  const dialogRef = useModalDialog(onClose);
  const ordered = [...events].sort((left, right) => (left.conflict_rank ?? 99) - (right.conflict_rank ?? 99));
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/35 sm:items-center sm:p-6" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div ref={dialogRef} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="conflict-title" className="w-full rounded-t-2xl border border-line bg-panel p-5 shadow-2xl sm:max-w-xl sm:rounded-lg sm:p-6">
        <div className="mb-4 flex items-start justify-between gap-4"><div><h2 id="conflict-title" className="text-lg font-semibold">{l("日程撞车", "Schedule conflict")}</h2><p className="mt-1 text-sm text-ink-3">{l("已按优先级从高到低排列。", "Ordered from highest to lowest priority.")}</p></div><button type="button" className="btn h-9 w-9 p-0" aria-label={l("关闭", "Close")} onClick={onClose}>×</button></div>
        <div className="space-y-2">{ordered.map((event) => <button type="button" key={`${event.id}-${event.occurrence_date}`} onClick={() => onEdit(event)} className={`w-full border p-3 text-left shadow-sm transition-transform hover:-translate-y-0.5 ${priorityStyle(event.priority)}`} style={{ borderRadius: 3 }}><span className="flex items-center gap-2"><span className="text-xs font-semibold">{labels.priority[event.priority]}</span><span className="font-semibold">{event.title}</span><span className="ml-auto text-xs">{event.start_time}–{event.end_time}</span></span>{(event.application_company || event.location) && <span className="mt-1 block text-xs text-ink-2">{event.application_company ? `${event.application_company} · ${event.application_position}` : ""}{event.application_company && event.location ? " · " : ""}{event.location}</span>}</button>)}</div>
      </div>
    </div>
  );
}

export function CalendarPage() {
  const l = useLocalizer();
  const [view, setView] = useState<CalendarView>("month");
  const [anchor, setAnchor] = useState(localDate);
  const [events, setEvents] = useState<CalendarOccurrence[]>([]);
  const [applications, setApplications] = useState<CalendarApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState<{ date: string; event: CalendarEvent | null } | null>(null);
  const [conflict, setConflict] = useState<CalendarOccurrence[] | null>(null);
  const [togglingTodoIds, setTogglingTodoIds] = useState<Set<number>>(() => new Set());
  const refreshEpochRef = useRef(0);
  const refreshControllerRef = useRef<AbortController | null>(null);

  const dates = useMemo(() => view === "month" ? monthGrid(anchor) : weekGrid(anchor), [anchor, view]);
  const rangeStart = dates[0];
  const rangeEnd = dates[dates.length - 1];

  const refresh = useCallback(() => {
    refreshControllerRef.current?.abort();
    const controller = new AbortController();
    const epoch = ++refreshEpochRef.current;
    refreshControllerRef.current = controller;
    setLoading(true);
    setError("");
    void (async () => {
      try {
        const [nextEvents, nextApplications] = await Promise.all([
          getCalendarEvents(rangeStart, rangeEnd, controller.signal),
          getCalendarApplications(controller.signal),
        ]);
        if (epoch !== refreshEpochRef.current || controller.signal.aborted) return;
        setEvents(nextEvents);
        setApplications(nextApplications);
      } catch (caught) {
        if (epoch !== refreshEpochRef.current || controller.signal.aborted) return;
        setError(caught instanceof Error ? caught.message : l("日程加载失败", "Could not load calendar"));
      } finally {
        if (epoch === refreshEpochRef.current && !controller.signal.aborted) setLoading(false);
      }
    })();
    return controller;
  }, [l, rangeEnd, rangeStart]);
  const latestRefreshRef = useRef(refresh);
  latestRefreshRef.current = refresh;

  useEffect(() => {
    const controller = refresh();
    return () => controller.abort();
  }, [refresh]);

  const byDate = useMemo(() => {
    const result = new Map<string, CalendarOccurrence[]>();
    for (const date of dates) result.set(date, []);
    for (const event of events) result.get(event.occurrence_date)?.push(event);
    return result;
  }, [dates, events]);

  const locale = document.documentElement.lang === "en" ? "en-US" : "zh-CN";
  const anchorDate = fromDate(anchor);
  const title = view === "month"
    ? new Intl.DateTimeFormat(locale, { year: "numeric", month: "long" }).format(anchorDate)
    : `${new Intl.DateTimeFormat(locale, { month: "short", day: "numeric" }).format(fromDate(startOfWeek(anchor)))} – ${new Intl.DateTimeFormat(locale, { month: "short", day: "numeric" }).format(fromDate(addDays(startOfWeek(anchor), 6)))}`;
  const weekdays = Array.from({ length: 7 }, (_, index) => new Intl.DateTimeFormat(locale, { weekday: "short" }).format(fromDate(addDays("2026-08-17", index))));
  const currentMonth = anchorDate.getMonth();
  const today = localDate();

  function openEvent(event: CalendarOccurrence) {
    setConflict(null);
    setEditor({ date: event.occurrence_date, event });
  }

  async function toggleTodo(event: CalendarOccurrence) {
    if (event.event_type !== "todo" || togglingTodoIds.has(event.id)) return;
    setError("");
    setTogglingTodoIds((current) => new Set(current).add(event.id));
    try {
      const updated = await updateCalendarEvent(
        event.id,
        { ...inputFromEvent(event), completed: !event.completed },
        event.revision,
      );
      refreshEpochRef.current += 1;
      setEvents((current) => current.map((item) =>
        item.id === updated.id ? { ...item, ...updated } : item));
      void latestRefreshRef.current();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : l("待办更新失败", "Could not update to-do"));
    } finally {
      setTogglingTodoIds((current) => {
        const next = new Set(current);
        next.delete(event.id);
        return next;
      });
    }
  }

  return (
    <div>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <button type="button" className="btn h-9 w-9 p-0 text-lg" title={l("上一段", "Previous")} aria-label={l("上一段", "Previous")} onClick={() => setAnchor(shiftAnchor(anchor, view, -1))}>‹</button>
          <button type="button" className="btn h-9 w-9 p-0 text-lg" title={l("下一段", "Next")} aria-label={l("下一段", "Next")} onClick={() => setAnchor(shiftAnchor(anchor, view, 1))}>›</button>
          <button type="button" className="btn btn-sm" onClick={() => setAnchor(today)}>{l("今天", "Today")}</button>
          <h2 className="ml-1 text-base font-semibold sm:text-lg">{title}</h2>
        </div>
        <div className="flex items-center gap-2">
          <div className="segmented"><button type="button" className={`segmented-item ${view === "month" ? "segmented-on" : ""}`} aria-pressed={view === "month"} onClick={() => setView("month")}>{l("月", "Month")}</button><button type="button" className={`segmented-item ${view === "week" ? "segmented-on" : ""}`} aria-pressed={view === "week"} onClick={() => setView("week")}>{l("周", "Week")}</button></div>
          <button type="button" className="btn-primary" onClick={() => setEditor({ date: anchor, event: null })}><span aria-hidden="true">＋</span>{l("新建日程", "New event")}</button>
        </div>
      </div>

      {error && <div role="alert" className="mb-4 border border-bad/30 bg-bad-soft p-3 text-sm text-bad" style={{ borderRadius: 6 }}>{error}</div>}
      <div className="overflow-x-auto border border-line bg-panel shadow-sm" style={{ borderRadius: 6 }}>
        <div className="min-w-[880px]">
          <div className="grid grid-cols-7 border-b border-line bg-panel-2">{weekdays.map((weekday) => <div key={weekday} className="px-2 py-2 text-center text-xs font-medium text-ink-3">{weekday}</div>)}</div>
          <div className={`grid grid-cols-7 ${view === "month" ? "grid-rows-6" : "grid-rows-1"}`}>
            {dates.map((date) => {
              const dayEvents = byDate.get(date) ?? [];
              const blocks = blocksFor(dayEvents);
              const completedTodoBlocks = blocks.filter((block) =>
                block.events.length === 1
                && block.events[0].event_type === "todo"
                && block.events[0].completed);
              const activeBlocks = blocks.filter((block) => !completedTodoBlocks.includes(block));
              const dateValue = fromDate(date);
              const outside = view === "month" && dateValue.getMonth() !== currentMonth;
              const renderBlock = (block: DayBlock) => block.events.length > 1
                ? <ConflictStack key={block.key} events={block.events} onExpand={() => setConflict(block.events)} />
                : block.events[0].event_type === "todo"
                  ? <TodoNote key={block.key} event={block.events[0]} busy={togglingTodoIds.has(block.events[0].id)} onOpen={() => openEvent(block.events[0])} onToggle={() => void toggleTodo(block.events[0])} />
                  : <EventNote key={block.key} event={block.events[0]} onOpen={() => openEvent(block.events[0])} />;
              return (
                <section key={date} className={`group min-w-0 border-b border-r border-line p-1.5 last:border-r-0 ${view === "month" ? "h-[148px]" : "min-h-[560px]"} ${outside ? "bg-panel-2/45" : "bg-panel"}`}>
                  <div className="mb-1 flex h-7 items-center justify-between gap-1">
                    <span className={`flex h-7 min-w-7 items-center justify-center text-xs tabular-nums ${date === today ? "rounded-full bg-accent font-semibold text-accent-ink" : outside ? "text-ink-3" : "text-ink-2"}`}>{dateValue.getDate()}</span>
                    <button type="button" className="h-6 w-6 rounded text-ink-3 opacity-100 transition-opacity hover:bg-panel-2 hover:text-ink sm:opacity-0 sm:group-hover:opacity-100 sm:focus:opacity-100" aria-label={l(`在 ${date} 新建日程`, `Add event on ${date}`)} title={l("新建日程", "New event")} onClick={() => setEditor({ date, event: null })}>＋</button>
                  </div>
                  {view === "month" ? (
                    <div className="flex h-[108px] min-h-0 flex-col gap-1">
                      <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto pr-0.5">
                        {activeBlocks.map(renderBlock)}
                        {loading && blocks.length === 0 && <span className="block h-8 animate-pulse bg-panel-2" style={{ borderRadius: 3 }} />}
                      </div>
                      {completedTodoBlocks.length > 0 && (
                        <div className="max-h-[42px] shrink-0 space-y-1 overflow-y-auto border-t border-line pt-1 pr-0.5" aria-label={l("已完成待办", "Completed to-dos")}>
                          {completedTodoBlocks.map(renderBlock)}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {blocks.map(renderBlock)}
                      {loading && blocks.length === 0 && <span className="block h-8 animate-pulse bg-panel-2" style={{ borderRadius: 3 }} />}
                    </div>
                  )}
                </section>
              );
            })}
          </div>
        </div>
      </div>

      {editor && <EventDialog initialDate={editor.date} event={editor.event} applications={applications} onClose={() => setEditor(null)} onSaved={() => { setEditor(null); void refresh(); }} onDeleted={() => { setEditor(null); void refresh(); }} />}
      {conflict && <ConflictDialog events={conflict} onClose={() => setConflict(null)} onEdit={openEvent} />}
    </div>
  );
}
