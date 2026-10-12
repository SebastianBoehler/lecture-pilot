import { useI18n } from "../i18n/i18n";

export function PlatformAdminRequired({ onBack }: { onBack: () => void }) {
  const { t } = useI18n();
  return (
    <main className="dashboard">
      <section aria-label={t("courseDemand.title")} className="dashboard-header">
        <button className="ghost-button" type="button" onClick={onBack}>
          {t("courseDemand.back")}
        </button>
        <h1>{t("courseDemand.accessTitle")}</h1>
        <p>{t("courseDemand.accessBody")}</p>
      </section>
    </main>
  );
}
