import { useEffect, useRef } from "react";

import { ExamOpenAnswerFeedback } from "./ExamOpenAnswerFeedback";
import { ExamReviewPlan } from "./ExamReviewPlan";
import { useI18n } from "./i18n";
import type { ExamReadinessAttemptResult, ExamReadinessCheck, Lecture } from "./types";

export function ExamReadinessResult({
  check,
  lectures,
  onOpenLecture,
  result,
}: {
  check: ExamReadinessCheck;
  lectures: Lecture[];
  onOpenLecture: (lecture: Lecture) => void;
  result: ExamReadinessAttemptResult;
}) {
  const { t } = useI18n();
  const status = resultStatus(result);
  const ready = status === "ready";
  const reviewTasks = result.tasks.filter((task) => task.kind === "review_wrong_mc");
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
          {result.score !== null ? (
            <span>{t("exam.result.target", { target: Math.round(result.passing_score * 100) })}</span>
          ) : null}
        </div>
      </header>

      <ul className="exam-result-signals" aria-label={t("exam.result.summaryLabel")}>
        <li>
          <strong>{reviewTasks.length}</strong> {priorityLabel(reviewTasks.length, t)}
        </li>
        <li>
          <strong>{t("exam.result.support")}</strong> {guidanceLabel(result.guidance_level, t)}
        </li>
      </ul>

      <ExamOpenAnswerFeedback check={check} results={result.results} />

      {reviewTasks.length ? (
        <ExamReviewPlan lectures={lectures} tasks={reviewTasks} onOpenLecture={onOpenLecture} />
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

function guidanceLabel(level: ExamReadinessAttemptResult["guidance_level"], t: Translator) {
  if (level === "challenge") return t("exam.result.guidance.challenge");
  if (level === "scaffolded") return t("exam.result.guidance.scaffolded");
  return t("exam.result.guidance.standard");
}
