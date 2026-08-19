import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const pageUrl = new URL("./CalendarPage.tsx", import.meta.url);
const apiUrl = new URL("./calendarApi.ts", import.meta.url);

test("calendar refresh aborts stale ranges and guards state with an epoch", async () => {
  const [page, api] = await Promise.all([
    readFile(pageUrl, "utf8"),
    readFile(apiUrl, "utf8"),
  ]);
  assert.match(page, /refreshControllerRef\.current\?\.abort\(\)/);
  assert.match(page, /epoch !== refreshEpochRef\.current/);
  assert.match(page, /controller\.signal\.aborted/);
  assert.match(page, /getCalendarEvents\(rangeStart, rangeEnd, controller\.signal\)/);
  assert.match(api, /getJson<unknown>\(`\/api\/calendar\/events\?\$\{query\}`, \{ signal \}\)/);
  assert.match(api, /getJson<unknown>\("\/api\/calendar\/applications", \{ signal \}\)/);
});

test("calendar keeps day creation visible on touch and explains weekly edits", async () => {
  const page = await readFile(pageUrl, "utf8");
  assert.match(page, /opacity-100 transition-opacity[^"]*sm:opacity-0/);
  assert.match(page, /系列首次日期/);
  assert.match(page, /修改会应用到整组每周日程/);
  assert.match(page, /form\.repeat_until \|\| null/);
});

test("calendar dialogs support escape, trapped focus, and focus restoration", async () => {
  const page = await readFile(pageUrl, "utf8");
  assert.match(page, /event\.key === "Escape"/);
  assert.match(page, /event\.key !== "Tab"/);
  assert.match(page, /openerRef\.current\?\.focus\(\)/);
  assert.equal((page.match(/const dialogRef = useModalDialog\(onClose/g) ?? []).length, 2);
});
