import { useI18n } from "./i18n";
import type { PracticeHint, PracticeTarget } from "./practiceDesignTypes";

const HINT_LEVELS: readonly PracticeHint["level"][] = [
  "prompt",
  "cue",
  "faded_example",
  "worked_step",
];

export function ProfessorPracticeTargetEditor({
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
    <details className="practice-target-editor">
      <summary>{t("builder.design.editTarget")}</summary>
      <div className="practice-target-fields">
        <ReadOnlyId label={t("builder.design.targetId")} value={target.id} />
        <TextField
          label={t("builder.design.targetTitle")}
          disabled={disabled}
          value={target.title}
          onChange={(title) => onChange({ ...target, title })}
        />
        <TextField
          label={t("builder.design.outcomeFor", { target: target.title })}
          disabled={disabled}
          value={target.outcome}
          onChange={(outcome) => onChange({ ...target, outcome })}
        />
        <TextField
          label={t("builder.design.baseline")}
          disabled={disabled}
          value={target.baseline_task}
          onChange={(baseline_task) => onChange({ ...target, baseline_task })}
        />
        <TextField
          label={t("builder.design.exit")}
          disabled={disabled}
          value={target.independent_exit_task}
          onChange={(independent_exit_task) => onChange({ ...target, independent_exit_task })}
        />
        <TextField
          label={t("builder.design.transfer")}
          disabled={disabled}
          value={target.delayed_transfer_task}
          onChange={(delayed_transfer_task) => onChange({ ...target, delayed_transfer_task })}
        />
        <label>
          {t("builder.design.reviewAfterDays")}
          <input
            min="1"
            max="365"
            type="number"
            disabled={disabled}
            value={target.review_after_days}
            onChange={(event) =>
              onChange({ ...target, review_after_days: Number(event.target.value) })
            }
          />
        </label>
        <TextField
          label={t("builder.design.sources")}
          disabled={disabled}
          value={target.source_refs.join("\n")}
          onChange={(sourceRefs) =>
            onChange({ ...target, source_refs: sourceRefs.split("\n").filter(Boolean) })
          }
        />
      </div>
      <fieldset className="practice-target-list">
        <legend>{t("builder.design.evidence")}</legend>
        {target.evidence_criteria.map((criterion) => (
          <div className="practice-contract-item" key={criterion.id}>
            <ReadOnlyId label={t("builder.design.criterionId")} value={criterion.id} />
            <TextField
              label={t("builder.design.criterionDescription", { id: criterion.id })}
              disabled={disabled}
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
      <fieldset className="practice-target-list">
        <legend>{t("builder.design.misconceptions")}</legend>
        {target.misconceptions.map((misconception) => (
          <div className="practice-contract-item" key={misconception.id}>
            <ReadOnlyId label={t("builder.design.misconceptionId")} value={misconception.id} />
            <TextField
              label={t("builder.design.misconceptionDescription", {
                id: misconception.id,
              })}
              disabled={disabled}
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
              label={t("builder.design.diagnosticCue", { id: misconception.id })}
              disabled={disabled}
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
      <fieldset className="practice-target-list">
        <legend>{t("builder.design.hints")}</legend>
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
                      level !== hint.level &&
                      target.hint_ladder.some((candidate) => candidate.level === level)
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
              label={t("builder.design.hintContent", { index: index + 1 })}
              disabled={disabled}
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
          <button
            disabled={disabled}
            type="button"
            onClick={() => {
              const level = HINT_LEVELS.find(
                (candidate) => !target.hint_ladder.some((hint) => hint.level === candidate),
              );
              if (level)
                onChange({
                  ...target,
                  hint_ladder: sortHints([...target.hint_ladder, { level, content: "" }]),
                });
            }}
          >
            {t("builder.design.addHint")}
          </button>
        ) : null}
      </fieldset>
    </details>
  );
}

function TextField({
  disabled,
  label,
  value,
  onChange,
}: {
  disabled: boolean;
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      {label}
      <textarea
        aria-label={label}
        disabled={disabled}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function ReadOnlyId({ label, value }: { label: string; value: string }) {
  return (
    <label>
      {label}
      <input readOnly value={value} />
    </label>
  );
}

function sortHints(hints: readonly PracticeHint[]): PracticeHint[] {
  return [...hints].sort(
    (left, right) => HINT_LEVELS.indexOf(left.level) - HINT_LEVELS.indexOf(right.level),
  );
}
