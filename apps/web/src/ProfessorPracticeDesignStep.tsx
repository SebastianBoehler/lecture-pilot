import { useMemo } from "react";

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
  onApprove: (lectureId: string) => void;
  onPropose: (lectureId: string, refresh?: boolean) => void;
  onReview: (lectureId: string) => void;
  onSave: (lectureId: string, update: PracticeDesignUpdate) => void;
}) {
  const { t } = useI18n();
  const lectureIds = useMemo(() => lectures.map(({ id }) => id), [lectures]);
  const draftState = usePracticeDesignDrafts({
    designs,
    lectureIds,
  });
  return (
    <section className="flow-card practice-design-step">
      <header className="practice-design-header">
        <div>
          <h2>{t("builder.design.title")}</h2>
          <p>{t("builder.design.help")}</p>
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
      <p className="practice-design-boundary">{t("builder.design.boundary")}</p>
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
                  <p>{t("builder.design.emptyHelp")}</p>
                </div>
                <button
                  className="primary-action"
                  disabled={pending || !routingReady}
                  type="button"
                  onClick={() => onPropose(lecture.id, false)}
                >
                  {pendingAction === "propose" && pending
                    ? t("builder.design.generating")
                    : t("builder.design.generate")}
                </button>
              </article>
            );
          return (
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
          );
        })}
      </div>
    </section>
  );
}
