import { useState } from "react";

import { useI18n } from "./i18n";
import type { LearningIntentApprovalOptions } from "./learningIntentTypes";
import type { PracticeDesign } from "./practiceDesignTypes";
import { isApproved, sameEditableDesign } from "./ProfessorPracticeDesignStep.helpers";
import { ProfessorPracticeEvidence } from "./ProfessorPracticeEvidence";
import { ProfessorPracticeLectureEditor } from "./ProfessorPracticeLectureEditor";
import { ProfessorPracticePlanningContext } from "./ProfessorPracticePlanningContext";
import { ProfessorPracticeTargetReview } from "./ProfessorPracticeTargetReview";

export function ProfessorLearningIntent({
  design,
  draft,
  label,
  pending,
  stale,
  conflict,
  onChange,
  onApprove,
  onSave,
  onRefresh,
  onUseLatest,
}: {
  design: PracticeDesign;
  draft: PracticeDesign;
  label: string;
  pending: boolean;
  stale: boolean;
  conflict: boolean;
  onChange: (design: PracticeDesign) => void;
  onApprove: (options: LearningIntentApprovalOptions) => void;
  onSave: () => void;
  onRefresh: () => void;
  onUseLatest: () => void;
}) {
  const { t } = useI18n();
  const [editing, setEditing] = useState(false);
  const [conversionConfirmed, setConversionConfirmed] = useState(false);
  const initialFixed = design.learning_intent?.fixed_targets.map(({ id }) => id) ?? [];
  const [fixed, setFixed] = useState<readonly string[]>(initialFixed);
  const fixedChanged =
    JSON.stringify([...fixed].sort()) !== JSON.stringify([...initialFixed].sort());
  const dirty = !sameEditableDesign(design, draft);
  const legacy = Boolean(design.approval);
  const approved = isApproved(design) && !legacy && !dirty && !fixedChanged && !stale;
  const disabled = pending || stale || conflict;
  const goals = draft.learning_intent?.goals ?? draft.targets;
  return (
    <article className="practice-design-lecture">
      <header className="practice-design-proposal-heading">
        <div>
          <h3>{label}</h3>
          <p>{draft.objective}</p>
        </div>
        <span role="status">
          {approved ? t("builder.intent.approved") : t("builder.status.pending")}
        </span>
      </header>
      <div className="practice-design-lecture-body">
        {legacy ? (
          <div className="practice-design-conflict">
            <p>{t("builder.intent.conversion")}</p>
            <label>
              <input
                type="checkbox"
                checked={conversionConfirmed}
                onChange={(event) => setConversionConfirmed(event.target.checked)}
              />
              {t("builder.intent.confirmConversion")}
            </label>
          </div>
        ) : null}
        {conflict ? (
          <div role="alert">
            <p>{t("builder.design.revisionConflict")}</p>
            <button type="button" onClick={onUseLatest}>
              {t("builder.design.useLatest")}
            </button>
          </div>
        ) : null}
        <button type="button" disabled={disabled || legacy} onClick={() => setEditing(!editing)}>
          {editing ? t("builder.design.finishEditing") : t("builder.intent.edit")}
        </button>
        {editing ? <ProfessorPracticeLectureEditor draft={draft} onChange={onChange} /> : null}
        <ProfessorPracticePlanningContext context={draft.planning_context} />
        <ol className="practice-target-summary">
          {goals.map((target, index) => {
            const implementation = draft.targets.find(({ id }) => id === target.id);
            return (
              <li key={target.id} className="practice-target">
                <strong>{target.title}</strong>
                {editing ? (
                  <label>
                    {t("builder.design.outcomeFor", { target: target.title })}
                    <textarea
                      value={target.outcome}
                      disabled={disabled}
                      onChange={(event) =>
                        onChange({
                          ...draft,
                          ...(draft.learning_intent
                            ? {
                                learning_intent: {
                                  ...draft.learning_intent,
                                  goals: goals.map((item) =>
                                    item.id === target.id
                                      ? { ...item, outcome: event.target.value }
                                      : item,
                                  ),
                                },
                              }
                            : {
                                targets: draft.targets.map((item) =>
                                  item.id === target.id
                                    ? { ...item, outcome: event.target.value }
                                    : item,
                                ),
                              }),
                        })
                      }
                    />
                  </label>
                ) : (
                  <p>{target.outcome}</p>
                )}
                <ProfessorPracticeEvidence anchor={target.outcome_anchor} />
                <p>{target.target_invariant}</p>
                {implementation ? (
                  <details>
                    <summary>{t("builder.intent.details")}</summary>
                    <ProfessorPracticeTargetReview
                      disabled
                      index={index}
                      target={implementation}
                      onChange={() => {}}
                    />
                    <label>
                      <input
                        type="checkbox"
                        disabled={disabled}
                        checked={fixed.includes(target.id)}
                        onChange={(event) =>
                          setFixed(
                            event.target.checked
                              ? [...fixed, target.id]
                              : fixed.filter((id) => id !== target.id),
                          )
                        }
                      />
                      {t("builder.intent.fixed")}
                    </label>
                  </details>
                ) : null}
              </li>
            );
          })}
        </ol>
        {draft.targets.length > 0 ? <p>{t("builder.intent.fixedHelp")}</p> : null}
        <p>{t("builder.intent.repair")}</p>
        <footer className="flow-actions">
          {dirty ? (
            <button type="button" className="primary-action" disabled={disabled} onClick={onSave}>
              {t("builder.design.save")}
            </button>
          ) : null}
          {!approved ? (
            <button
              type="button"
              className="primary-action"
              disabled={disabled || dirty || (legacy && !conversionConfirmed)}
              onClick={() => onApprove({ fixed_target_ids: fixed, convert_legacy: legacy })}
            >
              {t("builder.intent.approve")}
            </button>
          ) : null}
          {!legacy && approved && draft.targets.length > 0 ? (
            <button type="button" disabled={disabled || dirty} onClick={onRefresh}>
              {t("builder.intent.refresh")}
            </button>
          ) : null}
        </footer>
      </div>
    </article>
  );
}
