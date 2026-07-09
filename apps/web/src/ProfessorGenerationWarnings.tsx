import { useI18n } from "./i18n";

export function ProfessorGenerationWarnings({ warnings }: { warnings: string[] }) {
  const { t } = useI18n();
  if (!warnings.length) return null;
  return (
    <div className="generation-warnings" role="alert">
      <strong>{t("builder.warnings.title")}</strong>
      <ul>
        {warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </div>
  );
}
