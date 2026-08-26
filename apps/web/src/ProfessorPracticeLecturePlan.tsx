import { useId, useState } from "react";

import { useI18n } from "./i18n";
import { ProfessorPracticeDesignQuality } from "./ProfessorPracticeDesignQuality";
import {
  currentQualityReview,
  hasCriticalQualityFinding,
  isApproved,
  sameEditableDesign,
} from "./ProfessorPracticeDesignStep.helpers";
import {
  ProfessorPracticeLectureEditor,
  ProfessorPracticePlanStatus,
} from "./ProfessorPracticeLectureEditor";
import { ProfessorPracticePlanningContext } from "./ProfessorPracticePlanningContext";
import { ProfessorPracticeTargetReview } from "./ProfessorPracticeTargetReview";
import type { PracticeDesign } from "./practiceDesignTypes";
import type { PracticeDesignPendingAction } from "./useProfessorPracticeDesigns";

type Translator = ReturnType<typeof useI18n>["t"];

export function ProfessorPracticeLecturePlan({
  conflict,
  defaultOpen,
  design,
  draft,
  label,
  pending,
  pendingAction,
  stale,
  onApprove,
  onChange,
  onRefresh,
  onReview,
  onSave,
  onUseLatest,
}: {
  conflict: boolean;
  defaultOpen: boolean;
  design: PracticeDesign;
  draft: PracticeDesign;
  label: string;
  pending: boolean;
  pendingAction: PracticeDesignPendingAction | null;
  stale: boolean;
  onApprove: () => void;
  onChange: (design: PracticeDesign) => void;
  onRefresh: () => void;
  onReview: () => void;
  onSave: () => void;
  onUseLatest: () => void;
}) {
  const { t } = useI18n();
  const dirty = !sameEditableDesign(draft, design);
  const approved = !stale && isApproved(design);
  const qualityReview = currentQualityReview(design);
  const critical = !dirty && hasCriticalQualityFinding(design);
  const reviewMissing = dirty || qualityReview === null;
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
        <ProfessorPracticePlanStatus
          approved={approved && !dirty}
          critical={critical}
          dirty={dirty}
          reviewMissing={reviewMissing}
          stale={stale}
        />
      </header>
      {expanded ? (
        <div className="practice-design-lecture-body" id={regionId}>
          {conflict ? (
            <div className="practice-design-conflict" role="status">
              <p>{t("builder.design.revisionConflict")}</p>
              <button type="button" onClick={onUseLatest}>
                {t("builder.design.useLatest")}
              </button>
            </div>
          ) : null}
          <header className="practice-design-proposal-heading">
            <div>
              <h3>{draft.lecture_title}</h3>
              <p>{draft.objective}</p>
            </div>
            {!stale ? <ProfessorPracticeLectureEditor draft={draft} onChange={onChange} /> : null}
          </header>
          <ProfessorPracticePlanningContext context={draft.planning_context} />
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
          <ProfessorPracticeDesignQuality dirty={dirty} qualityReview={qualityReview} />
          <footer className="practice-design-actions">
            <p aria-live="polite" id={`${regionId}-approval-status`}>
              {approvalMessage({ critical, dirty, pendingAction, reviewMissing, stale, t })}
            </p>
            <div className="flow-actions">
              {dirty ? (
                <button
                  className="primary-action"
                  disabled={conflict || pending || stale}
                  type="button"
                  onClick={onSave}
                >
                  {pendingAction === "save" ? t("builder.design.saving") : t("builder.design.save")}
                </button>
              ) : null}
              {!dirty && reviewMissing ? (
                <button
                  className="primary-action"
                  disabled={pending || stale}
                  type="button"
                  onClick={onReview}
                >
                  {pendingAction === "review"
                    ? t("builder.design.reviewing")
                    : t("builder.design.reviewEdited")}
                </button>
              ) : null}
              {approved && !dirty ? null : (
                <button
                  aria-describedby={`${regionId}-approval-status`}
                  className="primary-action"
                  disabled={pending || stale || dirty || reviewMissing || critical}
                  type="button"
                  onClick={onApprove}
                >
                  {pendingAction === "approve"
                    ? t("builder.design.approving")
                    : t("builder.design.approve")}
                </button>
              )}
              <button disabled={pending || stale} type="button" onClick={onRefresh}>
                {pendingAction === "refresh"
                  ? t("builder.design.refreshing")
                  : t("builder.design.refresh")}
              </button>
            </div>
          </footer>
        </div>
      ) : null}
    </article>
  );
}

function approvalMessage({
  critical,
  dirty,
  pendingAction,
  reviewMissing,
  stale,
  t,
}: {
  critical: boolean;
  dirty: boolean;
  pendingAction: PracticeDesignPendingAction | null;
  reviewMissing: boolean;
  stale: boolean;
  t: Translator;
}) {
  if (stale) return t("builder.design.staleAction");
  if (pendingAction === "save") return t("builder.design.saving");
  if (pendingAction === "review") return t("builder.design.reviewing");
  if (pendingAction === "approve") return t("builder.design.approving");
  if (pendingAction === "refresh") return t("builder.design.refreshing");
  if (pendingAction === "propose") return t("builder.design.generating");
  if (dirty) return t("builder.design.saveBeforeApprove");
  if (reviewMissing) return t("builder.design.reviewBeforeApprove");
  if (critical) return t("builder.design.criticalBeforeApprove");
  return t("builder.design.approvalHelp");
}
