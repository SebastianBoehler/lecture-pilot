import { useI18n } from "./i18n";

export function AppFooter({
  onOpenHowItWorks,
  onOpenPrivacy,
}: {
  onOpenHowItWorks: () => void;
  onOpenPrivacy: () => void;
}) {
  const { t } = useI18n();
  return (
    <footer className="app-footer">
      <span>LecturePilot pilot</span>
      <nav aria-label={t("footer.info")}>
        <button type="button" onClick={onOpenHowItWorks}>
          {t("footer.howItWorks")}
        </button>
        <button type="button" onClick={onOpenPrivacy}>
          {t("footer.privacy")}
        </button>
      </nav>
    </footer>
  );
}
