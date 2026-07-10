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
      <nav aria-label={t("footer.info")}>
        <button type="button" onClick={onOpenHowItWorks}>
          {t("footer.howItWorks")}
        </button>
        <button type="button" onClick={onOpenPrivacy}>
          {t("footer.privacy")}
        </button>
      </nav>
      <p className="app-footer-signature">
        Built with <span role="img" aria-label="love">♥</span> in Tübingen
      </p>
    </footer>
  );
}
