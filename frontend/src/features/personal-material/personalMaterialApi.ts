import { getJson, postJson, putJson } from "../../shared/api/transport";
import {
  parseMaterialBlock,
  parseMaterialBlocks,
  type MaterialBlock,
  type MaterialBlockInput,
} from "./personalMaterialContract";

export async function getMaterialBlocks(
  includeArchived: boolean,
  signal?: AbortSignal,
): Promise<MaterialBlock[]> {
  const url = includeArchived
    ? "/api/personal-material/blocks?include_archived=true"
    : "/api/personal-material/blocks";
  return parseMaterialBlocks(await getJson<unknown>(url, { signal }));
}

export async function createMaterialBlock(input: MaterialBlockInput): Promise<MaterialBlock> {
  return parseMaterialBlock(await postJson<unknown>("/api/personal-material/blocks", input));
}

export async function updateMaterialBlock(
  id: number,
  input: MaterialBlockInput,
  expectedRevision: number,
): Promise<MaterialBlock> {
  return parseMaterialBlock(await putJson<unknown>(`/api/personal-material/blocks/${id}`, {
    ...input,
    expected_revision: expectedRevision,
  }));
}

export async function archiveMaterialBlock(
  id: number,
  expectedRevision: number,
): Promise<MaterialBlock> {
  return parseMaterialBlock(await postJson<unknown>(
    `/api/personal-material/blocks/${id}/archive`,
    { expected_revision: expectedRevision },
  ));
}

export async function restoreMaterialBlock(
  id: number,
  expectedRevision: number,
): Promise<MaterialBlock> {
  return parseMaterialBlock(await postJson<unknown>(
    `/api/personal-material/blocks/${id}/restore`,
    { expected_revision: expectedRevision },
  ));
}
