import type { CanvasBlock, CanvasDocument, CanvasSection, WorkspaceResource } from "./types";

export type SectionSourceReference = {
  number: number;
  resource: WorkspaceResource;
};

export function sectionSourceReferences(
  canvasDocument: CanvasDocument,
  section: CanvasSection,
): SectionSourceReference[] {
  const references: SectionSourceReference[] = [
    {
      number: 1,
      resource: lectureSourceResource(canvasDocument, section),
    },
  ];

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
  return references.find((reference) => reference.resource.path === (block.asset_path ?? block.caption ?? block.id)) ?? references[0];
}

function lectureSourceResource(canvasDocument: CanvasDocument, section: CanvasSection): WorkspaceResource {
  const path = displaySourcePath(canvasDocument.source_ref);
  return {
    id: `source-${canvasDocument.id}-${section.id}`,
    kind: "source",
    label: path,
    path,
    sectionId: section.id,
    detail: displaySourceDetail(section.source_ref ?? section.title, path),
  };
}

function displaySourcePath(sourceRef: string) {
  return sourceRef.replace(/^course planner from\s+/i, "").trim() || sourceRef;
}

function displaySourceDetail(detail: string, path: string) {
  return detail.replace(new RegExp(`^${escapeRegExp(path)}\\s*,?\\s*`, "i"), "").trim() || detail;
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function assetSourceResource(asset: CanvasBlock, section: CanvasSection, number: number): WorkspaceResource {
  return {
    id: `asset-${number}-${asset.id}`,
    kind: asset.type === "video" ? "video" : "asset",
    label: asset.asset_path ?? asset.caption ?? asset.id,
    path: asset.asset_path ?? asset.caption ?? asset.id,
    sectionId: section.id,
    blockId: asset.id,
    detail: asset.caption ?? null,
    url: asset.asset_url,
  };
}
