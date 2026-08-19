import { del, getJson, postJson, putJson } from "../../shared/api/transport";
import {
  parseCalendarApplications,
  parseCalendarEvent,
  parseCalendarOccurrences,
  type CalendarApplication,
  type CalendarEvent,
  type CalendarEventInput,
  type CalendarOccurrence,
} from "./calendarContract";

export async function getCalendarEvents(start: string, end: string): Promise<CalendarOccurrence[]> {
  const query = new URLSearchParams({ start, end });
  return parseCalendarOccurrences(await getJson<unknown>(`/api/calendar/events?${query}`));
}

export async function getCalendarApplications(): Promise<CalendarApplication[]> {
  return parseCalendarApplications(await getJson<unknown>("/api/calendar/applications"));
}

export async function createCalendarEvent(input: CalendarEventInput): Promise<CalendarEvent> {
  return parseCalendarEvent(await postJson<unknown>("/api/calendar/events", input));
}

export async function updateCalendarEvent(
  eventId: number,
  input: CalendarEventInput,
  expectedRevision: number,
): Promise<CalendarEvent> {
  return parseCalendarEvent(await putJson<unknown>(`/api/calendar/events/${eventId}`, {
    ...input,
    expected_revision: expectedRevision,
  }));
}

export async function deleteCalendarEvent(eventId: number, expectedRevision: number): Promise<void> {
  await del<unknown>(`/api/calendar/events/${eventId}?expected_revision=${expectedRevision}`);
}

