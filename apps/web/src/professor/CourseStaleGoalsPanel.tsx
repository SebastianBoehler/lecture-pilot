import { useEffect, useState } from "react";

import { useI18n } from "../i18n/i18n";
import { errorMessage } from "../shared/errorMessage";
import type { LoginSession } from "../shared/types";
import type { LectureState } from "./courseLectureStateTypes";
import type { DiffGoal } from "./goalDiff";
import { getPracticeDesign } from "./practiceDesignApi";
import type { PracticeDesign } from "./practiceDesignTypes";
import type { LecturePending } from "./useCourseLectureActions";

/** Sources changed after approval: keep the approved goals or regenerate and compare. */
export function CourseStaleGoalsPanel({
  courseId,
  lecture,
  session,
  pending,
  onKeep,
  onRegenerate,
}: {
  courseId: string;
  lecture: LectureState;
  session: LoginSession;
  pending?: LecturePending;
  onKeep: () => void;
  onRegenerate: (previous: readonly DiffGoal[]) => void;
}) {
  const { t } = useI18n();
  const [design, setDesign] = useState<PracticeDesign | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lectureId = lecture.lecture_id;

  useEffect(() => {
    let active = true;
    getPracticeDesign({ courseId, lectureId, session }).then(
      (loaded) => active && setDesign(loaded),
      (cause: unknown) =>
        active && setError(errorMessage(cause, "Learning goals could not be loaded.")),
    );
    return () => {
      active = false;
    };
  }, [courseId, lectureId, session]);

  const goals = design?.learning_intent.goals ?? [];
  return (
    <section className="lecture-panel" aria-labelledby={`stale-${lectureId}`}>
      <h3 id={`stale-${lectureId}`}>{t("coursePage.stale.title")}</h3>
      <p className="lecture-panel-help">{t("coursePage.stale.help")}</p>
      {error ? <p role="alert">{error}</p> : null}
      {!design && !error ? <p role="status">{t("coursePage.goals.loading")}</p> : null}
      {goals.length ? (
        <ol className="course-goal-list">
          {goals.map((goal) => (
            <li key={goal.id}>
              <strong>{goal.title}</strong>
              <p>{goal.outcome}</p>
            </li>
          ))}
        </ol>
      ) : null}
      <div className="lecture-panel-actions">
        <button
          className="course-row-button"
          data-primary
          type="button"
          disabled={Boolean(pending) || !design}
          onClick={onKeep}
        >
          {pending === "keeping" ? t("coursePage.pending.keeping") : t("coursePage.stale.keep")}
        </button>
        <button
          className="course-row-button"
          type="button"
          disabled={Boolean(pending) || !design}
          onClick={() =>
            onRegenerate(goals.map(({ id, title, outcome }) => ({ id, title, outcome })))
          }
        >
          {pending === "regenerating"
            ? t("coursePage.pending.regenerating")
            : t("coursePage.stale.regenerate")}
        </button>
      </div>
    </section>
  );
}
