import { useEffect, useMemo, useState } from "react";

import { useI18n } from "./i18n";
import { ProfessorPracticeTargetEditor } from "./ProfessorPracticeTargetEditor";
import type { PracticeDesign, PracticeDesignUpdate, PracticeTarget } from "./practiceDesignTypes";

type Lecture = { id: string; label: string };

export function ProfessorPracticeDesignStep({
  designs,
  error,
  lectures,
  pendingLectureId,
  onApprove,
  onPropose,
  onSave,
}: {
  designs: Readonly<Record<string, PracticeDesign>>;
  error: string | null;
  lectures: Lecture[];
  pendingLectureId: string | null;
  onApprove: (lectureId: string) => void;
  onPropose: (lectureId: string, refresh?: boolean) => void;
  onSave: (lectureId: string, update: PracticeDesignUpdate) => void;
}) {
  const { t } = useI18n();
  const designKey = useMemo(
    () => lectures.map(({ id }) => `${id}:${designs[id]?.revision ?? ""}`).join("|"),
    [designs, lectures],
  );
  const [drafts, setDrafts] = useState<Readonly<Record<string, PracticeDesign>>>({});
  useEffect(
    () =>
      setDrafts(
        Object.fromEntries(lectures.flatMap(({ id }) => (designs[id] ? [[id, designs[id]]] : []))),
      ),
    [designKey, designs, lectures],
  );
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
      <p className="practice-design-boundary">{t("builder.design.boundary")}</p>
      <div className="practice-design-lectures">
        {lectures.map((lecture) => {
          const design = designs[lecture.id];
          const draft = drafts[lecture.id] ?? design;
          const pending = pendingLectureId === lecture.id;
          if (!design || !draft)
            return (
              <article className="practice-design-lecture" key={lecture.id}>
                <header>
                  <strong>{lecture.label}</strong>
                  <span>{t("builder.status.pending")}</span>
                </header>
                <button
                  className="primary-action"
                  disabled={pending}
                  type="button"
                  onClick={() => onPropose(lecture.id, false)}
                >
                  {pending ? t("builder.design.generating") : t("builder.design.generate")}
                </button>
              </article>
            );
          const dirty = !sameEditableDesign(draft, design);
          const approved = isApproved(design);
          return (
            <article className="practice-design-lecture" key={lecture.id}>
              <header>
                <div>
                  <strong>{lecture.label}</strong>
                  <p>{draft.objective}</p>
                </div>
                <span className={approved && !dirty ? "is-approved" : ""} aria-live="polite">
                  {approved && !dirty
                    ? t("builder.design.approved")
                    : dirty
                      ? t("builder.design.unsaved")
                      : t("builder.status.pending")}
                </span>
              </header>
              <label className="practice-design-objective">
                {t("builder.design.objective")}
                <textarea
                  value={draft.objective}
                  onChange={(event) =>
                    setDrafts((current) => ({
                      ...current,
                      [lecture.id]: { ...draft, objective: event.target.value },
                    }))
                  }
                />
              </label>
              <div className="practice-target-summary" role="list">
                {draft.targets.map((target) => (
                  <TargetSummary
                    key={target.id}
                    target={target}
                    onChange={(next) =>
                      setDrafts((current) => ({
                        ...current,
                        [lecture.id]: {
                          ...draft,
                          targets: draft.targets.map((item) => (item.id === next.id ? next : item)),
                        },
                      }))
                    }
                  />
                ))}
              </div>
              <div className="flow-actions">
                <button
                  disabled={pending || !dirty}
                  type="button"
                  onClick={() => onSave(lecture.id, updateFor(draft))}
                >
                  {pending ? t("builder.design.saving") : t("builder.design.save")}
                </button>
                {approved && !dirty ? null : (
                  <button
                    className="primary-action"
                    disabled={pending || dirty}
                    type="button"
                    onClick={() => onApprove(lecture.id)}
                  >
                    {pending ? t("builder.design.approving") : t("builder.design.approve")}
                  </button>
                )}
                <button
                  disabled={pending}
                  type="button"
                  onClick={() => onPropose(lecture.id, true)}
                >
                  {t("builder.design.refresh")}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function TargetSummary({
  target,
  onChange,
}: {
  target: PracticeTarget;
  onChange: (target: PracticeTarget) => void;
}) {
  const { t } = useI18n();
  return (
    <section className="practice-target" role="listitem">
      <div>
        <strong>{target.title}</strong>
        <p>{target.outcome}</p>
      </div>
      <dl>
        <div>
          <dt>{t("builder.design.baseline")}</dt>
          <dd>{target.baseline_task}</dd>
        </div>
        <div>
          <dt>{t("builder.design.exit")}</dt>
          <dd>{target.independent_exit_task}</dd>
        </div>
        <div>
          <dt>{t("builder.design.transfer")}</dt>
          <dd>{target.delayed_transfer_task}</dd>
        </div>
      </dl>
      <ProfessorPracticeTargetEditor target={target} onChange={onChange} />
    </section>
  );
}

function updateFor(design: PracticeDesign): PracticeDesignUpdate {
  return {
    lecture_title: design.lecture_title,
    objective: design.objective,
    practice_design_revision: design.revision,
    source_revision: design.source_revision,
    targets: design.targets,
  };
}
function isApproved(design: PracticeDesign) {
  return Boolean(
    design.approval &&
    design.approval.source_revision === design.source_revision &&
    design.approval.practice_design_revision === design.revision,
  );
}
function sameEditableDesign(left: PracticeDesign, right: PracticeDesign) {
  return JSON.stringify(updateFor(left)) === JSON.stringify(updateFor(right));
}
