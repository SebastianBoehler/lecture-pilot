import { useI18n } from "./i18n";

export function AnalyticsEmptyState() {
  const { t } = useI18n();
  return (
    <div className="analytics-empty-state">
      <strong>{t("analytics.noSignals")}</strong>
      <p>{t("analytics.noSignalsHelp")}</p>
    </div>
  );
}
