import type { CanvasBlock } from "./types";

export function findKeySourceBlockId(blocks: CanvasBlock[]) {
  return (
    blocks.find((block) => block.type === "callout")?.id ??
    blocks.find((block) => block.type === "checkpoint")?.id ??
    blocks.find((block) => block.type === "list")?.id ??
    blocks.find((block) => block.type === "paragraph")?.id ??
    null
  );
}

export function shouldShowSourceMarker(block: CanvasBlock, keySourceBlockId: string | null) {
  if (block.type === "quiz" || block.type === "component") return false;
  return Boolean((block.type === "asset" || block.type === "video") && block.asset_url) || block.id === keySourceBlockId;
}
