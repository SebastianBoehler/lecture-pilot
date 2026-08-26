import { useI18n } from "./i18n";
import type { PracticeSourceAnchor } from "./practiceDesignTypes";

export function ProfessorPracticeEvidence({
  anchor,
  label,
}: {
  anchor: PracticeSourceAnchor | null;
  label?: string;
}) {
  const { t } = useI18n();
  if (!anchor) return <p className="practice-evidence-missing">{t("builder.design.noAnchor")}</p>;
  return (
    <details className="practice-source-evidence">
      <summary>{label ?? t("builder.design.showSource")}</summary>
      <div>
        <code>{anchor.source_path}</code>
        <blockquote>{anchor.excerpt}</blockquote>
      </div>
    </details>
  );
}
