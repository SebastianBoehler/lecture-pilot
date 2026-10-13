import { useEffect, useState } from "react";

import { useI18n } from "../i18n/i18n";
import { errorMessage } from "../shared/errorMessage";
import type { LoginSession } from "../shared/types";
import type { LectureState } from "./courseLectureStateTypes";
import { diffGoals, type DiffGoal } from "./goalDiff";
import { GoalDiffList } from "./GoalDiffList";
import type { LearningIntentApprovalOptions } from "./learningIntentTypes";
import {
  approvePracticeDesign,
  getPracticeDesign,
  PracticeDesignRequestError,
  proposePracticeDesign,
  updatePracticeDesign,
} from "./practiceDesignApi";
import type { PracticeDesign } from "./practiceDesignTypes";
import { updateFor } from "./ProfessorPracticeDesignStep.helpers";
import { ProfessorLearningIntent } from "./ProfessorLearningIntent";

/** Proposed goals for one lecture, reviewed with the builder's goal editor; approval drafts. */
export function CourseGoalReviewPanel({
  courseId,
  lecture,
  session,
  previousGoals,
  onApproved,
}: {
  courseId: string;
  lecture: LectureState;
  session: LoginSession;
  previousGoals?: readonly DiffGoal[];
  onApproved: () => void;
}) {
  const { t } = useI18n();
  const lectureId = lecture.lecture_id;
  const [design, setDesign] = useState<PracticeDesign | null>(null);
  const [draft, setDraft] = useState<PracticeDesign | null>(null);
  const [pending, setPending] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getPracticeDesign({ courseId, lectureId, session }).then(
      (loaded) => {
        if (!active) return;
        setDesign(loaded);
        setDraft(loaded);
      },
      (cause: unknown) =>
        active && setError(errorMessage(cause, "Learning goals could not be loaded.")),
    );
    return () => {
      active = false;
    };
  }, [courseId, lectureId, session]);

  async function run(work: () => Promise<PracticeDesign>, after?: () => void) {
    setPending(true);
    setError(null);
    try {
      const next = await work();
      setDesign(next);
      setDraft(next);
      setConflict(false);
      after?.();
    } catch (cause) {
      if (cause instanceof PracticeDesignRequestError && cause.status === 409) setConflict(true);
      setError(errorMessage(cause, "Learning goals could not be saved."));
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="lecture-panel" aria-label={t("coursePage.action.review_goals")}>
      {error ? <p role="alert">{error}</p> : null}
      {!design || !draft ? (
        error ? null : (
          <p role="status">{t("coursePage.goals.loading")}</p>
        )
      ) : (
        <>
          {previousGoals ? (
            <GoalDiffList entries={diffGoals(previousGoals, draft.learning_intent.goals)} />
          ) : null}
          <ProfessorLearningIntent
            key={design.revision}
            design={design}
            draft={draft}
            label={t("coursePage.goals.label", { number: lecture.number, title: lecture.title })}
            pending={pending}
            stale={false}
            conflict={conflict}
            onChange={setDraft}
            onSave={() =>
              void run(() =>
                updatePracticeDesign({ courseId, lectureId, session, update: updateFor(draft) }),
              )
            }
            onApprove={(intent: LearningIntentApprovalOptions) =>
              void run(
                () => approvePracticeDesign({ courseId, lectureId, design, intent, session }),
                onApproved,
              )
            }
            onRefresh={() =>
              void run(() => proposePracticeDesign({ courseId, lectureId, refresh: true, session }))
            }
            onUseLatest={() => void run(() => getPracticeDesign({ courseId, lectureId, session }))}
          />
        </>
      )}
    </section>
  );
}
