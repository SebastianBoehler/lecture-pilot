import { useI18n } from "./i18n";
import { ProfessorPracticeEvidence } from "./ProfessorPracticeEvidence";
import { TextField } from "./ProfessorPracticeEditorFields";
import type { PracticeHint, PracticeTarget } from "./practiceDesignTypes";

const HINT_LEVELS: readonly PracticeHint["level"][] = [
  "prompt",
  "cue",
  "faded_example",
  "worked_step",
];

export function ProfessorPracticeHintEditor({
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
          <ProfessorPracticeEvidence anchor={hint.source_anchor} />
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
        <p>{t("builder.design.addHintByRegenerating")}</p>
      ) : null}
    </fieldset>
  );
}

function sortHints(hints: readonly PracticeHint[]): PracticeHint[] {
  return [...hints].sort(
    (left, right) => HINT_LEVELS.indexOf(left.level) - HINT_LEVELS.indexOf(right.level),
  );
}
