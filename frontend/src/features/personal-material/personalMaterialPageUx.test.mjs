import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";

const pageUrl = new URL("./PersonalMaterialPage.tsx", import.meta.url);
const identifier = "[A-Za-z_$][\\w$]*";

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

test("copy actions close the success and manual fallback loop", async () => {
  const page = await readFile(pageUrl, "utf8");
  assert.match(page, new RegExp(`if \\(await copyToClipboard\\(${identifier}\\)\\)`));

  const resetTimeout = page.match(new RegExp(
    `${identifier}\\.current\\s*=\\s*setTimeout\\(\\(\\)\\s*=>\\s*\\{`
    + `(?<callback>[\\s\\S]*?)\\},\\s*2_?000\\)`,
  ));
  assert.ok(resetTimeout?.groups);
  assert.match(resetTimeout.groups.callback, new RegExp(`${identifier}\\(null\\)`));
  assert.match(resetTimeout.groups.callback, new RegExp(`${identifier}\\(""\\)`));

  assert.match(page, new RegExp(`aria-live="polite">\\{${identifier}\\}<\\/span>`));
  assert.match(
    page,
    new RegExp(
      `if \\(await copyToClipboard\\(${identifier}\\)\\) \\{[\\s\\S]*?return;\\s*\\}`
      + `\\s*${identifier}\\(null\\);\\s*${identifier}\\(\\{\\s*${identifier},`
      + `\\s*${identifier}\\s*\\}\\)`,
    ),
  );
  assert.match(
    page,
    new RegExp(
      `\\{(?<fallback>${identifier}) && \\([\\s\\S]*?<textarea\\s+readOnly`
      + `\\s+value=\\{\\k<fallback>\\.text\\}[\\s\\S]*?`
      + `onFocus=\\{\\(${identifier}\\) => ${identifier}\\.currentTarget\\.select\\(\\)\\}`,
    ),
  );
});

test("multi-select preserves click order and exposes the complete action bar", async () => {
  const page = await readFile(pageUrl, "utf8");
  const selectionState = page.match(new RegExp(
    `const \\[(?<ids>${identifier}),\\s*(?<setIds>${identifier})\\]`
    + `\\s*=\\s*useState<number\\[\\]>\\(\\[\\]\\);`,
  ));
  assert.ok(selectionState?.groups);
  const ids = escapeRegExp(selectionState.groups.ids);
  const setIds = escapeRegExp(selectionState.groups.setIds);

  const selectedCollection = page.match(new RegExp(
    `const\\s+(?<selected>${identifier})\\s*=\\s*useMemo\\(\\s*\\(\\) => ${ids}`
    + `\\s*\\.map\\(\\(${identifier}\\) => ${identifier}\\.find\\(`,
  ));
  assert.ok(selectedCollection?.groups);
  const selected = escapeRegExp(selectedCollection.groups.selected);

  const toggle = page.match(new RegExp(
    `function\\s+${identifier}\\((?<blockId>${identifier}):\\s*number\\)\\s*\\{\\s*${setIds}`
    + `\\(\\((?<current>${identifier})\\) => (?<body>[\\s\\S]*?)\\);\\s*\\}`,
  ));
  assert.ok(toggle?.groups);
  const blockId = escapeRegExp(toggle.groups.blockId);
  const current = escapeRegExp(toggle.groups.current);
  assert.match(
    toggle.groups.body,
    new RegExp(
      `${current}\\.includes\\(${blockId}\\)\\s*\\?\\s*${current}\\.filter\\(`
      + `\\(${identifier}\\) => ${identifier} !== ${blockId}\\)\\s*:\\s*`
      + `\\[\\.\\.\\.${current},\\s*${blockId}\\]`,
    ),
  );

  assert.match(
    page,
    new RegExp(
      `const\\s+(?<index>${identifier})\\s*=\\s*${ids}\\.indexOf\\(${identifier}\\.id\\)`
      + `[\\s\\S]*?\\{\\k<index>\\s*\\+\\s*1\\}`,
    ),
  );
  assert.match(
    page,
    new RegExp(
      `\\$\\{${selected}\\.length\\} selected[\\s\\S]*?`
      + `onClick=\\{\\(\\) => ${setIds}\\(\\[\\]\\)\\}[\\s\\S]*?`
      + `l\\("清空", "Clear"\\)[\\s\\S]*?mergeMaterialBodies\\(`
      + `${selected}\\.map\\(\\(${identifier}\\) => ${identifier}\\.body\\)\\)`
      + `[\\s\\S]*?l\\("合并复制", "Copy combined"\\)`,
    ),
  );
});

test("write conflicts and missing rows close the editor and refresh", async () => {
  const page = await readFile(pageUrl, "utf8");
  for (const status of [409, 404]) {
    assert.match(
      page,
      new RegExp(
        `(?<caught>${identifier}) instanceof HttpError && \\k<caught>\\.status === ${status}\\)`
        + ` \\{\\s*${identifier}\\(null\\);\\s*await ${identifier}\\(\\)`,
      ),
    );
  }
});

test("in-memory filters preserve language, type-or, and tag-and semantics", async () => {
  const page = await readFile(pageUrl, "utf8");
  assert.match(
    page,
    new RegExp(`\\(\\["all", "zh", "en"\\] as ${identifier}\\[\\]\\)\\.map`),
  );
  assert.match(
    page,
    new RegExp(
      `if \\(${identifier} !== "all" && ${identifier}\\.language !== ${identifier}\\) return false`,
    ),
  );
  assert.match(
    page,
    new RegExp(
      `if \\(${identifier}\\.size > 0 && !${identifier}\\.has\\(${identifier}\\.block_type\\)\\)`
      + " return false",
    ),
  );
  assert.match(
    page,
    new RegExp(
      `if \\(!\\[\\.\\.\\.${identifier}\\]\\.every\\(\\(${identifier}\\) => `
      + `${identifier}\\.includes\\(${identifier}\\)\\)\\) return false`,
    ),
  );

  const filteredCollection = [...page.matchAll(new RegExp(
    `const\\s+(?<filtered>${identifier})\\s*=\\s*useMemo\\(\\(\\) => \\{`
    + `(?<body>[\\s\\S]*?)\\n\\s*\\},\\s*\\[`,
    "g",
  ))].find((match) => new RegExp(`return ${identifier}\\.filter\\(`)
    .test(match.groups?.body ?? ""));
  assert.ok(filteredCollection?.groups);
  assert.match(
    page,
    new RegExp(`\\{\\s*${escapeRegExp(filteredCollection.groups.filtered)}\\.map\\(`),
  );
});

test("refresh cancels stale reads and guards state updates with an epoch", async () => {
  const page = await readFile(pageUrl, "utf8");
  assert.match(
    page,
    new RegExp(
      `(?<controllerRef>${identifier})\\.current\\?\\.abort\\(\\);\\s*`
      + `const (?<controller>${identifier}) = new AbortController\\(\\);\\s*`
      + `const (?<epoch>${identifier}) = \\+\\+(?<epochRef>${identifier})\\.current;\\s*`
      + `\\k<controllerRef>\\.current = \\k<controller>;[\\s\\S]*?`
      + `getMaterialBlocks\\(${identifier}, \\k<controller>\\.signal\\);\\s*`
      + `if \\(\\k<epoch> !== \\k<epochRef>\\.current \\|\\| \\k<controller>\\.signal\\.aborted\\)`,
    ),
  );
});
