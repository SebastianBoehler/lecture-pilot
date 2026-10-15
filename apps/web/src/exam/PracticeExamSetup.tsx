import { useState } from "react";

import { useI18n } from "../i18n/i18n";
import { dismissDialogFromBackdrop } from "../shared/dialogBackdrop";
import {
  DEFAULT_PRACTICE_EXAM_QUESTIONS,
  MAX_PRACTICE_EXAM_QUESTIONS,
  MIN_PRACTICE_EXAM_QUESTIONS,
} from "./practiceExamLimits";
import type { PracticeExamGenerationInput } from "./practiceExamTypes";
import type { UniversityCourse } from "../shared/types";
import { useModalDialog } from "../shared/useModalDialog";

export function PracticeExamSetup({
  course,
  error,
  generating,
  onClose,
  onGenerate,
}: {
  course: UniversityCourse;
  error: string | null;
  generating: boolean;
  onClose: () => void;
  onGenerate: (input: PracticeExamGenerationInput) => void;
}) {
  const { t } = useI18n();
  const [questionCount, setQuestionCount] = useState(DEFAULT_PRACTICE_EXAM_QUESTIONS);
  const [duration, setDuration] = useState(90);
  const [choiceFormat, setChoiceFormat] = useState<"single_answer" | "multiple_answers">(
    "single_answer",
  );
  const dialogRef = useModalDialog();

  return (
    <dialog
      aria-labelledby="practice-exam-setup-title"
      aria-modal="true"
      className="practice-exam-dialog"
      ref={dialogRef}
      onClick={(event) => dismissDialogFromBackdrop(event, onClose)}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <header>
        <div className="practice-exam-dialog-heading">
          <h2 id="practice-exam-setup-title">{t("practice.setup.title")}</h2>
          <p className="practice-exam-course">
            {t("practice.setup.course", { course: course.title })}
          </p>
        </div>
        <button
          aria-label={t("practice.setup.close")}
          className="practice-exam-dialog-close"
          type="button"
          onClick={onClose}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="m6 6 12 12M18 6 6 18" />
          </svg>
        </button>
      </header>
      <div className="practice-exam-dialog-body">
        {error ? (
          <p className="practice-exam-error" role="alert">
            {error}
          </p>
        ) : null}
        <div className="practice-exam-settings">
          <label>
            <span>{t("practice.setup.questions")}</span>
            <input
              max={MAX_PRACTICE_EXAM_QUESTIONS}
              min={MIN_PRACTICE_EXAM_QUESTIONS}
              type="number"
              value={questionCount}
              onChange={(event) => setQuestionCount(Number(event.currentTarget.value))}
            />
          </label>
          <label>
            <span>{t("practice.setup.duration")}</span>
            <input
              max={300}
              min={30}
              type="number"
              value={duration}
              onChange={(event) => setDuration(Number(event.currentTarget.value))}
            />
          </label>
        </div>
        <label className="practice-exam-choice-format">
          <span>{t("practice.setup.choiceFormat")}</span>
          <select
            value={choiceFormat}
            disabled={generating}
            onChange={(event) => setChoiceFormat(event.currentTarget.value as typeof choiceFormat)}
          >
            <option value="single_answer">{t("practice.setup.singleAnswer")}</option>
            <option value="multiple_answers">{t("practice.setup.multipleAnswers")}</option>
          </select>
        </label>
        {choiceFormat === "multiple_answers" ? <p>{t("practice.multipleRule")}</p> : null}
        <p className="practice-exam-scope-help">{t("practice.setup.help")}</p>
      </div>
      <footer>
        <button type="button" onClick={onClose}>
          {t("practice.cancel")}
        </button>
        <button
          className="practice-primary"
          disabled={
            generating ||
            questionCount < MIN_PRACTICE_EXAM_QUESTIONS ||
            questionCount > MAX_PRACTICE_EXAM_QUESTIONS
          }
          type="button"
          onClick={() =>
            onGenerate({
              question_count: questionCount,
              duration_minutes: duration,
              choice_format: choiceFormat,
            })
          }
        >
          {generating
            ? t("practice.generating")
            : t("practice.generateCount", { count: questionCount })}
        </button>
      </footer>
    </dialog>
  );
}
