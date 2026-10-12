import { useI18n } from "../i18n/i18n";
import type { PracticeHint, PracticeTarget } from "./practiceDesignTypes";

export function ProfessorHintEvidence({
  hint,
  target,
}: {
  hint: PracticeHint;
  target: PracticeTarget;
}) {
  const { t } = useI18n();
  const selected = hint.evidence_ids ?? [];
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
