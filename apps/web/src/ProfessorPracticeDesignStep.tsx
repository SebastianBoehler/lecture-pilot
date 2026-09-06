import type { LearningIntentApprovalOptions } from "./learningIntentTypes";
import { ProfessorLearningIntent } from "./ProfessorLearningIntent";
import { useMemo, useState } from "react";

import { useI18n } from "./i18n";
import { ProfessorPracticeLecturePlan } from "./ProfessorPracticeLecturePlan";
import { updateFor } from "./ProfessorPracticeDesignStep.helpers";
import type { PracticeDesign, PracticeDesignUpdate } from "./practiceDesignTypes";
import type { PracticeDesignPendingAction } from "./useProfessorPracticeDesigns";
import { usePracticeDesignDrafts } from "./usePracticeDesignDrafts";

type Lecture = { id: string; label: string };

export function ProfessorPracticeDesignStep({
  designs,
  error,
  lectures,
  pendingAction,
  pendingLectureId,
  routingReady,
  onApprove,
  onPropose,
  onReview,
  onSave,
}: {
  designs: Readonly<Record<string, PracticeDesign>>;
  error: string | null;
  lectures: Lecture[];
  pendingAction: PracticeDesignPendingAction | null;
  pendingLectureId: string | null;
  routingReady: boolean;
  onApprove: (lectureId: string, options?: LearningIntentApprovalOptions) => void;
  onPropose: (lectureId: string, refresh?: boolean) => void;
  onReview: (lectureId: string) => void;
  onSave: (lectureId: string, update: PracticeDesignUpdate) => void;
}) {
  const { t } = useI18n();
  const [converting, setConverting] = useState<Readonly<Record<string, boolean>>>({});
  const lectureIds = useMemo(() => lectures.map(({ id }) => id), [lectures]);
  const draftState = usePracticeDesignDrafts({
    designs,
    lectureIds,
  });
  return (
    <section className="flow-card practice-design-step">
      <header className="practice-design-header">
        <div>
          <h2>{t("builder.intent.title")}</h2>
          <p>{t("builder.intent.help")}</p>
        </div>
        <span aria-live="polite">
          {t("builder.design.coverage", {
            designed: lectures.filter(({ id }) => designs[id]).length,
            total: lectures.length,
          })}
        </span>
      </header>
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      {!routingReady ? (
        <p className="form-error" role="alert">
          {t("builder.design.staleAction")}
        </p>
      ) : null}
      <div className="practice-design-lectures">
        {lectures.map((lecture, lectureIndex) => {
          const design = designs[lecture.id];
          const draft = draftState.drafts[lecture.id] ?? design;
          const pending = pendingLectureId === lecture.id;
          if (!design || !draft)
            return (
              <article className="practice-design-empty" key={lecture.id}>
                <div>
                  <strong>{lecture.label}</strong>
                  <p>{t("builder.intent.empty")}</p>
                </div>
                <button
                  className="primary-action"
                  disabled={pending || !routingReady}
                  type="button"
                  onClick={() => onPropose(lecture.id, false)}
                >
                  {pendingAction === "propose" && pending
                    ? t("builder.intent.generating")
                    : t("builder.intent.generate")}
                </button>
              </article>
            );
          if (design.learning_intent || converting[lecture.id])
            return (
              <ProfessorLearningIntent
                key={`${lecture.id}:${design.revision}`}
                design={design}
                draft={draft}
                label={lecture.label}
                pending={pending}
                stale={!routingReady}
                conflict={draftState.conflicts[lecture.id] ?? false}
                onChange={(next) => draftState.change(lecture.id, next)}
                onApprove={(options) => onApprove(lecture.id, options)}
                onSave={() => onSave(lecture.id, updateFor(draft))}
                onRefresh={() => onPropose(lecture.id, true)}
                onUseLatest={() => draftState.useLatest(lecture.id)}
              />
            );
          return (
            <div key={lecture.id}>
              <button
                type="button"
                disabled={pending || !routingReady}
                onClick={() => setConverting({ ...converting, [lecture.id]: true })}
              >
                {t("builder.intent.convert")}
              </button>
              <ProfessorPracticeLecturePlan
                conflict={draftState.conflicts[lecture.id] ?? false}
                defaultOpen={lectures.length === 1 || lectureIndex === 0}
                design={design}
                draft={draft}
                key={lecture.id}
                label={lecture.label}
                pending={pending}
                pendingAction={pending ? pendingAction : null}
                stale={!routingReady}
                onApprove={() => onApprove(lecture.id)}
                onChange={(next) => draftState.change(lecture.id, next)}
                onRefresh={() => onPropose(lecture.id, true)}
                onReview={() => onReview(lecture.id)}
                onSave={() => onSave(lecture.id, updateFor(draft))}
                onUseLatest={() => draftState.useLatest(lecture.id)}
              />
            </div>
          );
        })}
      </div>
    </section>
  );
}
