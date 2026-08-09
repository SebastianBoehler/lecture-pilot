import type { CanvasBlock } from "./types";

export function canonicalQuizId(block: CanvasBlock) {
  return block.component_id || block.id;
}
