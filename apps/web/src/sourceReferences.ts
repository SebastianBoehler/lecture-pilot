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
      resource: assetSourceResource(asset, references.length + 1),
    });
  }

  return references;
}

export function blockSourceReference(
  references: SectionSourceReference[],
  block: CanvasBlock,
): SectionSourceReference {
  if (block.type !== "asset") return references[0];
  return references.find((reference) => reference.resource.path === (block.asset_path ?? block.caption ?? block.id)) ?? references[0];
}

function lectureSourceResource(canvasDocument: CanvasDocument, section: CanvasSection): WorkspaceResource {
  return {
    id: `source-${canvasDocument.id}-${section.id}`,
    kind: "source",
    label: canvasDocument.source_ref,
    path: canvasDocument.source_ref,
    detail: section.source_ref ?? section.title,
  };
}

function assetSourceResource(asset: CanvasBlock, number: number): WorkspaceResource {
  return {
    id: `asset-${number}-${asset.id}`,
    kind: "asset",
    label: asset.asset_path ?? asset.caption ?? asset.id,
    path: asset.asset_path ?? asset.caption ?? asset.id,
    detail: asset.caption ?? null,
    url: asset.asset_url,
  };
}
