import type { ReactNode } from "react";

import { QuizBlock } from "./CanvasLearningBlocks";
import type { CanvasBlock } from "./types";

type ComponentBlockProps = {
  block: CanvasBlock;
  className: string;
  sourceMarker: ReactNode;
  onSubmitAnswer: (block: CanvasBlock, answer: string, optionIndex: number) => void;
};

export function ComponentBlock({
  block,
  className,
  onSubmitAnswer,
  sourceMarker,
}: ComponentBlockProps) {
  if (block.component_type === "single_choice_quiz") {
    return (
      <QuizBlock
        block={block}
        className={`${className} canvas-component`}
        highlightedText={null}
        sourceMarker={null}
        onSubmitAnswer={onSubmitAnswer}
      />
    );
  }
  return (
    <aside className={`${className} canvas-component canvas-component-unsupported`} id={block.id}>
      <div className="canvas-learning-label">Interactive component</div>
      <strong>{block.caption || block.component_id || "Unsupported component"}</strong>
      <p>
        This course component type is not enabled yet:{" "}
        <code>{block.component_type || "unknown"}</code>
      </p>
      {sourceMarker}
    </aside>
  );
}
