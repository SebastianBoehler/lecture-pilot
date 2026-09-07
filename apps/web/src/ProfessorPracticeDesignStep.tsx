import { PracticeDesignLectureNavigation } from "./PracticeDesignLectureNavigation";
import type { PendingEntry } from "./practiceDesignOperations";
import "./practice-design-workspace.css";
import type { LearningIntentApprovalOptions } from "./learningIntentTypes";
import { ProfessorLearningIntent } from "./ProfessorLearningIntent";
import { useEffect, useMemo, useRef, useState } from "react";

import { useI18n } from "./i18n";
import { ProfessorPracticeLecturePlan } from "./ProfessorPracticeLecturePlan";
import { isApproved, updateFor } from "./ProfessorPracticeDesignStep.helpers";
import type {
  PracticeDesign,
  PracticeDesignReadiness,
  PracticeDesignUpdate,
} from "./practiceDesignTypes";
import type { PracticeDesignPendingAction } from "./useProfessorPracticeDesigns";
import { usePracticeDesignDrafts } from "./usePracticeDesignDrafts";

type Lecture = { id: string; label: string };

export function ProfessorPracticeDesignStep({
  designs,
  readiness = {},
  error,
  lectures,
  pendingAction,
  pendingByLecture = {},
  preparing = false,
  errorsByLecture = {},
  pendingLectureId,
  routingReady,
  onApprove,
  onPropose,
  onReview,
  onReload,
  onSave,
}: {
  designs: Readonly<Record<string, PracticeDesign>>;
  readiness?: Readonly<Record<string, PracticeDesignReadiness>>;
  error: string | null;
  lectures: Lecture[];
  pendingAction: PracticeDesignPendingAction | null;
  pendingByLecture?: Readonly<Record<string, PendingEntry>>;
  preparing?: boolean;
  errorsByLecture?: Readonly<Record<string, string>>;
  pendingLectureId: string | null;
  routingReady: boolean;
  onApprove: (lectureId: string, options?: LearningIntentApprovalOptions) => void;
  onPropose: (lectureId: string, refresh?: boolean) => void;
  onReview: (lectureId: string) => void;
  onReload?: (lectureId: string) => void;
  onSave: (lectureId: string, update: PracticeDesignUpdate) => void;
}) {
  const { t } = useI18n();
  const [converting, setConverting] = useState<Readonly<Record<string, boolean>>>({});
  const [selectedId, setSelectedId] = useState(lectures[0]?.id ?? "");
  const selected = lectures.some(({ id }) => id === selectedId) ? selectedId : lectures[0]?.id;
  const approving = useRef<string | null>(null);
  useEffect(() => {
    const id = approving.current;
    if (!id || !designs[id] || !isApproved(designs[id])) return;
    approving.current = null;
    if (selected !== id) return;
    const next = lectures.find(
      (lecture) => lecture.id !== id && (!designs[lecture.id] || !isApproved(designs[lecture.id])),
    );
    if (next) setSelectedId(next.id);
  }, [designs, lectures, selected]);
  const approve = (id: string, options?: LearningIntentApprovalOptions) => {
    approving.current = designs[id]?.learning_intent ? id : null;
    onApprove(id, options);
  };
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
      {selected && designs[selected] && errorsByLecture[selected] && onReload ? (
        <button
          type="button"
          disabled={Boolean(pendingByLecture[selected])}
          onClick={() => onReload(selected)}
        >
          {t("builder.plan.reload")}
        </button>
      ) : null}
      {preparing ? (
        <p className="plan-preparing" role="status">
          {t("builder.plan.preparing")}
        </p>
      ) : null}
      <div className="practice-plan-workspace">
        <PracticeDesignLectureNavigation
          lectures={lectures}
          designs={designs}
          selectedId={selected}
          pendingByLecture={pendingByLecture}
          preparing={preparing}
          routingReady={routingReady}
          errorsByLecture={errorsByLecture}
          onSelect={setSelectedId}
        />
        <div className="practice-design-lectures" key={selected}>
          {lectures
            .filter((lecture) => lecture.id === selected)
            .map((lecture) => {
              const design = designs[lecture.id];
              const sourceChanged = Boolean(
                design &&
                readiness[lecture.id] &&
                readiness[lecture.id].current_source_revision !== design.source_revision,
              );
              const draft = draftState.drafts[lecture.id] ?? design;
              const pending =
                Boolean(pendingByLecture[lecture.id]) || pendingLectureId === lecture.id;
              const action =
                pendingByLecture[lecture.id]?.action ?? (pending ? pendingAction : null);
              if (!design || !draft)
                return (
                  <article className="practice-design-empty" key={lecture.id}>
                    <div>
                      <strong>{lecture.label}</strong>
                      <p>{t("builder.intent.empty")}</p>
                    </div>
                    <button
                      className="primary-action"
                      disabled={
                        pending || (preparing && !errorsByLecture[lecture.id]) || !routingReady
                      }
                      type="button"
                      onClick={() => onPropose(lecture.id, false)}
                    >
                      {(action === "propose" || action === "load") && pending
                        ? t("builder.intent.generating")
                        : preparing && !errorsByLecture[lecture.id]
                          ? t("builder.plan.queued")
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
                    stale={!routingReady || sourceChanged}
                    onRegenerate={
                      sourceChanged && routingReady ? () => onPropose(lecture.id, false) : undefined
                    }
                    conflict={draftState.conflicts[lecture.id] ?? false}
                    onChange={(next) => draftState.change(lecture.id, next)}
                    onApprove={(options) => approve(lecture.id, options)}
                    onSave={() => onSave(lecture.id, updateFor(draft))}
                    onRefresh={() => onPropose(lecture.id, true)}
                    onUseLatest={() => draftState.useLatest(lecture.id)}
                  />
                );
              return (
                <div key={lecture.id}>
                  <button
                    type="button"
                    disabled={
                      pending || (preparing && !errorsByLecture[lecture.id]) || !routingReady
                    }
                    onClick={() => setConverting({ ...converting, [lecture.id]: true })}
                  >
                    {t("builder.intent.convert")}
                  </button>
                  <ProfessorPracticeLecturePlan
                    conflict={draftState.conflicts[lecture.id] ?? false}
                    defaultOpen
                    design={design}
                    draft={draft}
                    key={lecture.id}
                    label={lecture.label}
                    pending={pending}
                    pendingAction={action}
                    stale={!routingReady}
                    onApprove={() => approve(lecture.id)}
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
      </div>
    </section>
  );
}
