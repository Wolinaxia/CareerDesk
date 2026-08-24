import type { PreferenceItem } from "./preferencesContract";

export type PreferenceGroup = {
  id: string;
  kind: "shared" | "track" | "behavior";
  title: string;
  items: PreferenceItem[];
};

const BEHAVIOR_KEYS = new Set([
  "conversation_style",
  "response_greeting",
  "response_tone",
  "response_format",
]);
const TRACK_KEY = /^career_track\.([a-z0-9][a-z0-9_-]{0,31})\.([a-z0-9][a-z0-9_-]{0,31})$/;

export function preferenceFieldLabel(key: string, locale: string): string {
  const track = TRACK_KEY.exec(key);
  const field = track?.[2]
    ?? (key.startsWith("career_global.") ? key.slice("career_global.".length) : key);
  const labels: Record<string, [string, string]> = {
    career_strategy: ["总体求职策略", "Overall search strategy"],
    name: ["方向名称", "Track name"],
    target_roles: ["目标岗位", "Target roles"],
    industries: ["目标行业", "Industries"],
    strengths: ["优势侧重", "Strengths"],
    resume_focus: ["简历侧重", "Resume focus"],
    constraints: ["筛选条件", "Constraints"],
    locations: ["目标地点", "Locations"],
    compensation: ["薪资偏好", "Compensation"],
    work_style: ["工作方式", "Work style"],
    conversation_style: ["对话方式", "Conversation style"],
    response_greeting: ["称呼", "Greeting"],
    response_tone: ["回复语气", "Response tone"],
    response_format: ["回复格式", "Response format"],
  };
  const label = labels[field];
  if (label) return locale === "zh-CN" ? label[0] : label[1];
  return field.replaceAll("_", " ");
}

export function groupPreferences(items: PreferenceItem[], locale: string): PreferenceGroup[] {
  const shared: PreferenceItem[] = [];
  const behavior: PreferenceItem[] = [];
  const tracks = new Map<string, PreferenceItem[]>();

  for (const item of items) {
    if (BEHAVIOR_KEYS.has(item.key)) {
      behavior.push(item);
      continue;
    }
    const match = TRACK_KEY.exec(item.key);
    if (!match) {
      shared.push(item);
      continue;
    }
    tracks.set(match[1], [...(tracks.get(match[1]) ?? []), item]);
  }

  const groups: PreferenceGroup[] = [];
  if (shared.length) groups.push({
    id: "shared",
    kind: "shared",
    title: locale === "zh-CN" ? "通用偏好" : "Shared preferences",
    items: shared,
  });
  for (const [trackId, trackItems] of tracks) {
    const name = trackItems.find((item) => TRACK_KEY.exec(item.key)?.[2] === "name")?.value;
    groups.push({
      id: `track-${trackId}`,
      kind: "track",
      title: name ?? trackId,
      items: trackItems,
    });
  }
  if (behavior.length) groups.push({
    id: "behavior",
    kind: "behavior",
    title: locale === "zh-CN" ? "助手表达" : "Assistant responses",
    items: behavior,
  });
  return groups;
}
