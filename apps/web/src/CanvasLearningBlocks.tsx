import { useState, type FormEvent, type ReactNode } from "react";

import { MathText } from "./MathText";
import { useI18n } from "./i18n";
import type { LearnerQuizAnswerResult } from "./analyticsApi";
import type { LearnerQuizState } from "./learnerLessonStateTypes";
import type { CanvasBlock } from "./types";

export { QuizBlock } from "./CanvasQuizBlock";

type LearningBlockProps = {
  block: CanvasBlock;
  className: string;
  highlightedText: string | null;
  sourceMarker: ReactNode;
  sectionId?: string;
  quizState?: LearnerQuizState;
  publicationVersion?: number | null;
  onSubmitAnswer?: (
    block: CanvasBlock,
    answer: string,
    optionIndex: number,
    attemptId: string,
    publicationVersion: number,
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

function errorMessage(reason: unknown, fallback: string) {
  return reason instanceof Error ? reason.message : fallback;
}
