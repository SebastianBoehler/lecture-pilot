import { useI18n } from "./i18n";
import { NumberField, TextField } from "./ProfessorPracticeEditorFields";
import type { PracticeEditorSection } from "./ProfessorPracticeTargetEditor";
import type { PracticeHint, PracticeTarget } from "./practiceDesignTypes";

const HINT_LEVELS: readonly PracticeHint["level"][] = [
  "prompt",
  "cue",
  "faded_example",
  "worked_step",
];

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
        <TextField
          disabled={disabled}
          help={t("builder.design.exitEditHelp")}
          label={t("builder.design.exit")}
          value={target.independent_exit_task}
          onChange={(independent_exit_task) => onChange({ ...target, independent_exit_task })}
        />
        <TextField
          disabled={disabled}
          help={t("builder.design.transferEditHelp")}
          label={t("builder.design.transfer")}
          value={target.delayed_transfer_task}
          onChange={(delayed_transfer_task) => onChange({ ...target, delayed_transfer_task })}
        />
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
    return <HintEditor disabled={disabled} target={target} onChange={onChange} />;
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
      <TextField
        disabled={disabled}
        help={t("builder.design.sourcesHelp")}
        label={t("builder.design.sources")}
        value={target.source_refs.join("\n")}
        onChange={(sourceRefs) =>
          onChange({
            ...target,
            source_refs: sourceRefs
              .split("\n")
              .map((item) => item.trim())
              .filter(Boolean),
          })
        }
      />
    </fieldset>
  );
}

function HintEditor({
  disabled,
  target,
  onChange,
}: {
  disabled: boolean;
  target: PracticeTarget;
  onChange: (target: PracticeTarget) => void;
}) {
  const { t } = useI18n();
  return (
    <fieldset className="practice-editor-fields">
      <legend>{t("builder.design.hints")}</legend>
      <p>{t("builder.design.hintsHelp")}</p>
      {target.hint_ladder.map((hint, index) => (
        <div className="practice-contract-item" key={`${hint.level}-${index}`}>
          <label>
            {t("builder.design.hintLevel", { index: index + 1 })}
            <select
              disabled={disabled}
              value={hint.level}
              onChange={(event) =>
                onChange({
                  ...target,
                  hint_ladder: sortHints(
                    target.hint_ladder.map((item, itemIndex) =>
                      itemIndex === index
                        ? { ...item, level: event.target.value as PracticeHint["level"] }
                        : item,
                    ),
                  ),
                })
              }
            >
              {HINT_LEVELS.map((level) => (
                <option
                  disabled={
                    level !== hint.level && target.hint_ladder.some((item) => item.level === level)
                  }
                  key={level}
                  value={level}
                >
                  {t(`builder.design.hintLevels.${level}`)}
                </option>
              ))}
            </select>
          </label>
          <TextField
            disabled={disabled}
            label={t("builder.design.hintContent", { index: index + 1 })}
            value={hint.content}
            onChange={(content) =>
              onChange({
                ...target,
                hint_ladder: target.hint_ladder.map((item, itemIndex) =>
                  itemIndex === index ? { ...item, content } : item,
                ),
              })
            }
          />
          <button
            disabled={disabled}
            type="button"
            onClick={() =>
              onChange({
                ...target,
                hint_ladder: target.hint_ladder.filter((_item, itemIndex) => itemIndex !== index),
              })
            }
          >
            {t("builder.design.removeHint", { index: index + 1 })}
          </button>
        </div>
      ))}
      {target.hint_ladder.length < HINT_LEVELS.length ? (
        <button disabled={disabled} type="button" onClick={() => addHint(target, onChange)}>
          {t("builder.design.addHint")}
        </button>
      ) : null}
    </fieldset>
  );
}

function addHint(target: PracticeTarget, onChange: (target: PracticeTarget) => void) {
  const level = HINT_LEVELS.find(
    (candidate) => !target.hint_ladder.some((hint) => hint.level === candidate),
  );
  if (level)
    onChange({
      ...target,
      hint_ladder: sortHints([...target.hint_ladder, { level, content: "" }]),
    });
}
function sortHints(hints: readonly PracticeHint[]): PracticeHint[] {
  return [...hints].sort(
    (left, right) => HINT_LEVELS.indexOf(left.level) - HINT_LEVELS.indexOf(right.level),
  );
}
