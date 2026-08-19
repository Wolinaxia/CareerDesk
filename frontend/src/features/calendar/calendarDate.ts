export type CalendarView = "month" | "week";

export function localDate(value = new Date()): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function fromDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day, 12);
}

export function addDays(value: string, amount: number): string {
  const next = fromDate(value);
  next.setDate(next.getDate() + amount);
  return localDate(next);
}

export function startOfWeek(value: string): string {
  const date = fromDate(value);
  const offset = (date.getDay() + 6) % 7;
  return addDays(value, -offset);
}

export function monthGrid(value: string): string[] {
  const date = fromDate(value);
  const first = localDate(new Date(date.getFullYear(), date.getMonth(), 1, 12));
  const start = startOfWeek(first);
  return Array.from({ length: 42 }, (_, index) => addDays(start, index));
}

export function weekGrid(value: string): string[] {
  const start = startOfWeek(value);
  return Array.from({ length: 7 }, (_, index) => addDays(start, index));
}

export function shiftAnchor(value: string, view: CalendarView, amount: number): string {
  if (view === "week") return addDays(value, amount * 7);
  const date = fromDate(value);
  return localDate(new Date(date.getFullYear(), date.getMonth() + amount, 1, 12));
}

