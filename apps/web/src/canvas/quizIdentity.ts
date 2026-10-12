import type { CanvasBlock } from "../shared/types";

export function canonicalQuizId(block: CanvasBlock) {
  return block.component_id || block.id;
}
