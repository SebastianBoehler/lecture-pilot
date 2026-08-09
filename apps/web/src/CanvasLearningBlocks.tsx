import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";

import { MathText } from "./MathText";
import { useI18n } from "./i18n";
import type { LearnerQuizAnswerResult } from "./analyticsApi";
import type { MessageKey } from "./i18nMessages";
import type { LearnerQuizState } from "./learnerLessonStateTypes";
import type { CanvasBlock } from "./types";

type LearningBlockProps = {
  block: CanvasBlock;
  className: string;
  highlightedText: string | null;
  sourceMarker: ReactNode;
  sectionId?: string;
  quizState?: LearnerQuizState;
  onSubmitAnswer?: (
    block: CanvasBlock,
    answer: string,
    optionIndex: number,
    attemptId: string,
  ) => Promise<LearnerQuizAnswerResult>;
  onSubmitCheckpoint?: (gateId: string, sectionId: string, answer: string) => Promise<void>;
};

export function CheckpointBlock({
  block,
  className,
  highlightedText,
  onSubmitCheckpoint,
  sectionId,
  sourceMarker,
}: LearningBlockProps) {
  const { t } = useI18n();
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!answer.trim() || !onSubmitCheckpoint || !sectionId) return;
    setSubmitting(true);
    setError(null);
    setStatus(null);
    try {
      await onSubmitCheckpoint(block.id, sectionId, answer.trim());
      setStatus(t("checkpoint.submitted"));
    } catch (reason) {
      setError(errorMessage(reason, t("attempt.failed")));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <aside className={`${className} canvas-checkpoint`} id={block.id} key={block.id}>
      <div className="canvas-learning-label">{block.caption || t("checkpoint.label")}</div>
      <div className="canvas-markdown">
        <MathText highlightedText={highlightedText} mode="block" text={block.text ?? ""} />
      </div>
      {onSubmitCheckpoint && sectionId ? (
        <form className="canvas-checkpoint-form" onSubmit={submit}>
          <label htmlFor={`${block.id}-answer`}>{t("checkpoint.answer")}</label>
          <textarea
            id={`${block.id}-answer`}
            value={answer}
            disabled={submitting}
            placeholder={t("checkpoint.answerPlaceholder")}
            required
            rows={4}
            onChange={(event) => setAnswer(event.target.value)}
          />
          <button className="primary-button" disabled={submitting || !answer.trim()} type="submit">
            {submitting ? t("checkpoint.submitting") : t("checkpoint.submit")}
          </button>
          {status ? <p role="status">{status}</p> : null}
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
        </form>
      ) : null}
      {sourceMarker}
    </aside>
  );
}

export function QuizBlock({ block, className, onSubmitAnswer, quizState }: LearningBlockProps) {
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
    if (!onSubmitAnswer || checking || result) return;
    setSelectedIndex(optionIndex);
    setChecking(true);
    setError(null);
    attemptId.current ??= newAttemptId(block.id);
    try {
      const accepted = await onSubmitAnswer(block, answer, optionIndex, attemptId.current);
      setResult(accepted);
      attemptId.current = null;
    } catch (reason) {
      setSelectedIndex(null);
      setError(errorMessage(reason, t("attempt.failed")));
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

  const locked = checking || result !== null;
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

export function TableBlock({
  block,
  className,
  highlightedText,
  sourceMarker,
}: LearningBlockProps) {
  const table = parseMarkdownTable(block.text ?? "");
  if (!table) {
    return (
      <pre className={`${className} canvas-table-fallback`} id={block.id} key={block.id}>
        {block.text}
        {sourceMarker}
      </pre>
    );
  }
  return (
    <figure className={`${className} canvas-table`} id={block.id} key={block.id}>
      <table>
        <thead>
          <tr>
            {table.headers.map((header) => (
              <th key={header}>
                <MathText highlightedText={highlightedText} text={header} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr key={`${block.id}-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${block.id}-${rowIndex}-${cellIndex}`}>
                  <MathText highlightedText={highlightedText} text={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {sourceMarker}
    </figure>
  );
}

function parseMarkdownTable(markdown: string) {
  const lines = markdown
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length < 2 || !lines[0].includes("|") || !/^\|?\s*:?-{3,}/.test(lines[1])) return null;
  const headers = splitRow(lines[0]);
  const rows = lines
    .slice(2)
    .map(splitRow)
    .filter((row) => row.length);
  return { headers, rows };
}

function splitRow(line: string) {
  return line
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
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
