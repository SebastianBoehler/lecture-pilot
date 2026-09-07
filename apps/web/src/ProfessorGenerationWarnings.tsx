import { useI18n } from "./i18n";

export function ProfessorGenerationWarnings({ warnings }: { warnings: string[] }) {
  const { t } = useI18n();
  if (!warnings.length) return null;
  return (
    <details className="generation-warnings">
      <summary>{t("builder.warnings.title", { count: warnings.length })}</summary>
      <ul>
        {warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </details>
  );
}
