export type CalendarEventType =
  | "course"
  | "career_fair"
  | "written_test"
  | "interview"
  | "deadline"
  | "other";

export type CalendarPriority = "high" | "medium" | "low";
export type CalendarRecurrence = "none" | "weekly";

export type CalendarEvent = {
  id: number;
  title: string;
  event_type: CalendarEventType;
  priority: CalendarPriority;
  date: string;
  start_time: string | null;
  end_time: string | null;
  recurrence: CalendarRecurrence;
  repeat_until: string | null;
  location: string | null;
  note: string | null;
  application_id: number | null;
  revision: number;
  application_company: string | null;
  application_position: string | null;
  created_time: string;
  updated_time: string;
};

export type CalendarOccurrence = CalendarEvent & {
  occurrence_date: string;
  conflict_group: string | null;
  conflict_rank: number | null;
  conflict_count: number;
};

export type CalendarEventInput = Omit<
  CalendarEvent,
  | "id"
  | "revision"
  | "application_company"
  | "application_position"
  | "created_time"
  | "updated_time"
>;

export type CalendarApplication = { id: number; company: string; position: string };

const EVENT_TYPES = new Set<CalendarEventType>([
  "course", "career_fair", "written_test", "interview", "deadline", "other",
]);
const PRIORITIES = new Set<CalendarPriority>(["high", "medium", "low"]);
const RECURRENCES = new Set<CalendarRecurrence>(["none", "weekly"]);

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

function parseEvent(value: unknown): CalendarEvent {
  const item = object(value, "calendar event");
  if (!EVENT_TYPES.has(item.event_type as CalendarEventType)) throw new Error("calendar event type is invalid");
  if (!PRIORITIES.has(item.priority as CalendarPriority)) throw new Error("calendar priority is invalid");
  if (!RECURRENCES.has(item.recurrence as CalendarRecurrence)) throw new Error("calendar recurrence is invalid");
  return {
    id: integer(item.id, "calendar event id"),
    title: text(item.title, "calendar event title"),
    event_type: item.event_type as CalendarEventType,
    priority: item.priority as CalendarPriority,
    date: text(item.date, "calendar event date"),
    start_time: nullableText(item.start_time, "calendar start time"),
    end_time: nullableText(item.end_time, "calendar end time"),
    recurrence: item.recurrence as CalendarRecurrence,
    repeat_until: nullableText(item.repeat_until, "calendar repeat date"),
    location: nullableText(item.location, "calendar location"),
    note: nullableText(item.note, "calendar note"),
    application_id: item.application_id === null ? null : integer(item.application_id, "calendar application id"),
    revision: integer(item.revision, "calendar revision"),
    application_company: nullableText(item.application_company, "calendar application company"),
    application_position: nullableText(item.application_position, "calendar application position"),
    created_time: text(item.created_time, "calendar created time"),
    updated_time: text(item.updated_time, "calendar updated time"),
  };
}

export function parseCalendarEvent(value: unknown): CalendarEvent {
  return parseEvent(value);
}

export function parseCalendarOccurrences(value: unknown): CalendarOccurrence[] {
  const response = object(value, "calendar response");
  if (!Array.isArray(response.items)) throw new Error("calendar items are invalid");
  return response.items.map((raw) => {
    const item = object(raw, "calendar occurrence");
    const event = parseEvent(item);
    return {
      ...event,
      occurrence_date: text(item.occurrence_date, "calendar occurrence date"),
      conflict_group: nullableText(item.conflict_group, "calendar conflict group"),
      conflict_rank: item.conflict_rank === null ? null : integer(item.conflict_rank, "calendar conflict rank", 0),
      conflict_count: integer(item.conflict_count, "calendar conflict count", 0),
    };
  });
}

export function parseCalendarApplications(value: unknown): CalendarApplication[] {
  const response = object(value, "calendar applications response");
  if (!Array.isArray(response.items)) throw new Error("calendar applications are invalid");
  return response.items.map((raw) => {
    const item = object(raw, "calendar application");
    return {
      id: integer(item.id, "calendar application id"),
      company: text(item.company, "calendar company"),
      position: text(item.position, "calendar position"),
    };
  });
}

