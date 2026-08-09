import type { ComponentType, ReactNode } from "react";

import { InteractiveChart } from "./CanvasInteractiveChart";
import { QuizBlock } from "./CanvasLearningBlocks";
import { ProcessExplorer } from "./CanvasProcessExplorer";
import { useI18n } from "./i18n";
import type { LearnerQuizAnswerResult } from "./analyticsApi";
import type { LearnerQuizState } from "./learnerLessonStateTypes";
import type { CanvasBlock } from "./types";

export type ComponentRendererProps = {
  block: CanvasBlock;
  className: string;
  sourceMarker: ReactNode;
  quizState?: LearnerQuizState;
  onSubmitAnswer: (
    block: CanvasBlock,
    answer: string,
    optionIndex: number,
    attemptId: string,
  ) => Promise<LearnerQuizAnswerResult>;
};

const componentRegistry: Record<string, ComponentType<ComponentRendererProps>> = {
  single_choice_quiz: SingleChoiceQuiz,
  interactive_chart: InteractiveChart,
  process_explorer: ProcessExplorer,
};

export function ComponentBlock({
  block,
  className,
  onSubmitAnswer,
  quizState,
  sourceMarker,
}: ComponentRendererProps) {
  const { t } = useI18n();
  const Renderer = componentRegistry[block.component_type || ""];
  if (Renderer)
    return (
      <Renderer
        block={block}
        className={className}
        sourceMarker={sourceMarker}
        quizState={quizState}
        onSubmitAnswer={onSubmitAnswer}
      />
    );
  return (
    <aside className={`${className} canvas-component canvas-component-unsupported`} id={block.id}>
      <div className="canvas-learning-label">{t("component.unsupported.label")}</div>
      <strong>{block.caption || block.component_id || t("component.unsupported.title")}</strong>
      <p>
        {t("component.unsupported.message")} <code>{block.component_type || "unknown"}</code>
      </p>
      {sourceMarker}
    </aside>
  );
}

function SingleChoiceQuiz({ block, className, onSubmitAnswer, quizState }: ComponentRendererProps) {
  return (
    <QuizBlock
      block={block}
      className={`${className} canvas-component`}
      highlightedText={null}
      sourceMarker={null}
      quizState={quizState}
      onSubmitAnswer={onSubmitAnswer}
    />
  );
}
