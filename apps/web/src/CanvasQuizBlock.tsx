import { useEffect, useRef, useState, type ReactNode } from "react";

import { MathText } from "./MathText";
import { StaleQuizPublicationError, type LearnerQuizAnswerResult } from "./analyticsApi";
import { useI18n } from "./i18n";
import type { MessageKey } from "./i18nMessages";
import type { LearnerQuizState } from "./learnerLessonStateTypes";
import type { CanvasBlock } from "./types";

type QuizBlockProps = {
  block: CanvasBlock;
  className: string;
  highlightedText: string | null;
  sourceMarker: ReactNode;
  quizState?: LearnerQuizState;
  publicationVersion?: number | null;
  onSubmitAnswer?: (
    block: CanvasBlock,
    answer: string,
    optionIndex: number,
    attemptId: string,
    publicationVersion: number,
  ) => Promise<LearnerQuizAnswerResult>;
};

export function QuizBlock({
  block,
  className,
  onSubmitAnswer,
  publicationVersion,
  quizState,
}: QuizBlockProps) {
  const { t } = useI18n();
  const [selectedIndex, setSelectedIndex] = useState<number | null>(
    quizState?.selected_index ?? null,
  );
  const [result, setResult] = useState<LearnerQuizState | null>(quizState ?? null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const attemptId = useRef<string | null>(null);

  useEffect(() => {
    setSelectedIndex(quizState?.selected_index ?? null);
    setResult(quizState ?? null);
  }, [quizState]);

  async function submit(answer: string, optionIndex: number) {
    if (!onSubmitAnswer || !publicationVersion || checking || result) return;
    setSelectedIndex(optionIndex);
    setChecking(true);
    setError(null);
    attemptId.current ??= newAttemptId(block.id);
    try {
      const accepted = await onSubmitAnswer(
        block,
        answer,
        optionIndex,
        attemptId.current,
        publicationVersion,
      );
      setResult(accepted);
      attemptId.current = null;
    } catch (reason) {
      const stalePublication = reason instanceof StaleQuizPublicationError;
      if (stalePublication) attemptId.current = null;
      setSelectedIndex(null);
      setError(errorMessage(reason, t("attempt.failed")));
      if (stalePublication) window.location.reload();
    } finally {
      setChecking(false);
    }
  }

  function beginCorrection() {
    setSelectedIndex(null);
    setResult(null);
    setError(null);
    attemptId.current = null;
  }

  const locked = !publicationVersion || checking || result !== null;
  return (
    <section className={`${className} canvas-quiz`} id={block.id} key={block.id}>
      <div className="canvas-learning-label">{block.caption || t("quiz.label")}</div>
      <div className="canvas-markdown">
        <MathText highlightedText={null} mode="block" text={block.text ?? ""} />
      </div>
      {block.items.length ? (
        <ol className="canvas-quiz-options">
          {block.items.map((item, index) => (
            <li key={item}>
              <button
                aria-label={`${optionLetter(index)} ${item}`}
                aria-pressed={selectedIndex === index}
                className={quizOptionClass(index, selectedIndex, result)}
                disabled={locked}
                type="button"
                onClick={() => void submit(item, index)}
              >
                <span>{optionLetter(index)}</span>
                <span className="canvas-quiz-option-text">
                  <MathText highlightedText={null} text={item} />
                </span>
                {quizResultLabel(index, selectedIndex, result, t("quiz.review")) ? (
                  <span aria-hidden="true" className="canvas-quiz-result">
                    {quizResultLabel(index, selectedIndex, result, t("quiz.review"))}
                  </span>
                ) : null}
              </button>
            </li>
          ))}
        </ol>
      ) : null}
      {checking ? <p role="status">{t("quiz.checking")}</p> : null}
      {result ? (
        <div className="canvas-quiz-feedback" role="status">
          <strong>{outcomeLabel(result, t)}</strong>
          <p>{guidance(result, t)}</p>
        </div>
      ) : null}
      {result?.correction_state === "needed" ? (
        <button className="secondary-button" type="button" onClick={beginCorrection}>
          {t("quiz.tryCorrection")}
        </button>
      ) : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}

function optionLetter(index: number) {
  return String.fromCharCode(65 + index);
}

function quizOptionClass(
  index: number,
  selectedIndex: number | null,
  result: LearnerQuizState | null,
) {
  if (selectedIndex !== index) return "";
  if (!result) return "is-selected";
  if (result.correct === true) return "is-correct";
  if (result.correct === false) return "is-incorrect";
  return "is-selected";
}

function quizResultLabel(
  index: number,
  selectedIndex: number | null,
  result: LearnerQuizState | null,
  review: string,
) {
  if (!result || selectedIndex !== index) return null;
  if (result.correct === true) return "✓";
  if (result.correct === false) return review;
  return "";
}

function outcomeLabel(result: LearnerQuizState, t: (key: MessageKey) => string) {
  if (result.latest_outcome === "correct") return t("quiz.correct");
  if (result.latest_outcome === "incorrect") return t("quiz.incorrect");
  return t("quiz.unscored");
}

function guidance(result: LearnerQuizState, t: (key: MessageKey) => string) {
  if (result.latest_outcome === "correct") return t("quiz.correctGuidance");
  if (result.latest_outcome === "incorrect") return t("quiz.repairGuidance");
  return t("quiz.unscoredGuidance");
}

function newAttemptId(blockId: string) {
  return `${blockId}:${crypto.randomUUID()}`;
}

function errorMessage(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback;
}
