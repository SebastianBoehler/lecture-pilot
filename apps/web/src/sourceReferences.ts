import type { CanvasBlock, CanvasDocument, CanvasSection, WorkspaceResource } from "./types";

export type SectionSourceReference = {
  number: number;
  resource: WorkspaceResource;
};

export function sectionSourceReferences(
  canvasDocument: CanvasDocument,
  section: CanvasSection,
): SectionSourceReference[] {
  const lectureResources = lectureSourceResources(canvasDocument, section);
  const references: SectionSourceReference[] = lectureResources.map((resource, index) => ({
    number: index + 1,
    resource,
  }));

  for (const asset of section.blocks.filter((block) => block.asset_path || block.asset_url)) {
    const path = asset.asset_path ?? asset.caption ?? asset.id;
    if (references.some((reference) => reference.resource.path === path)) continue;
    references.push({
      number: references.length + 1,
      resource: assetSourceResource(asset, section, references.length + 1),
    });
  }

  return references;
}

export function blockSourceReference(
  references: SectionSourceReference[],
  block: CanvasBlock,
): SectionSourceReference {
  if (block.type !== "asset" && block.type !== "video") return references[0];
  return (
    references.find(
      (reference) => reference.resource.path === (block.asset_path ?? block.caption ?? block.id),
    ) ?? references[0]
  );
}

function lectureSourceResources(
  canvasDocument: CanvasDocument,
  section: CanvasSection,
): WorkspaceResource[] {
  const exactSources = sourceEntries(section.source_ref ?? "");
  const sources = exactSources.length
    ? exactSources
    : sourceEntries(displaySourcePath(canvasDocument.source_ref));
  if (!exactSources.length && sources.length === 1 && section.source_ref) {
    sources[0].detail = displaySourceDetail(section.source_ref, sources[0].path);
  }
  if (!sources.length) {
    const path = displaySourcePath(canvasDocument.source_ref);
    sources.push({ path, detail: displaySourceDetail(section.source_ref ?? section.title, path) });
  }
  return sources.map(({ path, detail }, index) => ({
    id: `source-${canvasDocument.id}-${section.id}-${index + 1}`,
    kind: "source",
    label: sourceFileName(path),
    path,
    sectionId: section.id,
    detail,
  }));
}

function displaySourcePath(sourceRef: string) {
  return sourceRef.replace(/^course planner from\s+/i, "").trim() || sourceRef;
}

function sourceEntries(sourceRef: string): { path: string; detail: string | null }[] {
  const value = displaySourcePath(sourceRef);
  const matches = [...value.matchAll(SOURCE_PATH_RE)];
  return matches.map((match, index) => {
    const path = match[0].trim();
    const detailStart = (match.index ?? 0) + match[0].length;
    const detailEnd = matches[index + 1]?.index ?? value.length;
    return {
      path,
      detail: cleanSourceDetail(value.slice(detailStart, detailEnd)),
    };
  });
}

function cleanSourceDetail(value: string): string | null {
  let detail = value.replace(/^[\s,;:]+|[\s,;]+$/g, "").trim();
  if (detail.startsWith("(") && detail.endsWith(")")) detail = detail.slice(1, -1).trim();
  return detail || null;
}

function sourceFileName(path: string) {
  return path.split("/").filter(Boolean).at(-1) ?? path;
}

function displaySourceDetail(detail: string, path: string) {
  return detail.replace(new RegExp(`^${escapeRegExp(path)}\\s*,?\\s*`, "i"), "").trim() || detail;
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function assetSourceResource(
  asset: CanvasBlock,
  section: CanvasSection,
  number: number,
): WorkspaceResource {
  const path = asset.asset_path ?? asset.caption ?? asset.id;
  return {
    id: `asset-${number}-${asset.id}`,
    kind: asset.type === "video" ? "video" : "asset",
    label: sourceFileName(path),
    path,
    sectionId: section.id,
    blockId: asset.id,
    detail: asset.caption ?? null,
    url: asset.asset_url,
  };
}

const SOURCE_PATH_RE =
  /(?:[\p{L}\p{N}_@()+.\- ]+\/)*[\p{L}\p{N}_@()+.\- ]+\.(?:tex|sty|pdf|md|txt|ipynb|json|png|jpe?g|svg|webp|gif|mp4|webm)/giu;
