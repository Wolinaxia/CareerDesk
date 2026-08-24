import assert from "node:assert/strict";
import { test } from "node:test";

import { groupPreferences, preferenceFieldLabel } from "./preferenceScopes.ts";

function item(id, key, value) {
  return {
    id, key, value, revision: 1,
    created_time: "2026-08-20T00:00:00+00:00",
    updated_time: "2026-08-20T00:00:00+00:00",
  };
}

test("preferences are grouped into shared, independent tracks, and assistant behavior", () => {
  const groups = groupPreferences([
    item(1, "career_global.locations", "Singapore"),
    item(2, "career_track.fintech.name", "金融科技"),
    item(3, "career_track.fintech.resume_focus", "工程与数据能力"),
    item(4, "career_track.product.name", "产品"),
    item(5, "response_tone", "简洁"),
    item(6, "旧偏好", "兼容旧数据"),
  ], "zh-CN");

  assert.deepEqual(groups.map((group) => [group.kind, group.title, group.items.length]), [
    ["shared", "通用偏好", 2],
    ["track", "金融科技", 2],
    ["track", "产品", 1],
    ["behavior", "助手表达", 1],
  ]);
  assert.equal(preferenceFieldLabel("career_track.fintech.resume_focus", "zh-CN"), "简历侧重");
  assert.equal(preferenceFieldLabel("career_global.locations", "en"), "Locations");
});

test("malformed track keys remain visible as shared legacy preferences", () => {
  const groups = groupPreferences([
    item(1, "career_track.FinTech.resume_focus", "keep visible"),
    item(2, "career_track.incomplete", "keep visible"),
  ], "en");
  assert.equal(groups.length, 1);
  assert.equal(groups[0].kind, "shared");
  assert.equal(groups[0].items.length, 2);
});
