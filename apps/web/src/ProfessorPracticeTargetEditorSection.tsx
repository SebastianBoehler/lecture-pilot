import { useI18n } from "./i18n";
import { ProfessorPracticeEvidence } from "./ProfessorPracticeEvidence";
import { NumberField, TextField } from "./ProfessorPracticeEditorFields";
import { ProfessorPracticeHintEditor } from "./ProfessorPracticeHintEditor";
import type { PracticeEditorSection } from "./ProfessorPracticeTargetEditor";
import type { PracticeTarget } from "./practiceDesignTypes";

export function ProfessorPracticeTargetEditorSection({
  disabled,
  section,
  target,
  onChange,
}: {
  disabled: boolean;
  section: PracticeEditorSection;
  target: PracticeTarget;
  onChange: (target: PracticeTarget) => void;
}) {
  const { t } = useI18n();
  if (section === "outcome")
    return (
      <fieldset className="practice-editor-fields">
        <legend>{t("builder.design.editSections.outcome")}</legend>
        <TextField
          disabled={disabled}
          help={t("builder.design.targetTitleHelp")}
          label={t("builder.design.targetTitle")}
          value={target.title}
          onChange={(title) => onChange({ ...target, title })}
        />
        <TextField
          disabled={disabled}
          help={t("builder.design.outcomeHelp")}
          label={t("builder.design.outcomeFor", { target: target.title })}
          value={target.outcome}
          onChange={(outcome) => onChange({ ...target, outcome })}
        />
        <ProfessorPracticeEvidence anchor={target.outcome_anchor} />
      </fieldset>
    );
  if (section === "invariant")
    return (
      <fieldset className="practice-editor-fields">
        <legend>{t("builder.design.invariant")}</legend>
        <TextField
          disabled={disabled}
          help={t("builder.design.invariantHelp")}
          label={t("builder.design.invariant")}
          value={target.target_invariant}
          onChange={(target_invariant) => onChange({ ...target, target_invariant })}
        />
        <ProfessorPracticeEvidence anchor={target.target_invariant_anchor} />
      </fieldset>
    );
  if (section === "sequence")
    return (
      <fieldset className="practice-editor-fields">
        <legend>{t("builder.design.editSections.sequence")}</legend>
        <TextField
          disabled={disabled}
          help={t("builder.design.baselineEditHelp")}
          label={t("builder.design.baseline")}
          value={target.baseline_task}
          onChange={(baseline_task) => onChange({ ...target, baseline_task })}
        />
        <ProfessorPracticeEvidence anchor={target.baseline_task_anchor} />
        <TextField
          disabled={disabled}
          help={t("builder.design.exitEditHelp")}
          label={t("builder.design.exit")}
          value={target.independent_exit_task}
          onChange={(independent_exit_task) => onChange({ ...target, independent_exit_task })}
        />
        <TextField
          disabled={disabled}
          help={t("builder.design.exitSurfaceHelp")}
          label={t("builder.design.exitSurface")}
          value={target.independent_exit_surface_change}
          onChange={(independent_exit_surface_change) =>
            onChange({ ...target, independent_exit_surface_change })
          }
        />
        <ProfessorPracticeEvidence anchor={target.independent_exit_task_anchor} />
        <TextField
          disabled={disabled}
          help={t("builder.design.transferEditHelp")}
          label={t("builder.design.transfer")}
          value={target.delayed_transfer_task}
          onChange={(delayed_transfer_task) => onChange({ ...target, delayed_transfer_task })}
        />
        <TextField
          disabled={disabled}
          help={t("builder.design.transferSurfaceHelp")}
          label={t("builder.design.transferSurface")}
          value={target.delayed_transfer_surface_change}
          onChange={(delayed_transfer_surface_change) =>
            onChange({ ...target, delayed_transfer_surface_change })
          }
        />
        <ProfessorPracticeEvidence anchor={target.delayed_transfer_task_anchor} />
      </fieldset>
    );
  if (section === "evidence")
    return (
      <fieldset className="practice-editor-fields">
        <legend>{t("builder.design.evidence")}</legend>
        <p>{t("builder.design.evidenceHelp")}</p>
        {target.evidence_criteria.map((criterion) => (
          <div className="practice-contract-item" key={criterion.id}>
            <code>{criterion.id}</code>
            <TextField
              disabled={disabled}
              label={t("builder.design.criterionDescription", { id: criterion.id })}
              value={criterion.description}
              onChange={(description) =>
                onChange({
                  ...target,
                  evidence_criteria: target.evidence_criteria.map((item) =>
                    item.id === criterion.id ? { ...item, description } : item,
                  ),
                })
              }
            />
            <label className="practice-checkbox-field">
              <input
                checked={criterion.required}
                disabled={disabled}
                type="checkbox"
                onChange={(event) =>
                  onChange({
                    ...target,
                    evidence_criteria: target.evidence_criteria.map((item) =>
                      item.id === criterion.id ? { ...item, required: event.target.checked } : item,
                    ),
                  })
                }
              />
              {t("builder.design.criterionRequired", { id: criterion.id })}
            </label>
            <ProfessorPracticeEvidence anchor={criterion.source_anchor} />
          </div>
        ))}
      </fieldset>
    );
  if (section === "misconceptions")
    return (
      <fieldset className="practice-editor-fields">
        <legend>{t("builder.design.misconceptions")}</legend>
        <p>{t("builder.design.misconceptionsHelp")}</p>
        {target.misconceptions.map((misconception) => (
          <div className="practice-contract-item" key={misconception.id}>
            <code>{misconception.id}</code>
            <TextField
              disabled={disabled}
              label={t("builder.design.misconceptionDescription", { id: misconception.id })}
              value={misconception.description}
              onChange={(description) =>
                onChange({
                  ...target,
                  misconceptions: target.misconceptions.map((item) =>
                    item.id === misconception.id ? { ...item, description } : item,
                  ),
                })
              }
            />
            <ProfessorPracticeEvidence anchor={misconception.source_anchor} />
            <TextField
              disabled={disabled}
              label={t("builder.design.diagnosticCue", { id: misconception.id })}
              value={misconception.diagnostic_cue}
              onChange={(diagnostic_cue) =>
                onChange({
                  ...target,
                  misconceptions: target.misconceptions.map((item) =>
                    item.id === misconception.id ? { ...item, diagnostic_cue } : item,
                  ),
                })
              }
            />
          </div>
        ))}
      </fieldset>
    );
  if (section === "hints")
    return <ProfessorPracticeHintEditor disabled={disabled} target={target} onChange={onChange} />;
  return (
    <fieldset className="practice-editor-fields">
      <legend>{t("builder.design.editSections.sources")}</legend>
      <NumberField
        disabled={disabled}
        help={t("builder.design.reviewAfterDaysHelp")}
        label={t("builder.design.reviewAfterDays")}
        value={target.review_after_days}
        onChange={(review_after_days) => onChange({ ...target, review_after_days })}
      />
      <p>{t("builder.design.sourcesReadOnly", { sources: target.source_refs.join(", ") })}</p>
    </fieldset>
  );
}
