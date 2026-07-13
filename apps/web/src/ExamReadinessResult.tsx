import { useEffect, useRef } from "react";

import { ExamReviewPlan } from "./ExamReviewPlan";
import { useI18n } from "./i18n";
import type { ExamReadinessAttemptResult, Lecture } from "./types";

export function ExamReadinessResult({
  lectures,
  onOpenLecture,
  result,
}: {
  lectures: Lecture[];
  onOpenLecture: (lecture: Lecture) => void;
  result: ExamReadinessAttemptResult;
}) {
  const { t } = useI18n();
  const status = resultStatus(result);
  const ready = status === "ready";
  const rubricReviewCount = result.results.filter(
    (item) => item.status === "needs_rubric_review",
  ).length;
  const score =
    result.score === null ? t("exam.result.pendingScore") : `${Math.round(result.score * 100)}%`;
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <section className={`exam-result${ready ? " is-ready" : ""}`}>
      <header className="exam-result-summary">
        <div>
          <h3 ref={headingRef} tabIndex={-1}>
            {resultTitle(status, t)}
          </h3>
          <p>{resultHelp(status, t)}</p>
        </div>
        <div className="exam-score" aria-label={t("exam.result.scoreLabel", { score })}>
          <strong>{score}</strong>
          <span>
            {result.score === null
              ? t("exam.result.rubricReview")
              : t("exam.result.target", { target: Math.round(result.passing_score * 100) })}
          </span>
        </div>
      </header>

      <ul className="exam-result-signals" aria-label={t("exam.result.summaryLabel")}>
        <li>
          <strong>{result.tasks.length}</strong> {priorityLabel(result.tasks.length, t)}
        </li>
        <li>
          <strong>{rubricReviewCount}</strong> {rubricLabel(rubricReviewCount, t)}
        </li>
        <li>
          <strong>{t("exam.result.support")}</strong> {guidanceLabel(result.guidance_level, t)}
        </li>
      </ul>

      {result.tasks.length ? (
        <ExamReviewPlan lectures={lectures} tasks={result.tasks} onOpenLecture={onOpenLecture} />
      ) : (
        <p className="exam-result-empty">{t("exam.result.noPriorities")}</p>
      )}
    </section>
  );
}

type Translator = ReturnType<typeof useI18n>["t"];
type ResultStatus = "pending" | "ready" | "review";

function resultStatus(result: ExamReadinessAttemptResult): ResultStatus {
  if (result.score === null) return "pending";
  return result.score >= result.passing_score ? "ready" : "review";
}

function resultTitle(status: ResultStatus, t: Translator) {
  if (status === "pending") return t("exam.result.pending.title");
  if (status === "ready") return t("exam.result.ready.title");
  return t("exam.result.review.title");
}

function resultHelp(status: ResultStatus, t: Translator) {
  if (status === "pending") return t("exam.result.pending.help");
  if (status === "ready") return t("exam.result.ready.help");
  return t("exam.result.review.help");
}

function priorityLabel(count: number, t: Translator) {
  return t(count === 1 ? "exam.result.priority.one" : "exam.result.priority.many");
}

function rubricLabel(count: number, t: Translator) {
  return t(count === 1 ? "exam.result.rubric.one" : "exam.result.rubric.many");
}

function guidanceLabel(level: ExamReadinessAttemptResult["guidance_level"], t: Translator) {
  if (level === "challenge") return t("exam.result.guidance.challenge");
  if (level === "scaffolded") return t("exam.result.guidance.scaffolded");
  return t("exam.result.guidance.standard");
}
