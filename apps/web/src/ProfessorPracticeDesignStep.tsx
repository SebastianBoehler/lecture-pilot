import { useEffect, useId, useMemo, useState } from "react";

import { useI18n } from "./i18n";
import { isApproved, sameEditableDesign, updateFor } from "./ProfessorPracticeDesignStep.helpers";
import { ProfessorPracticeTargetReview } from "./ProfessorPracticeTargetReview";
import type { PracticeDesign, PracticeDesignUpdate } from "./practiceDesignTypes";

type Lecture = { id: string; label: string };

export function ProfessorPracticeDesignStep({
  designs,
  error,
  lectures,
  pendingLectureId,
  routingReady,
  onApprove,
  onPropose,
  onSave,
}: {
  designs: Readonly<Record<string, PracticeDesign>>;
  error: string | null;
  lectures: Lecture[];
  pendingLectureId: string | null;
  routingReady: boolean;
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
      {!routingReady ? (
        <p className="form-error" role="alert">
          {t("builder.design.staleAction")}
        </p>
      ) : null}
      <p className="practice-design-boundary">{t("builder.design.boundary")}</p>
      <div className="practice-design-lectures">
        {lectures.map((lecture, lectureIndex) => {
          const design = designs[lecture.id];
          const draft = drafts[lecture.id] ?? design;
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
                  {pending ? t("builder.design.generating") : t("builder.design.generate")}
                </button>
              </article>
            );
          return (
            <LecturePlan
              defaultOpen={lectures.length === 1 || lectureIndex === 0}
              design={design}
              draft={draft}
              key={lecture.id}
              label={lecture.label}
              pending={pending}
              stale={!routingReady}
              onApprove={() => onApprove(lecture.id)}
              onChange={(next) => setDrafts((current) => ({ ...current, [lecture.id]: next }))}
              onRefresh={() => onPropose(lecture.id, true)}
              onSave={() => onSave(lecture.id, updateFor(draft))}
            />
          );
        })}
      </div>
    </section>
  );
}

function LecturePlan({
  defaultOpen,
  design,
  draft,
  label,
  pending,
  stale,
  onApprove,
  onChange,
  onRefresh,
  onSave,
}: {
  defaultOpen: boolean;
  design: PracticeDesign;
  draft: PracticeDesign;
  label: string;
  pending: boolean;
  stale: boolean;
  onApprove: () => void;
  onChange: (design: PracticeDesign) => void;
  onRefresh: () => void;
  onSave: () => void;
}) {
  const { t } = useI18n();
  const dirty = !sameEditableDesign(draft, design);
  const approved = !stale && isApproved(design);
  const [expanded, setExpanded] = useState(defaultOpen);
  const regionId = useId();
  return (
    <article className="practice-design-lecture">
      <header className="practice-design-lecture-toggle">
        <button
          aria-controls={regionId}
          aria-expanded={expanded}
          type="button"
          onClick={() => setExpanded(!expanded)}
        >
          <span className="practice-plan-action">{t("builder.design.reviewPlan")}</span>
          <span>
            <strong>{label}</strong>
            <span>{draft.objective}</span>
          </span>
        </button>
        <PlanStatus approved={approved && !dirty} dirty={dirty} stale={stale} />
      </header>
      {expanded ? (
        <div className="practice-design-lecture-body" id={regionId}>
          <header className="practice-design-proposal-heading">
            <div>
              <h3>{draft.lecture_title}</h3>
              <p>{draft.objective}</p>
            </div>
            {!stale ? <LectureDetailsEditor draft={draft} onChange={onChange} /> : null}
          </header>
          <div className="practice-target-summary" role="list">
            {draft.targets.map((target, index) => (
              <ProfessorPracticeTargetReview
                disabled={stale}
                index={index}
                key={target.id}
                target={target}
                onChange={(next) =>
                  onChange({
                    ...draft,
                    targets: draft.targets.map((item) => (item.id === next.id ? next : item)),
                  })
                }
              />
            ))}
          </div>
          <footer className="practice-design-actions">
            <p aria-live="polite">
              {dirty ? t("builder.design.saveBeforeApprove") : t("builder.design.approvalHelp")}
            </p>
            <div className="flow-actions">
              {dirty ? (
                <button
                  className="primary-action"
                  disabled={pending || stale}
                  type="button"
                  onClick={onSave}
                >
                  {pending ? t("builder.design.saving") : t("builder.design.save")}
                </button>
              ) : null}
              {approved && !dirty ? null : (
                <button
                  className="primary-action"
                  disabled={pending || stale || dirty}
                  type="button"
                  onClick={onApprove}
                >
                  {pending ? t("builder.design.approving") : t("builder.design.approve")}
                </button>
              )}
              <button disabled={pending || stale} type="button" onClick={onRefresh}>
                {t("builder.design.refresh")}
              </button>
            </div>
          </footer>
        </div>
      ) : null}
    </article>
  );
}

function LectureDetailsEditor({
  draft,
  onChange,
}: {
  draft: PracticeDesign;
  onChange: (design: PracticeDesign) => void;
}) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const regionId = useId();
  return (
    <div className="practice-lecture-editor">
      <button
        aria-controls={regionId}
        aria-expanded={open}
        type="button"
        onClick={() => setOpen(!open)}
      >
        {open ? t("builder.design.finishEditing") : t("builder.design.editLecture")}
      </button>
      {open ? (
        <div className="practice-lecture-fields" id={regionId}>
          <label>
            {t("builder.design.lectureTitle")}
            <span>{t("builder.design.lectureTitleHelp")}</span>
            <textarea
              value={draft.lecture_title}
              onChange={(event) => onChange({ ...draft, lecture_title: event.target.value })}
            />
          </label>
          <label>
            {t("builder.design.objective")}
            <span>{t("builder.design.objectiveHelp")}</span>
            <textarea
              value={draft.objective}
              onChange={(event) => onChange({ ...draft, objective: event.target.value })}
            />
          </label>
        </div>
      ) : null}
    </div>
  );
}

function PlanStatus({
  approved,
  dirty,
  stale,
}: {
  approved: boolean;
  dirty: boolean;
  stale: boolean;
}) {
  const { t } = useI18n();
  const key = stale
    ? "builder.design.stale"
    : approved
      ? "builder.design.approved"
      : dirty
        ? "builder.design.unsaved"
        : "builder.status.pending";
  return (
    <span className={`practice-design-status ${approved ? "is-approved" : ""}`} aria-live="polite">
      <span aria-hidden="true">{approved ? "✓" : stale ? "!" : "•"}</span>
      <span>{t(key)}</span>
    </span>
  );
}
