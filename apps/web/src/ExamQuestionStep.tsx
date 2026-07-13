import { useEffect, useRef } from "react";

import { useI18n } from "./i18n";
import type { ExamReadinessQuestion } from "./types";

export function ExamQuestionStep({
  answer,
  onAnswer,
  question,
}: {
  answer: number | string | undefined;
  onAnswer: (answer: number | string) => void;
  question: ExamReadinessQuestion;
}) {
  const { t } = useI18n();
  const legendRef = useRef<HTMLLegendElement>(null);
  const contextId = `exam-question-context-${question.id}`;

  useEffect(() => {
    legendRef.current?.focus();
  }, [question.id]);

  return (
    <fieldset className="exam-question" aria-describedby={contextId}>
      <legend ref={legendRef} tabIndex={-1}>
        {question.prompt}
      </legend>
      <p className="exam-question-context" id={contextId}>
        {question.lecture_title} <span aria-hidden="true">·</span> {question.section_title}
      </p>
      {question.kind === "multiple_choice" ? (
        <div className="exam-options">
          {question.options.map((option, optionIndex) => (
            <label
              className={answer === optionIndex ? "is-selected" : undefined}
              key={`${question.id}-${optionIndex}`}
            >
              <input
                checked={answer === optionIndex}
                name={question.id}
                type="radio"
                onChange={() => onAnswer(optionIndex)}
              />
              <span>{option}</span>
            </label>
          ))}
        </div>
      ) : (
        <textarea
          aria-label={t("exam.answer.label")}
          placeholder={t("exam.answer.placeholder")}
          rows={6}
          value={typeof answer === "string" ? answer : ""}
          onChange={(event) => onAnswer(event.target.value)}
        />
      )}
    </fieldset>
  );
}
