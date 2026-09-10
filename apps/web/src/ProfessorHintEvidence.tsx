import { useI18n } from "./i18n";
import type { PracticeHint, PracticeTarget } from "./practiceDesignTypes";

export function ProfessorHintEvidence({
  hint,
  target,
  disabled = true,
  onChange,
}: {
  hint: PracticeHint;
  target: PracticeTarget;
  disabled?: boolean;
  onChange?: (evidenceIds: readonly string[]) => void;
}) {
  const { t } = useI18n();
  const selected = hint.evidence_ids ?? [];
  if (!onChange) {
    return (
      <p>
        {t("builder.design.hintEvidence")}
        {": "}
        {selected.length
          ? target.evidence_criteria
              .filter((criterion) => selected.includes(criterion.id))
              .map((criterion) => criterion.description)
              .join("; ")
          : t("builder.design.hintGeneral")}
      </p>
    );
  }
  return (
    <fieldset className="practice-editor-fields" disabled={disabled}>
      <legend>{t("builder.design.hintEvidence")}</legend>
      <p>{t("builder.design.hintEvidenceHelp")}</p>
      {target.evidence_criteria.map((criterion) => (
        <label className="practice-checkbox-field" key={criterion.id}>
          <input
            type="checkbox"
            checked={selected.includes(criterion.id)}
            onChange={(event) =>
              onChange(
                event.target.checked
                  ? [...selected, criterion.id]
                  : selected.filter((id) => id !== criterion.id),
              )
            }
          />
          {criterion.description}
        </label>
      ))}
    </fieldset>
  );
}
